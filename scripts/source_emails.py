#!/usr/bin/env python3
"""Source email addresses for approved leads — tiered, near-zero-token.

The ~901 approved leads have no email; the cold-email drafts cannot send without
one. The hotel website URLs were dropped during enrichment, so this:

  Tier 1  recovers websites by re-matching leads to the raw scrape JSONs
          (fresh OSM scrape as fallback) and persists them to `companies`.
  Tier 2  takes OSM `contact:email` tag addresses        (Route A only).
  Tier 3  scrapes the hotel website for a published address (Route A + B),
          capturing a full provenance-evidence bundle per address.

Every address is written through `provenance.set_lead_email`, which records the
GDPR Art 14 / CASL evidence trail. The ONLY LLM use is a Haiku confirmation of
the opt-out-disclaimer check (Tier 3) — gated by the vybe-trading window.

Run on vybe-desktop:
  PYTHONPATH=. python scripts/source_emails.py --dry-run --limit 25
  PYTHONPATH=. python scripts/source_emails.py --dry-run
  PYTHONPATH=. python scripts/source_emails.py            # live, Tiers 1-3
"""

import argparse
import asyncio
import gzip
import hashlib
import json
import logging
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx

from backend.integrations import jurisdiction, provenance, suppression
from backend.integrations.email_extractor import (
    best_email, context_snippet, extract_emails, find_optout_disclaimer,
    html_to_text, page_title,
)
from backend.integrations.supabase_client import supabase
from backend.integrations.website_fetch import BROWSER_HEADERS, fetch_site
from backend.integrations import website_recovery as wr
from backend.prompts.system_prompts import DISCLAIMER_CLASSIFIER_SYSTEM_PROMPT
from backend.utils.anthropic_client import VybeTradingWindowError, classify

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("source_emails")

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = REPO_ROOT / "data" / "phase2" / "email_sourcing_checkpoint.jsonl"
EVIDENCE_DIR = REPO_ROOT / "data" / "email_evidence"
OSM_REFRESH = "data/phase2/osm_refresh.json"

# Checkpoint results that mean "done — skip on re-run". pending_confirm is NOT
# here: those leads are retried (the Haiku step was gated by the trading window).
_TERMINAL = {"emailed", "no_email", "skipped_disclaimer", "no_website"}

# Keywords that make a phrase-list-clean page "borderline" — possibly a
# paraphrased restriction worth a Haiku look under --confirm-borderline-only.
_BORDERLINE_KW = (
    "unsolicited", "solicitation", "do not contact", "no marketing",
    "not accept", "no sales", "mailing list", "opt out", "opt-out",
)


# --------------------------------------------------------------------------
# Checkpoint
# --------------------------------------------------------------------------

def load_checkpoint() -> dict[str, str]:
    """lead_id -> latest result, from the append-only checkpoint log."""
    done: dict[str, str] = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text().splitlines():
            try:
                row = json.loads(line)
                done[row["lead_id"]] = row["result"]
            except Exception:
                continue
    return done


def checkpoint(lead_id: str, tier: int, result: str) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT, "a") as f:
        f.write(json.dumps({
            "lead_id": lead_id, "tier": tier, "result": result,
            "ts": datetime.now(UTC).isoformat(),
        }) + "\n")


# --------------------------------------------------------------------------
# Tier 0 — scope reduction
# --------------------------------------------------------------------------

def load_working_set(limit: int | None) -> list[dict]:
    """Approved, non-suppressed, email-less leads on a sendable route (A/B)."""
    rows: list[dict] = []
    offset = 0
    while True:  # Supabase caps a select at 1000 rows.
        batch = (
            supabase.table("leads")
            .select("id,first_name,last_name,email,email_source,country,location,"
                    "source,enrichment_data,company_id,suppressed_at,outreach_approved")
            .eq("outreach_approved", True)
            .range(offset, offset + 999)
            .execute()
        ).data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    working: list[dict] = []
    skipped = Counter()
    for ld in rows:
        if (ld.get("email") or "").strip():
            skipped["already_emailed"] += 1
            continue
        if ld.get("suppressed_at"):
            skipped["suppressed"] += 1
            continue
        route = jurisdiction.classify(ld.get("country"))
        if route in ("C", "do_not_send"):
            skipped[f"route_{route}"] += 1
            continue
        ld["_route"] = route
        working.append(ld)
    logger.info("Tier 0: %d approved leads → %d in scope (skipped: %s)",
                len(rows), len(working), dict(skipped))
    return working[:limit] if limit else working


