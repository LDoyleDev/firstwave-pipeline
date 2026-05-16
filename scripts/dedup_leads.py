#!/usr/bin/env python3
"""
Deduplicate leads using SHA1 hash on (name + address + city).

Conflict resolution: Keep most recent registration, most complete contact.
"""

import json
import sys
import logging
import hashlib
from pathlib import Path
from typing import TypedDict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class Lead(TypedDict):
    name: str
    address: str
    country: str
    phone: str
    website: str | None


def normalize_for_hash(name: str, address: str, city: str) -> str:
    """Normalize strings for dedup hashing."""
    # Remove accents, convert to lowercase, remove punctuation
    import unicodedata

    def remove_accents(text):
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )

    name_norm = remove_accents(name).lower().replace("hotel", "").replace("inn", "").strip()
    address_norm = remove_accents(address).lower().replace(",", " ").split()[0:3]  # First 3 words
    city_norm = remove_accents(city).lower()

    key = f"{name_norm}|{' '.join(address_norm)}|{city_norm}"
    return key


def get_dedup_hash(lead: Lead) -> str:
    """Generate SHA1 hash for dedup."""
    # Extract city from address (last part, usually after last comma)
    address_parts = lead["address"].split(",")
    city = address_parts[-1].strip() if address_parts else ""

    key = normalize_for_hash(lead["name"], lead["address"], city)
    return hashlib.sha1(key.encode()).hexdigest()


def score_lead(lead: Lead) -> int:
    """Score lead completeness for conflict resolution (higher = better)."""
    score = 0
    if lead.get("name"):
        score += 10
    if lead.get("phone"):
        score += 20
    if lead.get("website"):
        score += 10
    if lead.get("address"):
        score += 5
    return score


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Deduplicate leads")
    parser.add_argument("--input", type=str, default="data/phase2_combined.json",
                       help="Input JSON file")
    parser.add_argument("--output", type=str, default="data/phase2_deduped.json",
                       help="Output JSON file")
    parser.add_argument("--verbose", action="store_true",
                       help="Print dedup details")

    args = parser.parse_args()

    logger.info(f"Deduplicating {args.input}")

    # Load input
    with open(args.input) as f:
        data = json.load(f)

    leads = data.get("leads", [])
    logger.info(f"Input: {len(leads)} leads")

    # Group by dedup hash
    groups = {}
    for lead in leads:
        hash_val = get_dedup_hash(lead)
        if hash_val not in groups:
            groups[hash_val] = []
        groups[hash_val].append(lead)

    # Conflict resolution
    deduped_leads = []
    duplicates_removed = 0

    for hash_val, group in groups.items():
        if len(group) == 1:
            deduped_leads.append(group[0])
        else:
            # Multiple records with same hash: keep highest-scoring
            best = max(group, key=score_lead)
            deduped_leads.append(best)
            duplicates_removed += len(group) - 1

            if args.verbose:
                logger.info(f"  Conflict resolved: kept {best['name']} (scored {score_lead(best)})")

    logger.info(f"Duplicates removed: {duplicates_removed}")
    logger.info(f"Output: {len(deduped_leads)} unique leads")

    # Write output
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({"leads": deduped_leads}, f, indent=2)

    logger.info(f"✓ Wrote {len(deduped_leads)} leads to {args.output}")

    # Report dedup rate
    if len(leads) > 0:
        dedup_rate = (duplicates_removed / len(leads)) * 100
        logger.info(f"Dedup rate: {dedup_rate:.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
