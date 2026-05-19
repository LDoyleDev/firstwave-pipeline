#!/usr/bin/env python3
"""
Generate personalized cold-outreach emails for top N hotel leads.

Uses Haiku for fast generation. Reads enriched leads from Supabase,
generates subject + body based on operator_type, pain_points, DM role, country.

Output: drafts stored in Supabase outreach_email_1 column + JSON report.
"""

import json
import sys
import logging
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.utils.anthropic_client import classify, VybeTradingWindowError
from backend.integrations.supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You write concise, personalized cold-outreach emails for First Wave AI — a voice-controlled B2B sales automation system for hotel operators.

Operator persona: Liam Doyle, liam@firstwaveai.com, based in Berlin. He helps independent hotels and boutique chains automate guest communication and revenue management.

Style guide:
- Tone: warm, direct, founder-led (not corporate marketing).
- Length: 80-120 words max.
- Open with a specific observation about THIS hotel (use pain point if known).
- One value prop, not three.
- Soft CTA: 15-min call (mention 10:30, 10:50, or 11:10 Europe/Berlin slot).
- No hyperbole, no "revolutionary," no "synergy."
- No formal sign-off; just "Liam".

Respond ONLY with valid JSON (no markdown):
{
  "subject": "<6-10 words, specific>",
  "body": "<the email body, plain text with \\n for breaks>"
}
"""


def parse_json(response: str) -> dict:
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    return json.loads(response.strip())


def generate_email(lead: dict) -> dict | None:
    """Generate subject + body for a lead."""
    ed = lead.get("enrichment_data") or {}
    enrichment = ed.get("enrichment") or {}

    name = f"{lead.get('first_name','')} {lead.get('last_name','')}".strip()
    location = lead.get("location") or ""
    dm_role = enrichment.get("decision_maker_role") or lead.get("title") or "General Manager"
    operator_type = enrichment.get("operator_type") or "independent"
    pain_points = enrichment.get("pain_points") or lead.get("pain_signals") or []
    parent_group = ed.get("parent_group") or "Independent"

    user_message = f"""Write a cold outreach email for this hotel.

Hotel name: {name}
Location: {location}
Operator type: {operator_type}
Parent group: {parent_group}
Decision-maker title: {dm_role}
Known pain points: {', '.join(pain_points) if pain_points else 'none specified'}

Generate the email now."""

    try:
        response = classify(SYSTEM_PROMPT, user_message)
        return parse_json(response)
    except (VybeTradingWindowError, json.JSONDecodeError) as e:
        logger.warning(f"  Generation error: {e}")
        return None
    except Exception as e:
        logger.warning(f"  Unexpected error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=200)
    parser.add_argument("--output", type=str, default="data/phase2/email_drafts.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't write to Supabase")
    args = parser.parse_args()

    logger.info(f"Fetching top {args.top_n} leads by lead_score...")
    response = (
        supabase.table("leads")
        .select("id, first_name, last_name, title, location, lead_score, pain_signals, enrichment_data, source")
        .in_("source", ["haiku_pilot", "haiku_max_test"])
        .order("lead_score", desc=True)
        .limit(args.top_n)
        .execute()
    )
    leads = response.data or []

    # Only verified
    leads = [l for l in leads if (l.get("enrichment_data") or {}).get("verification_status") == "verified_hotel"]
    logger.info(f"  Got {len(leads)} verified leads")

    drafts = []
    for i, lead in enumerate(leads, 1):
        name = f"{lead.get('first_name','')} {lead.get('last_name','')}".strip()
        logger.info(f"[{i}/{len(leads)}] {name[:50]}")

        t0 = time.time()
        email = generate_email(lead)
        t = time.time() - t0
        if not email:
            continue

        drafts.append({
            "id": lead["id"],
            "name": name,
            "score": lead.get("lead_score"),
            "subject": email.get("subject", ""),
            "body": email.get("body", ""),
            "elapsed_sec": round(t, 1),
        })

        if not args.dry_run:
            try:
                supabase.table("leads").update({
                    "outreach_email_1": json.dumps({
                        "subject": email.get("subject", ""),
                        "body": email.get("body", ""),
                    })
                }).eq("id", lead["id"]).execute()
            except Exception as e:
                logger.warning(f"  Supabase update failed: {e}")

        time.sleep(0.3)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({"drafts": drafts}, f, indent=2, ensure_ascii=False)
    logger.info(f"")
    logger.info(f"=== Generated {len(drafts)} email drafts ===")
    logger.info(f"✓ Written to {args.output}")
    if not args.dry_run:
        logger.info(f"✓ Updated Supabase outreach_email_1 for {len(drafts)} leads")


if __name__ == "__main__":
    sys.exit(main())
