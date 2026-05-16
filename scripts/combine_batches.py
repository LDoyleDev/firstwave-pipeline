#!/usr/bin/env python3
"""Combine multiple batch JSON files into a single file."""

import json
import sys
import logging
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


def main():
    import argparse
    import glob

    parser = argparse.ArgumentParser(description="Combine batch JSON files")
    parser.add_argument("--inputs", type=str, default="data/phase2_batch_*.json",
                       help="Input file pattern (glob)")
    parser.add_argument("--output", type=str, default="data/phase2_combined.json",
                       help="Output combined JSON file")

    args = parser.parse_args()

    logger.info(f"Combining batches: {args.inputs}")

    # Find all matching files
    input_files = sorted(glob.glob(args.inputs))
    if not input_files:
        logger.error(f"No files matched {args.inputs}")
        return 1

    logger.info(f"Found {len(input_files)} files")

    all_leads = []

    for file_path in input_files:
        logger.info(f"Reading {file_path}")
        try:
            with open(file_path) as f:
                data = json.load(f)

            leads = data.get("leads", [])
            all_leads.extend(leads)
            logger.info(f"  {len(leads)} leads")
        except Exception as e:
            logger.error(f"  Error: {e}")
            return 1

    logger.info(f"Total leads: {len(all_leads)}")

    # Write output
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({"leads": all_leads}, f, indent=2)

    logger.info(f"✓ Wrote {len(all_leads)} leads to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
