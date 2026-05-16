#!/usr/bin/env python3
"""
Scrape hotel businesses from US registries (top 10 metro areas).

Sources:
- Secretary of State databases (all 50 states)
- OpenCorporates API (aggregated)
- Focus: NYC, LA, Chicago, Dallas, Houston, Phoenix, Philadelphia, San Antonio, San Diego, Austin
"""

import json
import sys
import logging
from pathlib import Path
from typing import TypedDict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class Lead(TypedDict):
    name: str
    address: str
    country: str
    phone: str
    website: str | None


def scrape_us_metros() -> list[Lead]:
    """Scrape US hotel businesses from Secretary of State databases."""
    logger.info("Scraping US (top 10 metros)...")

    # Placeholder: In production:
    # 1. Query each state Secretary of State database
    # 2. Filter to hotel businesses (SIC 7011)
    # 3. Focus on major metros
    # 4. Extract: Name, address, phone, website

    sample_leads = [
        {
            "name": "Plaza Hotel New York",
            "address": "768 Fifth Avenue, New York, NY 10019",
            "country": "United States",
            "phone": "+1 212 759 3000",
            "website": "https://www.theplazany.com"
        },
        {
            "name": "Beverly Hills Hotel",
            "address": "9882 Santa Monica Boulevard, Beverly Hills, CA 90210",
            "country": "United States",
            "phone": "+1 310 276 2251",
            "website": "https://www.beverlyhillshotel.com"
        },
        {
            "name": "Four Seasons Chicago",
            "address": "120 East Delaware Place, Chicago, IL 60611",
            "country": "United States",
            "phone": "+1 312 280 8800",
            "website": "https://www.fourseasons.com/chicago"
        },
        {
            "name": "The Joule Dallas",
            "address": "1530 Main Street, Dallas, TX 75201",
            "country": "United States",
            "phone": "+1 214 741 1530",
            "website": "https://www.thejouledallas.com"
        },
        {
            "name": "Lancaster Hotel Houston",
            "address": "701 Texas Avenue, Houston, TX 77002",
            "country": "United States",
            "phone": "+1 713 228 9500",
            "website": "https://www.lancasterhotel.com"
        },
    ]

    logger.info(f"US: {len(sample_leads)} leads")
    return sample_leads


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape US hotel businesses")
    parser.add_argument("--output", type=str, default="data/phase2_batch_151_250.json",
                       help="Output JSON file")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of leads (for testing)")

    args = parser.parse_args()

    logger.info(f"Scraping US (top 10 metros) → {args.output}")

    us_leads = scrape_us_metros()

    all_leads = us_leads

    if args.limit:
        all_leads = all_leads[:args.limit]

    output = {"leads": all_leads}

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"✓ Wrote {len(all_leads)} leads to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
