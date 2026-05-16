#!/usr/bin/env python3
"""
Split a leads JSON file into range-based chunks for parallel processing.

Example: Split 1200 leads into 5 chunks of 250 leads each for 5 shells.
"""

import json
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Split leads into range-based chunks")
    parser.add_argument("--input", type=str, required=True,
                       help="Input JSON file")
    parser.add_argument("--range", type=str, required=True,
                       help="Range as start:end (e.g., 0:250, 250:500)")
    parser.add_argument("--output", type=str, required=True,
                       help="Output JSON file")

    args = parser.parse_args()

    # Parse range
    try:
        start, end = map(int, args.range.split(":"))
    except (ValueError, IndexError):
        logger.error(f"Invalid range format: {args.range} (expected start:end)")
        return 1

    logger.info(f"Splitting {args.input}[{start}:{end}] → {args.output}")

    # Load input
    with open(args.input) as f:
        data = json.load(f)

    all_leads = data.get("leads", [])
    logger.info(f"Total leads in input: {len(all_leads)}")

    # Extract range
    chunk = all_leads[start:end]
    logger.info(f"Extracted range [{start}:{end}]: {len(chunk)} leads")

    if not chunk:
        logger.warning("Extracted chunk is empty!")
        return 1

    # Write output
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({"leads": chunk}, f, indent=2)

    logger.info(f"✓ Wrote {len(chunk)} leads to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