# --------------------------------------------------------------------------
# Tier 1 — website recovery
# --------------------------------------------------------------------------

def recover_websites(leads: list[dict], dry_run: bool) -> None:
    """Attach `_website` / `_match` to each lead. Re-match to scrape JSONs;
    fall back to a fresh OSM scrape for the unmatched. Persist to `companies`."""
    linked = [l for l in leads if l.get("company_id")]
    unlinked = [l for l in leads if not l.get("company_id")]

    # Already-linked leads (a prior run) — read the website straight off companies.
    if linked:
        ids = [l["company_id"] for l in linked]
        comp: dict[str, dict] = {}
        for i in range(0, len(ids), 200):
            for c in (supabase.table("companies").select("id,website,name")
                      .in_("id", ids[i:i + 200]).execute().data or []):
                comp[c["id"]] = c
        for l in linked:
            c = comp.get(l["company_id"], {})
            l["_website"] = c.get("website")
            l["_match"], l["_match_method"] = None, "already_linked"

    records = wr.load_scrape_records(REPO_ROOT)
    exact_idx, fuzzy_idx = wr.build_indexes(records)
    _match_against(unlinked, exact_idx, fuzzy_idx)

    # Fallback: fresh OSM scrape for whatever did not match.
    still = [l for l in unlinked if not l.get("_website")]
    if still:
        isos = sorted({jurisdiction.to_iso(l.get("country")) or "" for l in still} - {""})
        logger.info("Tier 1: %d unmatched → OSM refresh for %s", len(still), isos)
        path = wr.run_osm_refresh(isos, OSM_REFRESH, REPO_ROOT)
        if path:
            ex2, fz2 = wr.build_indexes(wr.load_scrape_records(REPO_ROOT))
            _match_against(still, ex2, fz2)

    matched = [l for l in unlinked if l.get("_website")]
    logger.info("Tier 1: %d/%d unlinked leads matched a website",
                len(matched), len(unlinked))

    # Persist recovered websites to `companies` and link the lead.
    for l in matched:
        if dry_run:
            continue
        enr = l.get("enrichment_data") or {}
        name = enr.get("raw_name") or f"{l.get('first_name', '')} {l.get('last_name', '')}".strip()
        wr.upsert_company_for_lead(l["id"], name, l["_website"])


def _match_against(leads: list[dict], exact_idx: dict, fuzzy_idx: dict) -> None:
    for l in leads:
        if l.get("_website"):
            continue
        rec, method = wr.match_lead(l, exact_idx, fuzzy_idx)
        if rec and (rec.get("website") or rec.get("email")):
            l["_match"], l["_match_method"] = rec, method
            l["_website"] = (rec.get("website") or "").strip() or None


# --------------------------------------------------------------------------
# Tier 2 — OSM-tag emails
# --------------------------------------------------------------------------

def tier2_osm_emails(leads: list[dict], dry_run: bool, stats: Counter) -> None:
    """OSM `contact:email` addresses. Route A only — osm_tag is not a published
    source, so a Route B lead must wait for Tier 3."""
    from backend.integrations.email_extractor import is_junk  # local: keep header lean

    for l in leads:
        if l.get("_emailed"):
            continue
        rec = l.get("_match")
        email = (rec or {}).get("email", "").strip().lower()
        if not email or is_junk(email):
            continue
        if l["_route"] != "A":
            stats["tier2_route_b_osm_skipped"] += 1
            continue
        evidence = {
            "source_url": wr.osm_permalink(rec),
            "source_page_title": None,
            "context_snippet": None,
            "robots_allowed": None,
            "optout_disclaimer_seen": False,
            "disclaimer_check_method": "none",
            "notes": "OSM contact:email tag",
        }
        logger.info("Tier 2: %s ← %s (osm_tag)%s", l["id"], email, " [dry-run]" if dry_run else "")
        if not dry_run:
            provenance.set_lead_email(l["id"], email, source="osm_tag",
                                      country=l.get("country"), evidence=evidence)
            checkpoint(l["id"], 2, "emailed")
        l["_emailed"] = True
        stats["tier2_emailed"] += 1


