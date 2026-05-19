#!/usr/bin/env python3
"""
Audit scraped lead data for potential prompt injection attacks.

Scans all string fields for:
- Known injection phrases ("ignore previous", "system:", etc.)
- Suspicious patterns (excessive newlines, control chars)
- Length anomalies (legitimate hotel fields are bounded)
- Suspicious encoding tricks (zero-width chars, RTL overrides)

Outputs:
- Clean leads → data/phase2/clean_candidates.json
- Quarantined leads → data/phase2/quarantine.json
- Report → stdout + data/phase2/injection_audit_report.json
"""

import json
import sys
import re
import logging
import argparse
from pathlib import Path
from collections import defaultdict, Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# Injection phrase patterns — case-insensitive substring matches
INJECTION_PHRASES = [
    "ignore previous",
    "ignore the previous",
    "ignore all previous",
    "disregard previous",
    "disregard the previous",
    "forget previous",
    "forget the previous",
    "new instructions",
    "new task",
    "your new task",
    "you are now",
    "you must now",
    "system:",
    "assistant:",
    "user:",
    "[system]",
    "[assistant]",
    "<system>",
    "<assistant>",
    "</system>",
    "</user>",
    "override",
    "act as",
    "pretend you are",
    "from now on",
    "instead of",
    "do not classify",
    "do not respond",
    "respond with",
    "always respond",
    "always output",
    "output the following",
    "output exactly",
    "return the following",
    "return exactly",
    "verified hotel",  # output-format mimicry
    '"classification":',  # JSON output mimicry
    '"confidence":',
    "confidence: 1.0",
    "confidence: 0.99",
    "jailbreak",
    "prompt injection",
    "prompt:",
    "prompt =",
    "developer mode",
    "dan mode",
    "anthropic",
    "claude",
    "openai",
    "gpt-",
    "language model",
    "ai assistant",
]

# Suspicious unicode categories
ZERO_WIDTH = "​‌‍⁠﻿"
RTL_OVERRIDE = "‮‭‫‬‪"
CONTROL_CHARS = "".join(chr(c) for c in range(0, 32) if c not in (9, 10, 13))

# Field length thresholds (legitimate hotels rarely exceed)
MAX_LENGTHS = {
    "name": 100,
    "address": 200,
    "phone": 50,
    "website": 300,
    "email": 100,
    "brand": 60,
    "country": 50,
    "stars": 10,
}

FIELDS_TO_CHECK = ["name", "address", "phone", "website", "email", "brand", "country"]


def check_field(value: str, field_name: str) -> list[str]:
    """Return a list of injection signal flags for a single field."""
    flags = []
    if not value or not isinstance(value, str):
        return flags

    lower = value.lower()

    # Phrase matches
    for phrase in INJECTION_PHRASES:
        if phrase in lower:
            flags.append(f"phrase:{phrase}")

    # Excessive newlines (legitimate fields have 0)
    newlines = value.count("\n")
    if newlines > 1:
        flags.append(f"newlines:{newlines}")

    # Control chars (excluding tab/LF/CR)
    if any(c in CONTROL_CHARS for c in value):
        flags.append("control_chars")

    # Zero-width chars
    if any(c in ZERO_WIDTH for c in value):
        flags.append("zero_width")

    # RTL override (used to hide text)
    if any(c in RTL_OVERRIDE for c in value):
        flags.append("rtl_override")

    # Length anomaly
    max_len = MAX_LENGTHS.get(field_name, 500)
    if len(value) > max_len:
        flags.append(f"too_long:{len(value)}>{max_len}")

    # Excessive special chars (suspicious encoding)
    if len(value) > 20:
        special_ratio = sum(1 for c in value if not c.isalnum() and c not in " -.,()/:&'") / len(value)
        if special_ratio > 0.4:
            flags.append(f"special_ratio:{special_ratio:.2f}")

    # JSON-like content in field (mimicking our output)
    if "{" in value and "}" in value and ":" in value and '"' in value:
        flags.append("json_like")

    return flags


def audit_lead(lead: dict) -> dict:
    """Return a per-field flag report for a single lead."""
    report = {"lead": lead, "flags": {}}
    for field in FIELDS_TO_CHECK:
        value = lead.get(field, "")
        flags = check_field(value, field)
        if flags:
            report["flags"][field] = flags
    return report


def main():
    parser = argparse.ArgumentParser(description="Audit leads for prompt injection")
    parser.add_argument("--input", type=str, default="data/phase2/all_candidates.json")
    parser.add_argument("--clean-output", type=str, default="data/phase2/clean_candidates.json")
    parser.add_argument("--quarantine-output", type=str, default="data/phase2/quarantine.json")
    parser.add_argument("--report", type=str, default="data/phase2/injection_audit_report.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logger.info(f"Loading {args.input}")
    with open(args.input) as f:
        data = json.load(f)
    leads = data["leads"]
    logger.info(f"Loaded {len(leads)} leads")

    clean: list[dict] = []
    quarantined: list[dict] = []
    flag_counter: Counter = Counter()
    field_counter: Counter = Counter()
    sample_suspicious: list[dict] = []

    for i, lead in enumerate(leads):
        report = audit_lead(lead)
        if report["flags"]:
            quarantined.append({"lead": lead, "flags": report["flags"]})
            for field, flags in report["flags"].items():
                field_counter[field] += 1
                for flag in flags:
                    flag_type = flag.split(":")[0]
                    flag_counter[flag_type] += 1
            if len(sample_suspicious) < 20:
                sample_suspicious.append({"lead": lead, "flags": report["flags"]})
        else:
            clean.append(lead)

    logger.info("")
    logger.info("=== Audit Report ===")
    logger.info(f"Total leads: {len(leads)}")
    logger.info(f"Clean: {len(clean)} ({100*len(clean)/len(leads):.2f}%)")
    logger.info(f"Quarantined: {len(quarantined)} ({100*len(quarantined)/len(leads):.2f}%)")
    logger.info("")
    logger.info("Flag types triggered:")
    for flag, count in flag_counter.most_common():
        logger.info(f"  {flag}: {count}")
    logger.info("")
    logger.info("Fields most affected:")
    for field, count in field_counter.most_common():
        logger.info(f"  {field}: {count}")
    logger.info("")

    if sample_suspicious:
        logger.info("Sample suspicious entries (first 5):")
        for s in sample_suspicious[:5]:
            logger.info(f"  Name: {s['lead'].get('name', '')[:80]}")
            logger.info(f"  Flags: {s['flags']}")

    Path(args.clean_output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.clean_output, "w") as f:
        json.dump({"leads": clean}, f, indent=2, ensure_ascii=False)
    logger.info(f"")
    logger.info(f"✓ Clean leads → {args.clean_output}")

    with open(args.quarantine_output, "w") as f:
        json.dump({"leads": quarantined}, f, indent=2, ensure_ascii=False)
    logger.info(f"✓ Quarantine → {args.quarantine_output}")

    report = {
        "total": len(leads),
        "clean": len(clean),
        "quarantined": len(quarantined),
        "flag_types": dict(flag_counter.most_common()),
        "fields_affected": dict(field_counter.most_common()),
        "sample_suspicious": sample_suspicious,
    }
    with open(args.report, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"✓ Report → {args.report}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
