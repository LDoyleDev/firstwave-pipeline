"""Run enrichment in batches for discovered leads with no enrichment_data.

Processes in batches of 5 (hard limit per CLAUDE.md), with configurable
sleep between batches. Use --loop to keep running until the queue is empty.

Usage:
    PYTHONPATH=. venv/bin/python3 scripts/run_enrichment_batch.py
    PYTHONPATH=. venv/bin/python3 scripts/run_enrichment_batch.py --generate-outreach --loop
    PYTHONPATH=. venv/bin/python3 scripts/run_enrichment_batch.py --batch-size 5 --sleep-between-batches 60 --loop
"""
import argparse
import logging
import time

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 5  # CLAUDE.md: enrich leads in batches of 5 max


def _fetch_batch(batch_size: int) -> list[dict]:
    from backend.integrations.supabase_client import supabase
    result = (
        supabase.table("leads")
        .select("*")
        .eq("pipeline_stage", "discovered")
        .is_("enrichment_data", "null")
        .order("created_at")
        .limit(batch_size)
        .execute()
    )
    return result.data or []


def run_batch(
    batch_size: int = MAX_BATCH_SIZE,
    generate_outreach: bool = False,
    sleep_between_leads: float = 45.0,
) -> dict:
    from backend.agents.enrichment import enrich_lead
    from backend.agents.outreach import generate_client_outreach

    leads = _fetch_batch(batch_size)
    if not leads:
        return {"processed": 0, "succeeded": 0, "failed": 0, "empty": True}

    succeeded = 0
    failed = 0

    for lead in leads:
        lead_id = lead["id"]
        name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
        logger.info("Enriching: %s (%s)", name, lead.get("company", ""))

        try:
            enrich_lead(lead)
            succeeded += 1
        except Exception:
            logger.exception("Enrichment failed for lead %s", lead_id)
            failed += 1
            time.sleep(sleep_between_leads)
            continue

        if generate_outreach:
            try:
                generate_client_outreach(lead_id)
                logger.info("  Outreach generated for %s", lead_id)
            except Exception:
                logger.warning("Outreach generation failed for %s", lead_id)

        time.sleep(sleep_between_leads)

    return {"processed": len(leads), "succeeded": succeeded, "failed": failed, "empty": False}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run enrichment batches.")
    parser.add_argument("--batch-size", type=int, default=MAX_BATCH_SIZE, help=f"Max {MAX_BATCH_SIZE}.")
    parser.add_argument("--generate-outreach", action="store_true", help="Also generate outreach drafts after enrichment.")
    parser.add_argument("--loop", action="store_true", help="Keep running until queue is empty.")
    parser.add_argument("--sleep-between-batches", type=int, default=60, help="Seconds to sleep between batches (default 60).")
    parser.add_argument("--sleep-between-leads", type=float, default=45.0, help="Seconds between each lead (default 45 — respects Max OAuth rate limits).")
    args = parser.parse_args()

    batch_size = min(args.batch_size, MAX_BATCH_SIZE)
    total_processed = 0
    total_succeeded = 0
    total_failed = 0
    batch_num = 0

    while True:
        batch_num += 1
        logger.info("--- Batch %d ---", batch_num)
        result = run_batch(
            batch_size=batch_size,
            generate_outreach=args.generate_outreach,
            sleep_between_leads=args.sleep_between_leads,
        )

        total_processed += result["processed"]
        total_succeeded += result["succeeded"]
        total_failed += result["failed"]

        if result["empty"]:
            logger.info("Queue empty — all discovered leads have been enriched.")
            break

        logger.info(
            "Batch %d done: %d processed, %d succeeded, %d failed",
            batch_num, result["processed"], result["succeeded"], result["failed"],
        )

        if not args.loop:
            break

        logger.info("Sleeping %ds before next batch...", args.sleep_between_batches)
        time.sleep(args.sleep_between_batches)

    print(
        f"\nEnrichment complete:\n"
        f"  Batches run : {batch_num}\n"
        f"  Processed   : {total_processed}\n"
        f"  Succeeded   : {total_succeeded}\n"
        f"  Failed      : {total_failed}"
    )


if __name__ == "__main__":
    main()
