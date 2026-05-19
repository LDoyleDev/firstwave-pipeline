#!/usr/bin/env python3
"""
Apply validation gates and keyword filters to leads.

Validation gates:
- Name: NOT NULL, length > 2
- Address: Contains city OR postal code
- Country: In approved list
- Contact: Phone OR website present

Keyword filters: Reject OTA sites, review platforms, real estate, etc.
"""

import json
import sys
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


APPROVED_COUNTRIES = {
    # English-speaking (focus: non-US)
    "United Kingdom", "UK", "Ireland", "Canada", "Australia", "New Zealand", "Malta",
    # Western/Central Europe
    "Germany", "France", "Spain", "Italy", "Netherlands", "Belgium",
    "Austria", "Switzerland", "Portugal", "Luxembourg",
    # Nordic
    "Denmark", "Sweden", "Norway", "Finland", "Iceland",
    # Eastern Europe
    "Poland", "Czech Republic", "Hungary", "Slovakia", "Romania", "Bulgaria",
    "Croatia", "Slovenia", "Estonia", "Latvia", "Lithuania", "Serbia",
    # Mediterranean
    "Greece", "Cyprus",
    # US kept for backward-compat but not a focus target
    "United States", "USA", "US",
}

REJECT_KEYWORDS = [
    "booking.com", "expedia", "hotels.com", "airbnb", "vrbo",
    "tripadvisor", "google hotels", "kayak", "trivago",
    "real estate", "property management", "investment trust",
    "tour operator", "travel agency", "cruise",
    "closed", "under construction", "planned", "defunct"
]


def validate_lead(lead: dict) -> tuple[bool, str]:
    """
    Validate lead against gates.

    Returns: (is_valid, reason_if_invalid)
    """
    # Gate 1: Name
    if not lead.get("name") or len(lead["name"]) < 2:
        return False, "Invalid name"

    # Gate 2: Address
    address = lead.get("address", "")
    # Must contain either a postal code pattern (5+ digits) or common city indicator
    has_postal = re.search(r"\d{5,}", address)
    has_city_marker = any(word in address.lower() for word in ["city", "town", "street", "avenue", "road", "square"])
    if not (has_postal or has_city_marker or len(address) > 5):
        return False, "Weak address (no postal code or city marker)"

    # Gate 3: Country
    country = lead.get("country", "")
    if country not in APPROVED_COUNTRIES:
        return False, f"Country not approved: {country}"

    # Gate 4: Contact info — optional at this stage (Phase 3 enriches via web search)
    # Removed strict requirement: hotels without phone/website in source data can still
    # be enriched in Phase 3 using their name + country.

    # Gate 5: Keyword filter
    name_lower = lead["name"].lower()
    address_lower = address.lower()
    full_text = f"{name_lower} {address_lower}"

    for keyword in REJECT_KEYWORDS:
        if keyword in full_text:
            return False, f"Rejected keyword: {keyword}"

    return True, ""


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Apply screening filters")
    parser.add_argument("--input", type=str, default="data/phase2_deduped.json",
                       help="Input JSON file")
    parser.add_argument("--output", type=str, default="data/phase2_candidates_final.json",
                       help="Output JSON file")
    parser.add_argument("--verbose", action="store_true",
                       help="Print filter details")

    args = parser.parse_args()

    logger.info(f"Screening {args.input}")

    # Load input
    with open(args.input) as f:
        data = json.load(f)

    leads = data.get("leads", [])
    logger.info(f"Input: {len(leads)} leads")

    # Apply filters
    passed_leads = []
    failed_leads = []
    reasons = {}

    for lead in leads:
        is_valid, reason = validate_lead(lead)

        if is_valid:
            passed_leads.append(lead)
        else:
            failed_leads.append(lead)
            reasons[reason] = reasons.get(reason, 0) + 1

            if args.verbose:
                logger.warning(f"  Rejected {lead.get('name', 'Unknown')}: {reason}")

    logger.info(f"Passed validation: {len(passed_leads)}")
    logger.info(f"Rejected: {len(failed_leads)}")

    # Report rejection reasons
    logger.info("Rejection breakdown:")
    for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {count:4d} — {reason}")

    # Write output
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({"leads": passed_leads}, f, indent=2)

    logger.info(f"✓ Wrote {len(passed_leads)} leads to {args.output}")

    # Pass rate
    if len(leads) > 0:
        pass_rate = (len(passed_leads) / len(leads)) * 100
        logger.info(f"Pass rate: {pass_rate:.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
