import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.integrations.supabase_client import supabase
from backend.integrations import telegram_bot
from backend.integrations.gmail_client import send_email

logger = logging.getLogger(__name__)
router = APIRouter()

BERLIN = ZoneInfo("Europe/Berlin")
SLOT_TIMES = {1: "10:30", 2: "10:50", 3: "11:10"}


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


class MeetingCreate(BaseModel):
    track: str  # 'client' | 'investor'
    slot_number: int  # 1, 2, or 3
    scheduled_at: str  # ISO datetime string
    lead_id: Optional[str] = None
    investor_id: Optional[str] = None
    duration_minutes: int = 20


class MeetingUpdate(BaseModel):
    status: Optional[str] = None
    outcome: Optional[str] = None
    voice_feedback_raw: Optional[str] = None
    feedback_summary: Optional[str] = None
    next_action: Optional[str] = None
    next_action_at: Optional[str] = None
    follow_up_draft: Optional[str] = None
    follow_up_sent: Optional[bool] = None
    briefing_sent: Optional[bool] = None
    briefing_content: Optional[str] = None


@router.get("")
def list_meetings(date_filter: Optional[str] = None) -> list:
    """List meetings with optional date filter (YYYY-MM-DD)."""
    query = supabase.table("meetings").select("*, leads(*), investor_targets(*)").order(
        "scheduled_at"
    )
    if date_filter:
        day_start = f"{date_filter}T00:00:00+00:00"
        day_end = f"{date_filter}T23:59:59+00:00"
        query = query.gte("scheduled_at", day_start).lte("scheduled_at", day_end)
    result = query.execute()
    return result.data


@router.get("/today")
def meetings_today() -> dict:
    """Today's three meeting slots (10:30, 10:50, 11:10 Europe/Berlin) with booking details."""
    now = datetime.now(BERLIN)
    today = now.date()

    day_start = datetime.combine(today, time(0, 0), tzinfo=BERLIN).isoformat()
    day_end = datetime.combine(today, time(23, 59, 59), tzinfo=BERLIN).isoformat()

    result = (
        supabase.table("meetings")
        .select("*, leads(*), investor_targets(*)")
        .gte("scheduled_at", day_start)
        .lte("scheduled_at", day_end)
        .execute()
    )
    meetings_today = result.data

    slots = []
    for slot_num in [1, 2, 3]:
        meeting = next(
            (m for m in meetings_today if m.get("slot_number") == slot_num), None
        )
        slots.append({"slot": slot_num, "time": SLOT_TIMES[slot_num], "meeting": meeting})

    available = sum(1 for s in slots if s["meeting"] is None)
    return {"date": today.isoformat(), "slots": slots, "available_slots": available}


@router.post("", status_code=201)
def create_meeting(meeting: MeetingCreate) -> dict:
    """Create a new meeting record. Enforces slot_number must be 1, 2, or 3."""
    if meeting.slot_number not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="slot_number must be 1, 2, or 3")
    if meeting.track not in ("client", "investor"):
        raise HTTPException(status_code=400, detail="track must be 'client' or 'investor'")
    if meeting.track == "client" and not meeting.lead_id:
        raise HTTPException(status_code=400, detail="lead_id required for client meetings")
    if meeting.track == "investor" and not meeting.investor_id:
        raise HTTPException(status_code=400, detail="investor_id required for investor meetings")

    result = supabase.table("meetings").insert(meeting.model_dump(exclude_none=True)).execute()
    return result.data[0]


@router.post("/{meeting_id}/briefing")
def meeting_briefing(meeting_id: str) -> dict:
    """Generate and store a pre-meeting briefing via the briefing agent."""
    from backend.agents.briefing import generate_briefing
    try:
        briefing = generate_briefing(meeting_id)
        return {"meeting_id": meeting_id, "briefing": briefing}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class FeedbackInput(BaseModel):
    feedback_text: str


