#!/usr/bin/env python3
"""Read-only audit of an email-sourcing run.

Confirms coverage and — more importantly — that every sourced address is
defensible: complete provenance, a jurisdiction route that actually permits the
send, a matching evidence snapshot, and no suppressed or junk addresses.

Exits non-zero if a CRITICAL check fails (provenance / route / suppression /
junk) so it can gate a follow-on send. Run on vybe-desktop:
  PYTHONPATH=. python scripts/verify_email_sourcing.py
"""

import gzip
import hashlib
import logging
from collections import Counter
from pathlib import Path

from backend.integrations import jurisdiction
from backend.integrations.email_extractor import is_junk
from backend.integrations.supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_email_sourcing")

REPO_ROOT = Path(__file__).resolve().parent.parent


def _page(table: str, columns: str, **eq) -> list[dict]:
    """Fetch every row of a table (Supabase caps a select at 1000 rows)."""
    rows: list[dict] = []
    offset = 0
    while True:
        q = supabase.table(table).select(columns)
        for k, v in eq.items():
            q = q.eq(k, v)
        batch = q.range(offset, offset + 999).execute().data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    leads = _page("leads", "id,email,email_source,email_sourced_at,email_address_type,"
                           "country,jurisdiction_route,company_id,email_provenance,"
                           "suppressed_at,outreach_approved", outreach_approved=True)
    emailed = [l for l in leads if (l.get("email") or "").strip()]
    logger.info("Coverage: %d/%d approved leads have an email", len(emailed), len(leads))

    by_source = Counter(l.get("email_source") or "unknown" for l in emailed)
    by_route = Counter(l.get("jurisdiction_route") or "unknown" for l in emailed)
    logger.info("  by source: %s", dict(by_source))
    logger.info("  by route:  %s", dict(by_route))

    # --- CRITICAL: provenance completeness -----------------------------------
    for l in emailed:
        missing = [f for f in ("email_source", "email_sourced_at", "email_address_type")
                   if not l.get(f)]
        if missing:
            failures.append(f"lead {l['id']}: missing provenance fields {missing}")
        if not l.get("email_provenance"):
            warnings.append(f"lead {l['id']}: no email_provenance JSONB summary")

    # --- CRITICAL: route consistency -----------------------------------------
    for l in emailed:
        ok, reason = jurisdiction.is_sendable(l.get("country"), l.get("email_source"))
        if not ok:
            failures.append(f"lead {l['id']}: emailed but not sendable ({reason}, "
                            f"country={l.get('country')}, source={l.get('email_source')})")

    # --- CRITICAL: no junk addresses -----------------------------------------
    for l in emailed:
        if is_junk(l["email"]):
            failures.append(f"lead {l['id']}: junk address {l['email']}")

    # --- CRITICAL: nothing emailed is suppressed -----------------------------
    suppressed = {(_norm(r["email"])) for r in _page("suppression_list", "email")}
    for l in emailed:
        if _norm(l["email"]) in suppressed:
            failures.append(f"lead {l['id']}: emailed address {l['email']} is suppressed")

    # --- audit table: a provenance row per emailed lead ----------------------
    prov_rows = _page("email_provenance", "lead_id,email,email_source,html_sha256,"
                                          "snapshot_path,optout_disclaimer_seen")
    prov_by_lead: dict[str, list[dict]] = {}
    for r in prov_rows:
        prov_by_lead.setdefault(r["lead_id"], []).append(r)
    for l in emailed:
        if l.get("email_provenance") and l["id"] not in prov_by_lead:
            warnings.append(f"lead {l['id']}: email_provenance JSONB set but no audit row")

    # --- snapshots exist and hash-match --------------------------------------
    checked = missing_snap = bad_hash = 0
    for r in prov_rows:
        if not r.get("snapshot_path"):
            continue
        checked += 1
        path = REPO_ROOT / r["snapshot_path"]
        if not path.exists():
            missing_snap += 1
            warnings.append(f"snapshot missing: {r['snapshot_path']}")
            continue
        if r.get("html_sha256"):
            try:
                raw = gzip.open(path, "rb").read()
                if hashlib.sha256(raw).hexdigest() != r["html_sha256"]:
                    bad_hash += 1
                    failures.append(f"snapshot hash mismatch: {r['snapshot_path']}")
            except Exception as e:
                warnings.append(f"snapshot unreadable {r['snapshot_path']}: {e}")

    # --- disclaimer integrity ------------------------------------------------
    for r in prov_rows:
        if r.get("optout_disclaimer_seen"):
            failures.append(f"lead {r['lead_id']}: emailed despite optout_disclaimer_seen")

    linked = sum(1 for l in emailed if l.get("company_id"))
    logger.info("Snapshots: %d checked, %d missing, %d hash-mismatch", checked, missing_snap, bad_hash)
    logger.info("Companies linkage: %d/%d emailed leads have company_id", linked, len(emailed))

    logger.info("=" * 60)
    if warnings:
        logger.warning("%d warning(s):", len(warnings))
        for w in warnings[:25]:
            logger.warning("  %s", w)
    if failures:
        logger.error("%d CRITICAL failure(s):", len(failures))
        for f in failures[:25]:
            logger.error("  %s", f)
        return 1
    logger.info("All critical checks passed.")
    return 0


def _norm(email: str) -> str:
    return (email or "").strip().lower()


if __name__ == "__main__":
    raise SystemExit(main())
