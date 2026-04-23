"""Bulk import leads from CSV into the pipeline without triggering enrichment.

Handles Apollo export, LinkedIn export, or any generic CSV.

Usage:
    PYTHONPATH=. venv/bin/python3 scripts/import_leads_csv.py apollo_uk.csv
    PYTHONPATH=. venv/bin/python3 scripts/import_leads_csv.py leads.csv --source linkedin_csv --dry-run
"""
import argparse
import csv
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Column name maps — keys are normalised lower-stripped header names
_APOLLO_MAP = {
    "first name": "first_name",
    "last name": "last_name",
    "title": "title",
    "company": "company",
    "email": "email",
    "linkedin url": "linkedin_url",
    "city": "location",
    "website": "company_website",
}

_LINKEDIN_MAP = {
    "first name": "first_name",
    "last name": "last_name",
    "position": "title",
    "company": "company",
    "email address": "email",
    "profile url": "linkedin_url",
}

_GENERIC_MAP = {
    "first_name": "first_name",
    "last_name": "last_name",
    "title": "title",
    "company": "company",
    "email": "email",
    "linkedin_url": "linkedin_url",
    "location": "location",
}

_SOURCE_MAPS = {
    "apollo_csv": _APOLLO_MAP,
    "linkedin_csv": _LINKEDIN_MAP,
    "generic": _GENERIC_MAP,
}


def _detect_source(headers: list[str]) -> str:
    lc = [h.lower().strip() for h in headers]
    if "linkedin url" in lc:
        return "apollo_csv"
    if "profile url" in lc:
        return "linkedin_csv"
    return "generic"


def _map_row(row: dict, col_map: dict) -> dict:
    normalised = {k.lower().strip(): v.strip() for k, v in row.items()}
    result = {}
    for csv_col, field in col_map.items():
        val = normalised.get(csv_col, "")
        if val:
            result[field] = val
    return result


def import_csv(
    file_path: str,
    source: str | None = None,
    dry_run: bool = False,
) -> dict:
    path = Path(file_path)
    if not path.exists():
        logger.error("File not found: %s", file_path)
        sys.exit(1)

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        logger.info("CSV is empty — nothing to import.")
        return {"found": 0, "added": 0, "skipped": 0}

    headers = list(rows[0].keys())
    detected = source or _detect_source(headers)
    col_map = _SOURCE_MAPS.get(detected, _GENERIC_MAP)
    logger.info("Detected source format: %s (%d rows)", detected, len(rows))

    # Normalise rows
    leads = [_map_row(r, col_map) for r in rows]
    leads = [l for l in leads if l.get("first_name") or l.get("email")]

    if dry_run:
        logger.info("[dry-run] Would attempt to import %d leads.", len(leads))
        return {"found": len(rows), "added": 0, "skipped": 0, "dry_run": True}

    from backend.integrations.supabase_client import supabase

    # Load existing emails in one query for dedup
    existing_rows = supabase.table("leads").select("email").not_.is_("email", "null").execute().data or []
    known_emails: set[str] = {r["email"].lower() for r in existing_rows if r.get("email")}

    to_insert = []
    skipped = 0
    for lead in leads:
        email = (lead.get("email") or "").lower()
        if email and email in known_emails:
            skipped += 1
            continue
        if email:
            known_emails.add(email)
        record = {
            "first_name": lead.get("first_name", ""),
            "last_name": lead.get("last_name", ""),
            "title": lead.get("title"),
            "company": lead.get("company"),
            "email": lead.get("email") or None,
            "linkedin_url": lead.get("linkedin_url") or None,
            "location": lead.get("location"),
            "source": detected,
            "pipeline_stage": "discovered",
        }
        to_insert.append(record)

    added = 0
    for i in range(0, len(to_insert), 100):
        batch = to_insert[i : i + 100]
        supabase.table("leads").insert(batch).execute()
        added += len(batch)
        logger.info("  Inserted batch %d–%d", i + 1, i + len(batch))

    logger.info("Import complete: %d added, %d duplicates skipped.", added, skipped)
    return {"found": len(rows), "added": added, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import leads from CSV.")
    parser.add_argument("file", help="Path to CSV file.")
    parser.add_argument(
        "--source",
        choices=list(_SOURCE_MAPS.keys()),
        default=None,
        help="Force CSV format. Auto-detected if omitted.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving.")
    args = parser.parse_args()

    result = import_csv(args.file, source=args.source, dry_run=args.dry_run)
    print(
        f"\nImport result:\n"
        f"  Rows in file : {result['found']}\n"
        f"  Added        : {result['added']}\n"
        f"  Skipped      : {result['skipped']}"
    )


if __name__ == "__main__":
    main()