@router.post("/{meeting_id}/feedback")
def meeting_feedback(meeting_id: str, body: FeedbackInput) -> dict:
    """Record post-meeting feedback and generate follow-up via the followup agent."""
    from backend.agents.followup import generate_followup
    try:
        result = generate_followup(meeting_id, body.feedback_text)
        return {"meeting_id": meeting_id, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{meeting_id}")
def update_meeting(meeting_id: str, update: MeetingUpdate) -> dict:
    """Update meeting status, outcome, or feedback."""
    payload = update.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    payload["updated_at"] = "now()"
    result = (
        supabase.table("meetings").update(payload).eq("id", meeting_id).execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return result.data[0]


@router.get("/upcoming-briefings")
def upcoming_briefings() -> dict:
    """Return meetings due within 35 minutes that haven't been briefed yet.

    For each meeting found, generates and sends the briefing via Telegram,
    then marks briefing_sent=true. Called by n8n every 10 minutes.
    """
    from backend.agents.briefing import generate_briefing

    now = datetime.now(BERLIN)
    window_end = now + timedelta(minutes=35)

    result = supabase.table("meetings").select(
        "*, leads(first_name, last_name), investor_targets(contact_name, firm_name)"
    ).eq("briefing_sent", False).eq("status", "scheduled").gte(
        "scheduled_at", now.isoformat()
    ).lte("scheduled_at", window_end.isoformat()).execute()

    meetings = result.data or []
    sent = []

    for meeting in meetings:
        meeting_id = meeting["id"]
        track = meeting.get("track", "client")

        if track == "client":
            entity = meeting.get("leads") or {}
            name = f"{entity.get('first_name', '')} {entity.get('last_name', '')}".strip()
        else:
            entity = meeting.get("investor_targets") or {}
            name = entity.get("contact_name") or entity.get("firm_name", "")

        try:
            briefing_text = generate_briefing(meeting_id)
            _send_telegram(f"Pre-meeting briefing — {name}:\n\n{briefing_text}")
            sent.append(meeting_id)
        except Exception:
            logger.exception("Briefing failed for meeting %s", meeting_id)

    return {"checked": len(meetings), "briefings_sent": len(sent), "meeting_ids": sent}


@router.get("/completed-pending-feedback")
def completed_pending_feedback() -> dict:
    """Return meetings that ended 20+ minutes ago with no feedback yet.

    For each, sends a Telegram prompt asking for voice feedback and marks
    the meeting status as 'completed'. Called by n8n every 5 minutes.
    """
    now = datetime.now(BERLIN)
    cutoff = now - timedelta(minutes=20)

    result = supabase.table("meetings").select(
        "*, leads(first_name, last_name, company), investor_targets(contact_name, firm_name)"
    ).eq("status", "scheduled").is_(
        "voice_feedback_raw", "null"
    ).lte("scheduled_at", cutoff.isoformat()).execute()

    meetings = result.data or []
    prompted = []

    for meeting in meetings:
        meeting_id = meeting["id"]
        track = meeting.get("track", "client")

        if track == "client":
            entity = meeting.get("leads") or {}
            name = f"{entity.get('first_name', '')} {entity.get('last_name', '')}".strip()
            company = entity.get("company", "")
        else:
            entity = meeting.get("investor_targets") or {}
            name = entity.get("contact_name") or entity.get("firm_name", "")
            company = entity.get("firm_name", "")

        display = f"{name} at {company}" if company else name

        # Mark as completed so we don't prompt again
        supabase.table("meetings").update({"status": "completed"}).eq("id", meeting_id).execute()

        _send_telegram(
            f"How did the meeting with {display} go?\n"
            f"Send a voice note with your feedback."
        )
        prompted.append(meeting_id)

    return {"checked": len(meetings), "prompted": len(prompted), "meeting_ids": prompted}


@router.post("/{meeting_id}/confirm-followup")
def confirm_followup(meeting_id: str) -> dict:
    """Send the stored follow-up draft email for a meeting after operator confirms.

    Sends the follow_up_draft via Gmail, marks follow_up_sent=true,
    and updates the lead/investor pipeline stage.
    """
    meeting = supabase.table("meetings").select(
        "*, leads(email, first_name, last_name), investor_targets(contact_email, contact_name, firm_name)"
    ).eq("id", meeting_id).single().execute().data

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    draft = meeting.get("follow_up_draft")
    if not draft:
        raise HTTPException(status_code=400, detail="No follow-up draft stored for this meeting")

    if meeting.get("follow_up_sent"):
        raise HTTPException(status_code=400, detail="Follow-up already sent")

    track = meeting.get("track", "client")
    outcome = meeting.get("outcome", "warm")

    if track == "client":
        entity = meeting.get("leads") or {}
        to_email = entity.get("email", "")
        name = f"{entity.get('first_name', '')} {entity.get('last_name', '')}".strip()
        entity_id = meeting.get("lead_id")
        stage_map = {"hot": "follow_up", "warm": "follow_up", "cold": "follow_up", "dead": "closed_lost", "won": "closed_won"}
        new_stage = stage_map.get(outcome, "follow_up")
        table = "leads"
    else:
        entity = meeting.get("investor_targets") or {}
        to_email = entity.get("contact_email", "")
        name = entity.get("contact_name") or entity.get("firm_name", "")
        entity_id = meeting.get("investor_id")
        new_stage = "met"
        table = "investor_targets"

    if not to_email:
        raise HTTPException(status_code=400, detail="No email address found for this meeting attendee")

    gmail_id = send_email(
        to=to_email,
        subject="Following up on our conversation",
        body=draft,
    )

    supabase.table("meetings").update({"follow_up_sent": True}).eq("id", meeting_id).execute()

    if entity_id:
        supabase.table(table).update({"pipeline_stage": new_stage}).eq("id", entity_id).execute()

    _send_telegram(f"Follow-up sent to {name}")

    return {"status": "sent", "to": to_email, "gmail_message_id": gmail_id}
