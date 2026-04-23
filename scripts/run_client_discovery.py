"""Run Apollo lead discovery campaigns for one or all markets.

Usage:
    PYTHONPATH=. venv/bin/python3 scripts/run_client_discovery.py
    PYTHONPATH=. venv/bin/python3 scripts/run_client_discovery.py --market UK
    PYTHONPATH=. venv/bin/python3 scripts/run_client_discovery.py --market DACH --bypass-limit
    PYTHONPATH=. venv/bin/python3 scripts/run_client_discovery.py --dry-run
    PYTHONPATH=. venv/bin/python3 scripts/run_client_discovery.py --max-pages 4
"""
import argparse
import logging
import sys
import time

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

HOTEL_TITLES = [
    "VP Revenue",
    "Director of Revenue",
    "Chief Commercial Officer",
    "VP Sales",
    "Director of Sales",
    "Head of Commercial",
    "CMO",
    "Chief Marketing Officer",
    "VP Guest Experience",
    "General Manager",
]

EXECUTIVE_TITLES = [
    "Chief Operating Officer",
    "CEO",
    "VP Operations",
    "Managing Director",
]

CAMPAIGNS: dict[str, list[dict]] = {
    "UK": [
        {
            "name": "UK — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["United Kingdom"],
            "industry": "hospitality hotels",
            "max_pages": 8,
        },
        {
            "name": "UK — Hotel Group Executives",
            "titles": EXECUTIVE_TITLES,
            "geography": ["United Kingdom"],
            "industry": "hospitality hotels",
            "min_employees": 100,
            "max_pages": 4,
        },
    ],
    "Australia": [
        {
            "name": "Australia — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["Australia"],
            "industry": "hospitality hotels",
            "max_pages": 6,
        },
        {
            "name": "Australia — Hotel Group Executives",
            "titles": EXECUTIVE_TITLES,
            "geography": ["Australia"],
            "industry": "hospitality hotels",
            "min_employees": 50,
            "max_pages": 3,
        },
    ],
    "UAE": [
        {
            "name": "UAE — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["United Arab Emirates"],
            "industry": "hospitality hotels",
            "max_pages": 6,
        },
    ],
    "India": [
        {
            "name": "India — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["India"],
            "industry": "hospitality hotels",
            "max_pages": 6,
        },
    ],
    "Ireland": [
        {
            "name": "Ireland — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["Ireland"],
            "industry": "hospitality hotels",
            "max_pages": 4,
        },
    ],
    "NZ": [
        {
            "name": "New Zealand — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["New Zealand"],
            "industry": "hospitality hotels",
            "max_pages": 4,
        },
    ],
    "SouthAfrica": [
        {
            "name": "South Africa — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["South Africa"],
            "industry": "hospitality hotels",
            "max_pages": 4,
        },
    ],
    "Singapore": [
        {
            "name": "Singapore — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["Singapore"],
            "industry": "hospitality hotels",
            "max_pages": 4,
        },
    ],
    "HongKong": [
        {
            "name": "Hong Kong — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["Hong Kong"],
            "industry": "hospitality hotels",
            "max_pages": 3,
        },
    ],
    "EastAfrica": [
        {
            "name": "East Africa — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["Kenya", "Tanzania", "Uganda", "Rwanda"],
            "industry": "hospitality hotels",
            "max_pages": 3,
        },
    ],
    "WestAfrica": [
        {
            "name": "West Africa — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["Nigeria", "Ghana", "Ivory Coast", "Senegal"],
            "industry": "hospitality hotels",
            "max_pages": 3,
        },
    ],
    "Philippines": [
        {
            "name": "Philippines — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["Philippines"],
            "industry": "hospitality hotels",
            "max_pages": 3,
        },
    ],
    "MaltaCaribbean": [
        {
            "name": "Malta & Caribbean — Hotel Revenue & Commercial",
            "titles": HOTEL_TITLES,
            "geography": ["Malta", "Jamaica", "Barbados", "Bahamas", "Cayman Islands"],
            "industry": "hospitality hotels",
            "max_pages": 2,
        },
    ],
    # DACH markets
    "DACH": [
        {
            "name": "Germany — Hotel Revenue & Commercial",
            "titles": [
                "Revenue Manager",
                "Director of Revenue",
                "VP Revenue",
                "Commercial Director",
                "Head of Sales",
                "Chief Commercial Officer",
            ],
            "geography": ["Germany"],
            "industry": "hospitality hotels",
            "max_pages": 8,
        },
        {
            "name": "Germany — Hotel CMO & GM",
            "titles": ["CMO", "Chief Marketing Officer", "General Manager", "VP Guest Experience", "VP Sales"],
            "geography": ["Germany"],
            "industry": "hospitality hotels",
            "max_pages": 6,
        },
        {
            "name": "Austria + Switzerland — Hotel Leaders",
            "titles": [
                "Revenue Manager",
                "Director of Revenue",
                "Commercial Director",
                "CMO",
                "General Manager",
                "VP Revenue",
            ],
            "geography": ["Austria", "Switzerland"],
            "industry": "hospitality hotels",
            "max_pages": 4,
        },
        {
            "name": "DACH — Hotel Group Executives",
            "titles": EXECUTIVE_TITLES,
            "geography": ["Germany", "Austria", "Switzerland"],
            "industry": "hospitality hotels",
            "min_employees": 100,
            "max_pages": 4,
        },
    ],
}

