import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.integrations.supabase_client import supabase
from backend.integrations import telegram_bot

logger = logging.getLogger(__name__)
router = APIRouter()


def _send_telegram(text: str) -> None:
    try:
        asyncio.get_event_loop().run_until_complete(telegram_bot.send_operator_message(text))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(telegram_bot.send_operator_message(text))
        finally:
            loop.close()
    except Exception:
        logger.exception("Telegram send failed")


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------

@router.get("/review-queue")
def get_review_queue() -> dict:
    """Return all leads and investors awaiting outreach approval, ordered by lead_score desc."""
    # Order: chatbot_detected=false first (greenfield opportunities), then by lead_score desc
    client_result = supabase.table("leads").select("*").eq(
        "outreach_approved", False
    ).neq("pipeline_stage", "closed_lost").order("chatbot_detected", desc=False).order("lead_score", desc=True).execute()

    investor_result = supabase.table("investor_targets").select("*").eq(
        "outreach_approved", False
    ).neq("pipeline_stage", "closed").neq("pipeline_stage", "pass").order(
        "tier", desc=False
    ).execute()

    # Annotate each client lead with its compliance route so the operator can see
    # at a glance whether approving it will actually result in a send.
    from backend.integrations import jurisdiction
    client_rows = client_result.data or []
    for row in client_rows:
        row["jurisdiction_route"] = row.get("jurisdiction_route") or jurisdiction.classify(
            row.get("country")
        )

    return {
        "client": client_rows,
        "investor": investor_result.data or [],
        "totals": {
            "client": len(client_result.data or []),
            "investor": len(investor_result.data or []),
        },
    }


class ApproveRequest(BaseModel):
    track: str  # 'client' | 'investor'


@router.post("/review-queue/{entity_id}/approve")
def approve_outreach(entity_id: str, body: ApproveRequest) -> dict:
    """Approve an outreach draft.

    Sets outreach_approved=true, increments system_config counter,
    flips review_mode to 'auto' at 20 approvals, and schedules sequence step 1.
    """
    from backend.agents.sequence_executor import schedule_sequence

    track = body.track
    if track not in ("client", "investor"):
        raise HTTPException(status_code=400, detail="track must be 'client' or 'investor'")

    table = "leads" if track == "client" else "investor_targets"
    update_result = supabase.table(table).update({
        "outreach_approved": True,
    }).eq("id", entity_id).execute()

    if not update_result.data:
        raise HTTPException(status_code=404, detail=f"{track} entity {entity_id} not found")

    # Increment system_config counter
    config_key = f"{track}_outreach_approved_count"
    cfg = supabase.table("system_config").select("value").eq("key", config_key).single().execute()
    current_count = int(cfg.data.get("value", 0)) if cfg.data else 0
    new_count = current_count + 1
    supabase.table("system_config").upsert({
        "key": config_key,
        "value": str(new_count),
    }).execute()

    # Flip to auto mode after 20 approvals
    if new_count >= 20:
        mode_key = f"review_mode_{track}"
        supabase.table("system_config").upsert({
            "key": mode_key,
            "value": "auto",
        }).execute()
        logger.info("Review mode for %s track switched to auto (20 approvals reached)", track)

    # Schedule the email sequence
    try:
        schedule_sequence(entity_id, track)
    except Exception:
        logger.exception("Failed to schedule sequence for %s (%s)", entity_id, track)

    # Telegram confirmation
    row = update_result.data[0]
    if track == "client":
        name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
        company = row.get("company", "")
        _send_telegram(f"Approved: {name} at {company} — sequence scheduled")
    else:
        name = row.get("contact_name") or row.get("firm_name", "")
        company = row.get("firm_name", "")
        tier = row.get("tier", 99)

        # Tier 1 investors: ask about warm intro before sending cold email
        if tier == 1:
            supabase.table("investor_targets").update({
                "pending_intro_check": True,
            }).eq("id", entity_id).execute()
            _send_telegram(
                f"🤝 Before emailing {name} at {company} (Tier 1):\n"
                f"Do you have a warm connection who could intro you?\n\n"
                f"If yes, say: intro via [name]\n"
                f"If no, say: send cold"
            )
        else:
            _send_telegram(f"Approved: {name} at {company} — sequence scheduled")

    return {"status": "approved", "entity_id": entity_id, "total_approved": new_count}