# --------------------------------------------------------------------------
# Tier 3 — website scrape + evidence capture
# --------------------------------------------------------------------------

async def _fetch_all(leads: list[dict]) -> dict[str, dict]:
    """Concurrently fetch every lead's website. Returns {lead_id: fetch_result}."""
    sem = asyncio.Semaphore(25)
    results: dict[str, dict] = {}
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(headers=BROWSER_HEADERS, follow_redirects=True,
                                 timeout=timeout) as client:
        async def one(ld: dict) -> None:
            async with sem:
                iso = jurisdiction.to_iso(ld.get("country"))
                results[ld["id"]] = await fetch_site(client, ld["_website"], iso)
        await asyncio.gather(*[one(l) for l in leads if l.get("_website")],
                             return_exceptions=True)
    return results


def _haiku_says_restricted(page_text: str) -> str:
    """Ask Haiku whether the page restricts unsolicited email.
    Returns 'restricted' | 'clear' | 'unknown'. May raise VybeTradingWindowError."""
    out = classify(DISCLAIMER_CLASSIFIER_SYSTEM_PROMPT, page_text[:6000]).upper()
    if "RESTRICTED" in out:
        return "restricted"
    if "CLEAR" in out:
        return "clear"
    logger.warning("disclaimer classifier returned an unparseable verdict")
    return "unknown"


def _save_snapshot(lead_id: str, html: str) -> tuple[str, str]:
    """Persist a gzipped HTML snapshot. Returns (sha256, repo-relative path)."""
    raw = html.encode("utf-8", "replace")
    sha = hashlib.sha256(raw).hexdigest()
    out_dir = EVIDENCE_DIR / lead_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{sha}.html.gz"
    with gzip.open(path, "wb") as f:
        f.write(raw)
    return sha, str(path.relative_to(REPO_ROOT))


