#!/usr/bin/env python3
"""
Pilot: deep-personalize outreach emails by researching the named decision-maker
and recent company signals for each lead.

Per lead:
  1. Search for a named DM (GM / Owner / Director).
  2. Search for recent company news (renovations, awards, hiring).
  3. Scrape the lead's website About page if available.
  4. Synthesize findings via Ollama into structured `personalisation_hooks` JSON.
  5. Regenerate `outreach_email_1` using that enriched context.

Writes:
  - Supabase: leads.personalisation_hooks  (jsonb)
  - Supabase: leads.outreach_email_1       (json-stringified {subject, body})
  - Local:    data/phase2/research_pilot.json (before/after, for review)

Pilot mode: --top-n 10 (default). Use --dry-run to skip writes.
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.integrations.supabase_client import supabase
from backend.integrations.web_researcher import scrape_website_text, search_web
from backend.utils.anthropic_client import classify, VybeTradingWindowError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


RESEARCH_SYNTHESIS_PROMPT = """You are a B2B sales researcher synthesizing public-source findings about a hotel and its decision-makers.

You will receive raw search snippets and (optionally) website text. Extract only what is supported by the evidence — do not invent names, titles, events, dates, or numbers.

Respond ONLY with valid JSON (no markdown):
{
  "decision_maker": {
    "name": "<full name (first + last) or null — NEVER first-name-only>",
    "title": "<exact title from source or null>",
    "source_url": "<url that mentioned them or null>"
  },
  "recent_signals": [
    {"text": "<1-line fact, only restate what the snippet says>", "source_url": "<url>"},
    ...
  ],
  "personal_hooks": ["<1-line angle worth referencing in an email, must trace to a recent_signal>", ...],
  "confidence": <0.0-1.0, how confident you are in the decision_maker name>,
  "notes": "<one line on what evidence quality looked like>"
}

HARD RULES — break these and the output is rejected:
- If you cannot find a FULL name (first + last) from a credible source, set decision_maker fields to null and confidence to 0. First-name-only is NEVER acceptable.
- TripAdvisor / Booking.com / Expedia review responders are NOT verified decision-makers. Names appearing only on these sources do not count; treat as null.
- A credible DM source is: company website "team"/"about" page, LinkedIn, press release, or an industry publication.
- Every recent_signal must restate (not embellish) a specific snippet. Do not infer years, anniversaries, or rounded counts that don't appear in the text.
- personal_hooks must paraphrase a recent_signal — no hooks without a backing signal.
- Skip OTA listings, review aggregators, generic directory entries when extracting DM info.
"""


EMAIL_PROMPT = """You write concise, personalized cold-outreach emails for First Wave AI — a voice-controlled B2B sales automation system for hotel operators.

Operator persona: Liam Doyle, liam@firstwaveai.com, based in Berlin. He helps independent hotels and boutique chains automate guest communication and revenue management.

Style guide:
- Tone: warm, direct, founder-led (not corporate marketing).
- Length: 80-120 words max.
- Open with a SPECIFIC observation grounded in the research (named DM + a recent signal or personal hook). If decision_maker is null, address by role ("General Manager,") and open with a hotel-specific signal — NEVER invent a name.
- One value prop, not three. Tie it to the pain point or signal.
- Soft CTA: 15-min call (mention 10:30, 10:50, or 11:10 Europe/Berlin slot).
- No hyperbole, no "revolutionary," no "synergy."
- No formal sign-off; just "Liam".

HARD ANTI-HALLUCINATION RULES:
- Do not state any number, year, anniversary count, room count, or rating that is not explicitly present in `recent_signals`. Restate, don't infer.
- Do not invent achievements, awards, partnerships, or events not in `recent_signals`.
- Do not fabricate guest reviews or quotes.

Respond ONLY with valid JSON (no markdown):
{
  "subject": "<6-10 words, specific>",
  "body": "<the email body, plain text with \\n for breaks>"
}
"""


def parse_json_response(response: str) -> dict:
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    return json.loads(response.strip())


def research_lead(lead: dict) -> dict:
    """Run web searches + scrape, return raw evidence bundle."""
    hotel_name = f"{lead.get('first_name','')} {lead.get('last_name','')}".strip() or lead.get("company") or ""
    location = lead.get("location") or ""

    queries = [
        f'"{hotel_name}" general manager',
        f'"{hotel_name}" {location} owner OR director',
        f'"{hotel_name}" 2025 OR 2026',
    ]

    evidence = {"hotel_name": hotel_name, "location": location, "snippets": [], "website_text": ""}
    for q in queries:
        results = search_web(q, max_results=4)
        for r in results:
            evidence["snippets"].append({
                "query": q,
                "title": r.get("title", "")[:200],
                "href": r.get("href", ""),
                "body": r.get("body", "")[:300],
            })
        time.sleep(0.3)

    # Scrape the lead's website if we have one
    website = lead.get("linkedin_url") or (lead.get("enrichment_data") or {}).get("website")
    if website and "linkedin.com" not in website:
        text = scrape_website_text(website, max_chars=2000)
        if text:
            evidence["website_text"] = text

    return evidence


UNVERIFIED_DM_DOMAINS = ("tripadvisor.", "booking.com", "expedia.", "hotels.com", "trivago.")


def sanitize_hooks(hooks: dict) -> dict:
    """Defensive post-filter — reject DM names that the model leaked through despite the prompt."""
    dm = hooks.get("decision_maker") or {}
    name = (dm.get("name") or "").strip()
    src = (dm.get("source_url") or "").lower()

    bad = False
    reason = None
    if name and " " not in name:
        bad, reason = True, "first_name_only"
    if src and any(d in src for d in UNVERIFIED_DM_DOMAINS):
        bad, reason = True, "untrusted_source_domain"

    if bad:
        hooks["decision_maker"] = {"name": None, "title": None, "source_url": None}
        hooks["confidence"] = 0.0
        hooks["notes"] = (hooks.get("notes") or "") + f" | DM rejected: {reason}"
    return hooks


def synthesize_research(evidence: dict) -> dict:
    """Call Ollama to extract structured hooks from raw evidence."""
    user_message = f"""Hotel: {evidence['hotel_name']}
