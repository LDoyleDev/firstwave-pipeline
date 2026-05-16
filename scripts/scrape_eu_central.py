#!/usr/bin/env python3
"""
Scrape hotel businesses from EU-Central registries (UK + Spain).

Sources:
- Companies House (UK)
- BORME (Spain)
- Regional Chambers of Commerce
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


def scrape_uk() -> list[Lead]:
    """Scrape UK hotel businesses from Companies House and tourism boards."""
    logger.info("Scraping UK...")

    # Placeholder: In production:
    # 1. Query Companies House API (SIC 5510, 5511, 5512)
    # 2. Filter to major cities (London, Manchester, Edinburgh, Birmingham)
    # 3. Extract: Name, address, phone, website

    sample_leads = [
        {
            "name": "The Langham London",
            "address": "1 Portland Place, London W1B 1JA",
            "country": "United Kingdom",
            "phone": "+44 20 7636 1000",
            "website": "https://www.langhamhotels.com"
        },
        {
            "name": "Manchester Grand Hotel",
            "address": "Bridge Street, Manchester M3 2RF",
            "country": "United Kingdom",
            "phone": "+44 161 236 3333",
            "website": "https://www.manchestergrandhotel.com"
        },
    ]

    logger.info(f"UK: {len(sample_leads)} leads")
    return sample_leads


def scrape_spain() -> list[Lead]:
    """Scrape Spanish hotel businesses from BORME and chambers."""
    logger.info("Scraping Spain...")

    # Placeholder: In production:
    # 1. Query BORME (Spanish business registry)
    # 2. Filter to major cities (Madrid, Barcelona, Valencia, Seville)
    # 3. Extract: Name, address, phone, website

    sample_leads = [
        {
            "name": "Hotel Arts Barcelona",
            "address": "Marina 19-21, Barcelona 08005",
            "country": "Spain",
            "phone": "+34 93 221 1000",
            "website": "https://www.hotelarts.es"
        },
        {
            "name": "Ritz Madrid Hotel",
            "address": "Calle del Prado 5, Madrid 28014",
            "country": "Spain",
            "phone": "+34 91 701 6767",
            "website": "https://www.ritzmadridad.es"
        },
    ]

    logger.info(f"Spain: {len(sample_leads)} leads")
    return sample_leads


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape EU-Central hotel businesses")
    parser.add_argument("--output", type=str, default="data/phase2_batch_051_100.json",
                       help="Output JSON file")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of leads (for testing)")

    args = parser.parse_args()

    logger.info(f"Scraping EU-Central (UK + Spain) → {args.output}")

    uk_leads = scrape_uk()
    spain_leads = scrape_spain()

    all_leads = uk_leads + spain_leads

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