class RejectRequest(BaseModel):
    track: str  # 'client' | 'investor'


@router.post("/review-queue/{entity_id}/reject")
def reject_outreach(entity_id: str, body: RejectRequest) -> dict:
    """Reject an outreach draft and close the entity as lost/passed."""
    track = body.track
    if track not in ("client", "investor"):
        raise HTTPException(status_code=400, detail="track must be 'client' or 'investor'")

    if track == "client":
        result = supabase.table("leads").update({
            "pipeline_stage": "closed_lost",
            "outreach_approved": False,
        }).eq("id", entity_id).execute()
    else:
        result = supabase.table("investor_targets").update({
            "pipeline_stage": "pass",
            "outreach_approved": False,
        }).eq("id", entity_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail=f"{track} entity {entity_id} not found")

    row = result.data[0]
    if track == "client":
        name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
    else:
        name = row.get("contact_name") or row.get("firm_name", "")

    _send_telegram(f"Rejected: {name} — marked as {'closed_lost' if track == 'client' else 'pass'}")

    return {"status": "rejected", "entity_id": entity_id}


class EditRequest(BaseModel):
    track: str  # 'client' | 'investor'
    new_subject: str
    new_body: str
    email_number: int = 1  # 1 or 2


@router.post("/review-queue/{entity_id}/edit")
def edit_outreach(entity_id: str, body: EditRequest) -> dict:
    """Update an outreach draft inline. Does NOT auto-approve — still requires explicit approval."""
    import json

    track = body.track
    if track not in ("client", "investor"):
        raise HTTPException(status_code=400, detail="track must be 'client' or 'investor'")

    if track == "client":
        current = supabase.table("leads").select("*").eq("id", entity_id).single().execute().data
        if not current:
            raise HTTPException(status_code=404, detail=f"Lead {entity_id} not found")

        field = f"outreach_email_{body.email_number}"
        new_draft = json.dumps({"subject": body.new_subject, "body": body.new_body})
        supabase.table("leads").update({field: new_draft}).eq("id", entity_id).execute()
    else:
        current = supabase.table("investor_targets").select("*").eq("id", entity_id).single().execute().data
        if not current:
            raise HTTPException(status_code=404, detail=f"Investor {entity_id} not found")

        existing_raw = current.get("outreach_draft") or "{}"
        try:
            existing = json.loads(existing_raw) if isinstance(existing_raw, str) else existing_raw
        except Exception:
            existing = {}

        key = f"email_{body.email_number}"
        existing[key] = {"subject": body.new_subject, "body": body.new_body}
        supabase.table("investor_targets").update({
            "outreach_draft": json.dumps(existing),
        }).eq("id", entity_id).execute()

    return {"status": "updated", "entity_id": entity_id, "email_number": body.email_number}


# ---------------------------------------------------------------------------
# Sequence processing
# ---------------------------------------------------------------------------

@router.post("/sequences/process")
def process_sequences() -> dict:
    """Send all email sequences that are due now. Called by n8n daily at 08:00."""
    from backend.agents.sequence_executor import process_due_sequences
    return process_due_sequences()


@router.post("/sequences/check-replies")
def check_replies() -> dict:
    """Check all active sent sequences for email replies. Called by n8n every 2 hours."""
    from backend.agents.sequence_executor import check_all_replies
    check_all_replies()
    return {"status": "ok"}


@router.post("/sequences/process-bounces")
def process_bounces_endpoint() -> dict:
    """Scan for delivery-failure notices and suppress hard bounces. Called by n8n."""
    from backend.agents.sequence_executor import process_bounces
    return process_bounces()


@router.get("/sequences")
def list_sequences(
    track: str | None = None,
    status: str | None = None,
    lead_id: str | None = None,
    investor_id: str | None = None,
) -> list:
    """List email sequences with optional filters."""
    query = supabase.table("email_sequences").select("*")
    if track:
        query = query.eq("track", track)
    if status:
        query = query.eq("status", status)
    if lead_id:
        query = query.eq("lead_id", lead_id)
    if investor_id:
        query = query.eq("investor_id", investor_id)
    return query.order("scheduled_for").execute().data or []