def tier3_website_scrape(leads: list[dict], dry_run: bool,
                         confirm_borderline_only: bool, stats: Counter) -> None:
    todo = [l for l in leads if not l.get("_emailed") and l.get("_website")]
    logger.info("Tier 3: fetching %d websites...", len(todo))
    fetched = asyncio.run(_fetch_all(todo))

    for l in todo:
        result = fetched.get(l["id"], {})
        pages: dict[str, str] = result.get("pages", {})
        if not pages:
            stats["tier3_no_website"] += 1
            checkpoint(l["id"], 3, "no_website")
            continue
        domain = result.get("domain")

        # Collect candidate addresses, remembering the page each came from.
        candidates: list[tuple[str, str, str]] = []
        for url, html in pages.items():
            for e in extract_emails(html):
                candidates.append((e, url, html))
        pick = best_email([c[0] for c in candidates], domain)
        if not pick:
            stats["tier3_no_email"] += 1
            checkpoint(l["id"], 3, "no_email")
            continue
        email, addr_type = pick
        src_url, src_html = next((u, h) for (e, u, h) in candidates if e == email)
        src_text = html_to_text(src_html)
        all_text = " ".join(html_to_text(h) for h in pages.values())

        # Disclaimer check — deterministic phrase list first.
        method = "phrase_list"
        phrase_hit = find_optout_disclaimer(all_text)
        if phrase_hit:
            _skip_disclaimer(l, email, src_url, f"phrase: {phrase_hit}", dry_run, stats)
            continue

        # Haiku confirm (vybe-trading-gated). dry-run skips the call to save tokens.
        run_haiku = not confirm_borderline_only or any(k in all_text.lower()
                                                       for k in _BORDERLINE_KW)
        if run_haiku and not dry_run:
            method = "phrase_list+haiku"
            try:
                verdict = _haiku_says_restricted(src_text)
            except VybeTradingWindowError:
                logger.info("Tier 3: %s deferred — LLM window closed", l["id"])
                checkpoint(l["id"], 3, "pending_confirm")
                stats["tier3_pending_confirm"] += 1
                continue
            if verdict == "restricted":
                _skip_disclaimer(l, email, src_url, "haiku verdict", dry_run, stats)
                continue
        elif run_haiku and dry_run:
            method = "phrase_list+haiku"

        # Clear — capture evidence and source the address.
        if dry_run:
            logger.info("Tier 3: %s ← %s (website_published, %s) [dry-run]",
                        l["id"], email, method)
        else:
            sha, snap = _save_snapshot(l["id"], src_html)
            evidence = {
                "source_url": src_url,
                "source_page_title": page_title(src_html),
                "context_snippet": context_snippet(src_text, email),
                "robots_allowed": True,  # only robots-permitted pages were fetched
                "optout_disclaimer_seen": False,
                "disclaimer_check_method": method,
                "html_sha256": sha,
                "snapshot_path": snap,
            }
            provenance.set_lead_email(l["id"], email, source="website_published",
                                      address_type=addr_type, country=l.get("country"),
                                      evidence=evidence)
            checkpoint(l["id"], 3, "emailed")
        l["_emailed"] = True
        stats["tier3_emailed"] += 1
        stats[f"tier3_emailed_route_{l['_route']}"] += 1


def _skip_disclaimer(lead: dict, email: str, src_url: str, why: str,
                     dry_run: bool, stats: Counter) -> None:
    logger.info("Tier 3: %s SKIPPED — opt-out disclaimer (%s)%s",
                lead["id"], why, " [dry-run]" if dry_run else "")
    if not dry_run:
        suppression.add_suppression(email, reason="source_optout",
                                    source_campaign="email_sourcing",
                                    notes=f"opt-out disclaimer ({why}) at {src_url}")
        checkpoint(lead["id"], 3, "skipped_disclaimer")
    stats["tier3_skipped_disclaimer"] += 1


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Tiered email sourcing for approved leads")
    ap.add_argument("--dry-run", action="store_true",
                    help="Run every tier but log would-writes instead of writing")
    ap.add_argument("--limit", type=int, default=None, help="Cap the working set (smoke test)")
    ap.add_argument("--confirm-borderline-only", action="store_true",
                    help="Run the Haiku disclaimer confirm only on borderline pages")
    args = ap.parse_args()

    done = load_checkpoint()
    working = load_working_set(args.limit)
    # Skip leads already resolved in a prior run (pending_confirm is retried).
    fresh = [l for l in working if done.get(l["id"]) not in _TERMINAL]
    logger.info("%d leads to process (%d already resolved)",
                len(fresh), len(working) - len(fresh))
    if not fresh:
        return 0

    stats: Counter = Counter()
    recover_websites(fresh, args.dry_run)
    tier2_osm_emails(fresh, args.dry_run, stats)
    tier3_website_scrape(fresh, args.dry_run, args.confirm_borderline_only, stats)

    emailed = stats["tier2_emailed"] + stats["tier3_emailed"]
    logger.info("=" * 60)
    logger.info("EMAIL SOURCING %s — %d/%d leads sourced",
                "DRY RUN" if args.dry_run else "COMPLETE", emailed, len(fresh))
    for k in sorted(stats):
        logger.info("  %-32s %d", k, stats[k])
    no_site = sum(1 for l in fresh if not l.get("_website"))
    logger.info("  %-32s %d", "leads with no website recovered", no_site)
    if stats["tier3_pending_confirm"]:
        logger.info("Re-run in an allowed LLM window to finish pending_confirm leads.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
