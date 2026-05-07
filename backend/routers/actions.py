"""Actions router — trigger pipeline operations from the dashboard or n8n."""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.integrations.supabase_client import supabase
from backend.utils.anthropic_client import ollama_available

logger = logging.getLogger(__name__)
router = APIRouter()


class DiscoverRequest(BaseModel):
    market: str = "UK"
    max_pages: int = 2


class EnrichBatchRequest(BaseModel):
    batch_size: int = 5


class OutreachBatchRequest(BaseModel):
    batch_size: int = 10
    track: str = "client"


@router.get("/queue-stats")
def queue_stats() -> dict:
    """Return counts of leads waiting at each pipeline action stage."""
    # Unenriched discovered leads
    unenriched = (
        supabase.table("leads")
        .select("id", count="exact")
        .eq("pipeline_stage", "discovered")
        .is_("enrichment_data", "null")
        .execute()
    )

    # Enriched but no outreach draft yet
    no_draft = (
        supabase.table("leads")
        .select("id", count="exact")
        .eq("pipeline_stage", "enriched")
        .is_("outreach_email_1", "null")
        .execute()
    )

    # In review queue
    review = (
        supabase.table("leads")
        .select("id", count="exact")
        .eq("pipeline_stage", "review_queue")
        .execute()
    )

    # Emails sent today
    from datetime import datetime, timezone
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    sent_today = (
        supabase.table("email_sequences")
        .select("id", count="exact")
        .eq("status", "sent")
        .gte("sent_at", today_start)
        .execute()
    )

    # Daily send limit from config
    cfg = supabase.table("system_config").select("value").eq("key", "daily_send_limit").single().execute()
    daily_limit = int(cfg.data.get("value", 20)) if cfg.data else 20

    return {
        "discovered_unenriched": unenriched.count or 0,
        "enriched_no_draft": no_draft.count or 0,
        "review_queue": review.count or 0,
        "daily_sends_today": sent_today.count or 0,
        "daily_limit": daily_limit,
    }


@router.post("/discover")
def discover(body: DiscoverRequest) -> dict:
    """Run Apollo discovery for a specific market."""
    from scripts.run_client_discovery import run_discovery

    result = run_discovery(
        markets=[body.market],
        dry_run=False,
        bypass_limit=False,
        max_pages_override=body.max_pages,
    )
    return result


@router.post("/enrich-batch")
def enrich_batch(body: EnrichBatchRequest) -> dict:
    """Enrich the next N discovered leads (max 5)."""
    if not ollama_available():
        logger.warning("enrich-batch skipped — Ollama unavailable")
        return {"skipped": True, "reason": "Ollama unavailable"}

    from backend.agents.enrichment import enrich_lead
    from backend.integrations.supabase_client import supabase as sb
    import time

    batch_size = min(body.batch_size, 5)
    rows = (
        sb.table("leads")
        .select("*")
        .eq("pipeline_stage", "discovered")
        .is_("enrichment_data", "null")
        .order("created_at")
        .limit(batch_size)
        .execute()
        .data or []
    )

    succeeded = 0
    failed = 0
    for lead in rows:
        try:
            enrich_lead(lead)
            succeeded += 1
        except Exception:
            logger.exception("Enrich failed for lead %s", lead["id"])
            failed += 1
        time.sleep(1)

    return {"processed": len(rows), "succeeded": succeeded, "failed": failed}


@router.post("/generate-outreach-batch")
def generate_outreach_batch(body: OutreachBatchRequest) -> dict:
    """Generate outreach drafts for enriched leads not yet in review queue."""
    if not ollama_available():
        logger.warning("generate-outreach-batch skipped — Ollama unavailable")
        return {"skipped": True, "reason": "Ollama unavailable"}

    from backend.agents.outreach import generate_client_outreach, generate_investor_outreach

    if body.track == "client":
        rows = (
            supabase.table("leads")
            .select("id")
            .eq("pipeline_stage", "enriched")
            .is_("outreach_email_1", "null")
            .order("lead_score", desc=True)
            .limit(body.batch_size)
            .execute()
            .data or []
        )
        fn = generate_client_outreach
    else:
        rows = (
            supabase.table("investor_targets")
            .select("id")
            .is_("outreach_draft", "null")
            .eq("pipeline_stage", "research_needed")
            .order("tier")
            .limit(body.batch_size)
            .execute()
            .data or []
        )
        fn = generate_investor_outreach

    added = 0
    failed = 0
    for row in rows:
        try:
            fn(row["id"])
            added += 1
        except Exception:
            logger.exception("Outreach gen failed for %s", row["id"])
            failed += 1

    return {"processed": len(rows), "added_to_queue": added, "failed": failed}


@router.post("/trigger-reengagement")
def trigger_reengagement() -> dict:
    """Identify cold leads and create re-engagement sequence steps for review."""
    from backend.agents.sequence_executor import identify_reengagement_candidates
    from backend.agents.outreach import generate_reengagement_email
    from datetime import datetime, timezone

    candidates = identify_reengagement_candidates(days_cold=30)
    if not candidates:
        return {"queued": 0, "message": "No re-engagement candidates found."}

    queued = 0
    for lead_id in candidates:
        try:
            draft = generate_reengagement_email(lead_id)
            supabase.table("email_sequences").insert({
                "lead_id": lead_id,
                "track": "client",
                "step_number": 4,
                "step_type": "reengagement",
                "subject": draft.get("subject", "Re-engagement"),
                "body": draft.get("body", ""),
                "scheduled_for": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
            }).execute()
            supabase.table("leads").update({
                "reengagement_sent_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", lead_id).execute()
            queued += 1
        except Exception:
            logger.exception("Re-engagement failed for lead %s", lead_id)

    return {"queued": queued, "candidates_found": len(candidates)}


@router.post("/enrich-investors-batch")
def enrich_investors_batch() -> dict:
    """Enrich all investor targets sitting at 'identified' with no enrichment data yet."""
    if not ollama_available():
        logger.warning("enrich-investors-batch skipped — Ollama unavailable")
        return {"skipped": True, "reason": "Ollama unavailable"}

    from backend.agents.enrichment import enrich_investor
    import time

    rows = (
        supabase.table("investor_targets")
        .select("*")
        .eq("pipeline_stage", "identified")
        .is_("enrichment_data", "null")
        .order("tier")
        .limit(5)
        .execute()
        .data or []
    )

    succeeded = 0
    failed = 0
    for investor in rows:
        try:
            enrich_investor(investor)
            succeeded += 1
        except Exception:
            logger.exception("Enrich failed for investor %s", investor["id"])
            failed += 1
        time.sleep(1)

    return {"processed": len(rows), "succeeded": succeeded, "failed": failed}


@router.post("/generate-investor-outreach-batch")
def generate_investor_outreach_batch() -> dict:
    """Generate outreach drafts for all enriched investor targets that have no draft yet."""
    if not ollama_available():
        logger.warning("generate-investor-outreach-batch skipped — Ollama unavailable")
        return {"skipped": True, "reason": "Ollama unavailable"}

    from backend.agents.outreach import generate_investor_outreach

    rows = (
        supabase.table("investor_targets")
        .select("id")
        .eq("pipeline_stage", "research_needed")
        .is_("outreach_draft", "null")
        .order("tier")
        .execute()
        .data or []
    )

    added = 0
    failed = 0
    for row in rows:
        try:
            generate_investor_outreach(row["id"])
            added += 1
        except Exception:
            logger.exception("Outreach gen failed for investor %s", row["id"])
            failed += 1

    return {"processed": len(rows), "added_to_queue": added, "failed": failed}