Location: {evidence['location']}

Search snippets (top results from multiple queries):
{json.dumps(evidence['snippets'], indent=2, ensure_ascii=False)[:6000]}

Website text (if available, truncated):
{evidence['website_text'][:1500]}

Synthesize now."""

    try:
        response = classify(RESEARCH_SYNTHESIS_PROMPT, user_message)
        return sanitize_hooks(parse_json_response(response))
    except (VybeTradingWindowError, json.JSONDecodeError) as e:
        logger.warning(f"  Synthesis parse error: {e}")
        return {"decision_maker": {"name": None, "title": None, "source_url": None},
                "recent_signals": [], "personal_hooks": [], "confidence": 0.0,
                "notes": f"synthesis_error: {e}"}


def regenerate_email(lead: dict, hooks: dict) -> dict | None:
    """Regenerate the email with the enriched research context."""
    hotel_name = f"{lead.get('first_name','')} {lead.get('last_name','')}".strip() or lead.get("company") or ""
    enrichment = (lead.get("enrichment_data") or {}).get("enrichment") or {}
    dm = hooks.get("decision_maker") or {}

    user_message = f"""Write a cold-outreach email for this hotel using the research context.

Hotel: {hotel_name}
Location: {lead.get('location') or ''}
Operator type: {enrichment.get('operator_type') or 'independent'}
Known pain points: {', '.join(enrichment.get('pain_points') or []) or 'none specified'}

Decision-maker (from research):
  Name: {dm.get('name') or '(unknown — address by role)'}
  Title: {dm.get('title') or enrichment.get('decision_maker_role') or 'General Manager'}
  Research confidence: {hooks.get('confidence', 0)}

Recent signals: {hooks.get('recent_signals') or []}
Personal hooks: {hooks.get('personal_hooks') or []}

Generate the email now. If no named DM, do NOT invent one — open with a hotel-specific observation."""

    try:
        response = classify(EMAIL_PROMPT, user_message)
        return parse_json_response(response)
    except (VybeTradingWindowError, json.JSONDecodeError) as e:
        logger.warning(f"  Email regen error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--output", type=str, default="data/phase2/research_pilot.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't write to Supabase (still writes local JSON)")
    args = parser.parse_args()

    logger.info(f"Loading top {args.top_n} highest-score leads with existing drafts...")
    rows = (supabase.table("leads")
            .select("*")
            .not_.is_("outreach_email_1", "null")
            .order("lead_score", desc=True)
            .limit(args.top_n)
            .execute().data)
    logger.info(f"Got {len(rows)} leads")

    results = []
    for i, lead in enumerate(rows, 1):
        name = f"{lead.get('first_name','')} {lead.get('last_name','')}".strip() or lead.get("company") or "?"
        logger.info(f"[{i}/{len(rows)}] {name[:60]}  (score={lead.get('lead_score')})")

        old_draft_raw = lead.get("outreach_email_1") or "{}"
        try:
            old_draft = json.loads(old_draft_raw)
        except Exception:
            old_draft = {"subject": "(unparseable)", "body": old_draft_raw[:200]}

        t0 = time.time()
        evidence = research_lead(lead)
        logger.info(f"  research: {len(evidence['snippets'])} snippets, website={'yes' if evidence['website_text'] else 'no'}")

        hooks = synthesize_research(evidence)
        dm = hooks.get("decision_maker") or {}
        logger.info(f"  DM: {dm.get('name') or '(none)'}  conf={hooks.get('confidence', 0):.2f}  signals={len(hooks.get('recent_signals') or [])}")

        new_email = regenerate_email(lead, hooks)
        elapsed = time.time() - t0
        logger.info(f"  elapsed: {elapsed:.1f}s")

        if not args.dry_run:
            try:
                ed = dict(lead.get("enrichment_data") or {})
                ed["research"] = hooks
                supabase.table("leads").update({
                    "personalisation_hooks": hooks.get("personal_hooks") or [],
                    "enrichment_data": ed,
                    "outreach_email_1": json.dumps(new_email) if new_email else old_draft_raw,
                }).eq("id", lead["id"]).execute()
            except Exception as e:
                logger.warning(f"  Supabase update failed: {e}")

        results.append({
            "id": lead["id"],
            "name": name,
            "score": lead.get("lead_score"),
            "before": old_draft,
            "after": new_email,
            "hooks": hooks,
            "elapsed_sec": round(elapsed, 1),
        })

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({"pilot": results}, f, indent=2, ensure_ascii=False)
    logger.info(f"")
    logger.info(f"=== Pilot complete: {len(results)} leads ===")
    logger.info(f"✓ Local: {args.output}")
    if not args.dry_run:
        logger.info(f"✓ Supabase: personalisation_hooks + outreach_email_1 updated")
    named = sum(1 for r in results if (r["hooks"].get("decision_maker") or {}).get("name"))
    logger.info(f"Named DM found: {named}/{len(results)}  ({100*named/max(len(results),1):.0f}%)")


if __name__ == "__main__":
    main()