ALL_MARKETS = list(CAMPAIGNS.keys())


def _get_daily_limit() -> int:
    from backend.integrations.supabase_client import supabase
    row = supabase.table("system_config").select("value").eq("key", "daily_discovery_limit").single().execute().data
    try:
        return int(row["value"]) if row else 100
    except (TypeError, ValueError):
        return 100


def _count_discovered_today() -> int:
    from backend.integrations.supabase_client import supabase
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date().isoformat()
    result = supabase.table("leads").select("id", count="exact").gte("created_at", today).execute()
    return result.count or 0


def _existing_emails() -> set[str]:
    from backend.integrations.supabase_client import supabase
    rows = supabase.table("leads").select("email").not_.is_("email", "null").execute().data or []
    return {r["email"].lower() for r in rows if r.get("email")}


def _save_leads(leads: list[dict]) -> tuple[int, int]:
    """Insert leads in batches of 100, deduplicating against existing emails.

    Returns:
        (added, skipped) counts.
    """
    from backend.integrations.supabase_client import supabase

    known = _existing_emails()
    to_insert = []
    skipped = 0

    for lead in leads:
        email = (lead.get("email") or "").lower()
        if email and email in known:
            skipped += 1
            continue
        if email:
            known.add(email)
        to_insert.append({
            "first_name": lead.get("first_name", ""),
            "last_name": lead.get("last_name", ""),
            "title": lead.get("title", ""),
            "company": lead.get("company", ""),
            "email": lead.get("email") or None,
            "linkedin_url": lead.get("linkedin_url") or None,
            "location": lead.get("location", ""),
            "source": "apollo",
            "pipeline_stage": "discovered",
        })

    added = 0
    for i in range(0, len(to_insert), 100):
        batch = to_insert[i : i + 100]
        supabase.table("leads").insert(batch).execute()
        added += len(batch)

    return added, skipped


def run_discovery(
    markets: list[str],
    dry_run: bool = False,
    bypass_limit: bool = False,
    max_pages_override: int | None = None,
) -> dict:
    from backend.integrations.apollo_client import search_leads

    if not bypass_limit:
        limit = _get_daily_limit()
        already_found = _count_discovered_today()
        remaining = limit - already_found
        if remaining <= 0:
            logger.info("Daily discovery limit reached (%d). Use --bypass-limit to override.", limit)
            return {"found": 0, "added": 0, "skipped": 0, "campaigns_run": 0}
    else:
        remaining = 999_999

    total_found = 0
    total_added = 0
    total_skipped = 0
    campaigns_run = 0

    for market in markets:
        campaigns = CAMPAIGNS.get(market, [])
        if not campaigns:
            logger.warning("Unknown market: %s — skipping", market)
            continue

        for campaign in campaigns:
            name = campaign["name"]
            titles = campaign["titles"]
            geography = campaign["geography"]
            industry = campaign["industry"]
            min_emp = campaign.get("min_employees", 10)
            pages = max_pages_override or campaign["max_pages"]

            logger.info("Campaign: %s (max_pages=%d)", name, pages)

            try:
                leads = search_leads(
                    job_titles=titles,
                    industry=industry,
                    geography=geography,
                    min_employees=min_emp,
                    max_pages=pages,
                )
            except Exception:
                logger.exception("Apollo search failed for campaign: %s", name)
                continue

            total_found += len(leads)
            campaigns_run += 1

            if dry_run:
                logger.info("  [dry-run] Would add up to %d leads from '%s'", len(leads), name)
                continue

            added, skipped = _save_leads(leads)
            total_added += added
            total_skipped += skipped
            remaining -= added
            logger.info("  Saved %d new leads, skipped %d duplicates", added, skipped)

            if not bypass_limit and remaining <= 0:
                logger.info("Daily limit reached — stopping early.")
                break

            time.sleep(1)

        if not bypass_limit and remaining <= 0:
            break

    return {
        "found": total_found,
        "added": total_added if not dry_run else 0,
        "skipped": total_skipped if not dry_run else 0,
        "campaigns_run": campaigns_run,
        "dry_run": dry_run,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Apollo lead discovery campaigns.")
    parser.add_argument(
        "--market",
        choices=ALL_MARKETS + ["ALL"],
        default="ALL",
        help="Market to run (default: ALL). Options: " + ", ".join(ALL_MARKETS),
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be found without saving.")
    parser.add_argument("--bypass-limit", action="store_true", help="Ignore daily_discovery_limit.")
    parser.add_argument("--max-pages", type=int, default=None, help="Override max_pages for all campaigns.")
    args = parser.parse_args()

    markets = ALL_MARKETS if args.market == "ALL" else [args.market]
    logger.info("Running discovery for markets: %s%s", markets, " [DRY RUN]" if args.dry_run else "")

    result = run_discovery(
        markets=markets,
        dry_run=args.dry_run,
        bypass_limit=args.bypass_limit,
        max_pages_override=args.max_pages,
    )

    print(
        f"\nDiscovery complete:\n"
        f"  Campaigns run : {result['campaigns_run']}\n"
        f"  Leads found   : {result['found']}\n"
        f"  Leads added   : {result['added']}\n"
        f"  Duplicates    : {result['skipped']}\n"
        f"  Dry run       : {result['dry_run']}"
    )


if __name__ == "__main__":
    main()
