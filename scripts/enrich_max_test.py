#!/usr/bin/env python3
"""
Max-subscription Haiku enrichment test (100 leads).

Tracks calls and time so we can compute approximate Max session usage.
Watches Redis cooloff key — bails out if Max limit hits.
"""

import json
import sys
import time
import logging
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.utils.anthropic_client import (
    _call_cli,
    HAIKU,
    VybeTradingWindowError,
    _is_vybe_trading_window,
    _get_fw_redis,
    _CLAUDE_COOLOFF_KEY,
)
from backend.integrations.supabase_client import supabase


def force_max_call(system_prompt: str, user_message: str) -> str:
    """Force a Haiku call via Claude Max OAuth CLI (bypass Ollama)."""
    if _is_vybe_trading_window():
        # We bypass for the explicit Max test only (user authorized)
        pass
    return _call_cli(system_prompt, user_message, HAIKU)


classify = force_max_call

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


CLARIFY_PROMPT = """You verify hotel businesses. Respond ONLY with valid JSON:
{"classification": "Verified Hotel Operator" | "Not a Hotel" | "Unclear - needs manual review", "confidence": <0.0-1.0>, "reasoning": "<brief>"}
"""

ENRICH_PROMPT = """You extract hotel business attributes. Respond ONLY with valid JSON:
{"operator_type": "independent|boutique|franchise", "team_size_estimate": "<range>", "pain_points": ["<point>"], "decision_maker_role": "<role>", "region": "<region>"}
"""


def parse_json(response: str) -> dict:
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    return json.loads(response.strip())


def check_cooloff() -> bool:
    """Return True if Claude is in cooloff (don't make calls)."""
    if _get_fw_redis is None:
        return False
    r = _get_fw_redis()
    if r is None:
        return False
    try:
        raw = r.get(_CLAUDE_COOLOFF_KEY)
        return bool(raw)
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output-stats", default="data/phase2/max_test_stats.json")
    parser.add_argument("--save-supabase", action="store_true")
    args = parser.parse_args()

    with open(args.input) as f:
        leads = json.load(f)["leads"][:args.limit]

    logger.info(f"Max-test enrichment: {len(leads)} leads")
    logger.info(f"Watching cooloff key: {_CLAUDE_COOLOFF_KEY}")
    logger.info("")

    stats = {
        "total_leads": len(leads),
        "calls_made": 0,
        "calls_failed": 0,
        "verified": 0,
        "manual_review": 0,
        "rejected": 0,
        "cooloff_hit": False,
        "time_started": time.time(),
        "time_ended": None,
        "elapsed_seconds": 0,
        "avg_call_seconds": 0,
        "per_lead_times": [],
    }

    for i, lead in enumerate(leads, 1):
        if check_cooloff():
            logger.warning(f"⚠️  Cooloff key set — Max limit reached. Stopping at lead {i}/{len(leads)}.")
            stats["cooloff_hit"] = True
            break

        t0 = time.time()
        try:
            user_msg = f"Hotel: {lead['name']}\nAddress: {lead['address']}\nCountry: {lead['country']}\nPhone: {lead.get('phone','')}\nWebsite: {lead.get('website','')}"
            clarify_resp = classify(CLARIFY_PROMPT, user_msg)
            stats["calls_made"] += 1
            clarify = parse_json(clarify_resp)
            classification = clarify.get("classification", "Unknown")

            enrich = None
            if classification == "Verified Hotel Operator" and clarify.get("confidence", 0) >= 0.5:
                enrich_resp = classify(ENRICH_PROMPT, user_msg)
                stats["calls_made"] += 1
                enrich = parse_json(enrich_resp)
                stats["verified"] += 1
            elif classification == "Unclear - needs manual review":
                stats["manual_review"] += 1
            else:
                stats["rejected"] += 1

            t_lead = time.time() - t0
            stats["per_lead_times"].append(t_lead)
            logger.info(f"[{i}/{len(leads)}] {lead['name'][:50]} → {classification} ({t_lead:.1f}s, {stats['calls_made']} calls)")

            if args.save_supabase and enrich:
                try:
                    record = {
                        "first_name": lead["name"].split()[0] if lead["name"] else "Unknown",
                        "last_name": " ".join(lead["name"].split()[1:]) or lead["name"],
                        "title": enrich.get("decision_maker_role", "General Manager"),
                        "phone": lead.get("phone"),
                        "location": f"{lead.get('address')}, {lead.get('country')}",
                        "pipeline_stage": "discovered",
                        "enrichment_data": {
                            "raw_name": lead["name"],
                            "verification_status": "verified_hotel",
                            "classification": clarify,
                            "enrichment": enrich,
                            "source_path": "max_test",
                        },
                        "pain_signals": enrich.get("pain_points", []),
                        "source": "haiku_max_test",
                        "warmth": "cold",
                        "lead_score": int(clarify.get("confidence", 0.5) * 100),
                    }
                    supabase.table("leads").insert(record).execute()
                except Exception as e:
                    logger.warning(f"  Supabase write failed: {e}")

        except VybeTradingWindowError:
            logger.warning("Trading window active — Max OAuth deferred. Stopping.")
            stats["cooloff_hit"] = True
            break
        except Exception as e:
            logger.warning(f"Error at lead {i}: {e}")
            stats["calls_failed"] += 1

    stats["time_ended"] = time.time()
    stats["elapsed_seconds"] = stats["time_ended"] - stats["time_started"]
    if stats["per_lead_times"]:
        stats["avg_call_seconds"] = sum(stats["per_lead_times"]) / len(stats["per_lead_times"])

    Path(args.output_stats).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_stats, "w") as f:
        json.dump(stats, f, indent=2)

    logger.info("")
    logger.info("=== Max Test Stats ===")
    logger.info(f"Calls made: {stats['calls_made']}")
    logger.info(f"Calls failed: {stats['calls_failed']}")
    logger.info(f"Verified: {stats['verified']}, Manual review: {stats['manual_review']}, Rejected: {stats['rejected']}")
    logger.info(f"Elapsed: {stats['elapsed_seconds']:.1f}s ({stats['elapsed_seconds']/60:.1f} min)")
    logger.info(f"Avg per lead: {stats['avg_call_seconds']:.1f}s")
    logger.info(f"Cooloff hit: {stats['cooloff_hit']}")
    logger.info(f"")
    if stats["calls_made"] > 0:
        per_5hr_window = int(stats["calls_made"] * (5*3600) / stats["elapsed_seconds"])
        logger.info(f"Projected calls/5hr session at this pace: ~{per_5hr_window}")
    logger.info(f"✓ Stats written to {args.output_stats}")


if __name__ == "__main__":
    sys.exit(main())
