from datetime import datetime, time, date
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.integrations.supabase_client import supabase

router = APIRouter()

BERLIN = ZoneInfo("Europe/Berlin")
SLOT_TIMES = {1: "10:30", 2: "10:50", 3: "11:10"}


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
