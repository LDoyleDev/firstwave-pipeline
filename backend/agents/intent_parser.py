import asyncio
import json
import logging
from datetime import datetime, timezone
from backend.integrations.supabase_client import supabase
from backend.integrations import calcom_client, calendar_client, gmail_client, telegram_bot
from backend.utils.anthropic_client import classify
from backend.prompts.system_prompts import INTENT_PARSER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_FALLBACK_INTENT = {
    "intent": "check_pipeline",
    "track": "both",
    "parameters": {},
    "confidence": 0.0,
    "raw_transcript": "",
}


def parse_voice_intent(transcript: str) -> dict:
    """Parse a voice transcript into a structured intent using Claude Haiku.

    Always returns valid JSON. Logs the command to voice_commands table.

    Args:
        transcript: Raw transcribed text from Groq Whisper.

    Returns:
        Intent dict with keys: intent, track, parameters, confidence, raw_transcript.
    """
    raw = classify(INTENT_PARSER_SYSTEM_PROMPT, transcript)

    try:
        intent = json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            intent = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Intent parse failed for transcript: %s — raw: %s", transcript[:100], raw[:200])
            intent = {**_FALLBACK_INTENT, "raw_transcript": transcript}

    intent["raw_transcript"] = transcript

    try:
        supabase.table("voice_commands").insert({
            "transcript": transcript,
            "parsed_intent": intent,
            "status": "processed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.warning("Failed to log voice command to Supabase: %s", e)

    return intent


def route_intent(intent: dict) -> dict:
    """Route a parsed intent to the appropriate action handler.

    This is the dispatch layer. Each intent is mapped to a concrete action.
    Complex actions (enrich, outreach, meeting booking) call their respective agents.
    Simple read intents return data directly.

    Args:
        intent: Dict returned by parse_voice_intent().

    Returns:
        Dict with keys: success (bool), message (str), data (any).
    """
    intent_name = intent.get("intent", "")
    params = intent.get("parameters", {})
    track = intent.get("track", "both")

    handlers = {
        "check_pipeline": _handle_check_pipeline,
        "review_queue": _handle_review_queue,
        "next_actions": _handle_next_actions,
        "discover_leads": _handle_discover_leads,
        "enrich_lead": _handle_enrich_lead,
        "approve_lead": _handle_approve_lead,
        "reject_lead": _handle_reject_lead,
        "find_investor": _handle_find_investor,
        "book_meeting": _handle_book_meeting,
        "pre_meeting_briefing": _handle_pre_meeting_briefing,
        "post_meeting_feedback": _handle_post_meeting_feedback,
        "send_followup": _handle_send_followup,
        "pause_sequence": _handle_pause_sequence,
        "edit_outreach": _handle_edit_outreach,
        "cancel_meeting": _handle_cancel_meeting,
    }

    handler = handlers.get(intent_name)
    if not handler:
        return {"success": False, "message": f"Unknown intent: {intent_name}", "data": None}

    try:
        return handler(params, track)
    except Exception as e:
        logger.error("Intent handler failed for %s: %s", intent_name, e)
        return {"success": False, "message": f"Action failed: {str(e)}", "data": None}


# --- Intent handlers ---

def _handle_check_pipeline(params: dict, track: str) -> dict:
    leads_resp = supabase.table("leads").select("pipeline_stage").execute()
    leads = leads_resp.data or []
    inv_resp = supabase.table("investor_targets").select("pipeline_stage").execute()
    investors = inv_resp.data or []

    review_count = sum(1 for l in leads if l["pipeline_stage"] == "review_queue")
    active_count = sum(1 for l in leads if l["pipeline_stage"] in ("contacted", "replied"))
    inv_active = sum(1 for i in investors if i["pipeline_stage"] in ("ready_to_contact", "contacted", "replied"))

    msg = (
        f"Pipeline: {len(leads)} leads total, {review_count} in review queue, "
        f"{active_count} active. Investors: {inv_active} active of {len(investors)}."
    )
    return {"success": True, "message": msg, "data": {"leads": len(leads), "review_queue": review_count, "investors_active": inv_active}}


def _handle_review_queue(params: dict, track: str) -> dict:
    leads = supabase.table("leads").select("id,first_name,last_name,company,lead_score").eq("pipeline_stage", "review_queue").execute().data or []
    inv = supabase.table("investor_targets").select("id,firm_name,contact_name,tier").eq("outreach_approved", False).not_.is_("outreach_draft", "null").execute().data or []
    msg = f"Review queue: {len(leads)} client leads, {len(inv)} investor drafts pending approval."
    return {"success": True, "message": msg, "data": {"client": leads, "investor": inv}}


def _handle_next_actions(params: dict, track: str) -> dict:
    review = supabase.table("leads").select("id").eq("pipeline_stage", "review_queue").execute().data or []
    msg = f"Next: {len(review)} leads waiting for approval in review queue."
    return {"success": True, "message": msg, "data": None}


def _handle_discover_leads(params: dict, track: str) -> dict:
    count = params.get("count", 5)
    return {"success": True, "message": f"Discovery queued for {count} leads. Use POST /discovery/run to trigger.", "data": params}


def _handle_enrich_lead(params: dict, track: str) -> dict:
    lead_name = params.get("lead_name")
    if not lead_name:
        return {"success": False, "message": "Lead name required to enrich.", "data": None}
    return {"success": True, "message": f"Enrichment queued for {lead_name}. Use POST /leads/{{id}}/enrich.", "data": params}


def _handle_approve_lead(params: dict, track: str) -> dict:
    lead_name = params.get("lead_name")
    return {"success": True, "message": f"Use POST /review-queue/{{id}}/approve to approve{' ' + lead_name if lead_name else ''}.", "data": params}


def _handle_reject_lead(params: dict, track: str) -> dict:
    lead_name = params.get("lead_name")
    return {"success": True, "message": f"Use POST /review-queue/{{id}}/reject to reject{' ' + lead_name if lead_name else ''}.", "data": params}


def _handle_find_investor(params: dict, track: str) -> dict:
    investor_name = params.get("investor_name") or params.get("lead_name", "")
    if not investor_name:
        return {"success": False, "message": "Investor name required.", "data": None}
    results = supabase.table("investor_targets").select("id,firm_name,tier,contact_name,pipeline_stage").ilike("firm_name", f"%{investor_name}%").execute().data or []
    if not results:
        results = supabase.table("investor_targets").select("id,firm_name,tier,contact_name,pipeline_stage").ilike("contact_name", f"%{investor_name}%").execute().data or []
    msg = f"Found {len(results)} investor(s) matching '{investor_name}'."
    return {"success": True, "message": msg, "data": results}


def _handle_book_meeting(params: dict, track: str) -> dict:
    """Book a meeting: Cal.com + Google Calendar + Supabase meeting record."""
    from datetime import datetime, time as dt_time, timedelta
    from zoneinfo import ZoneInfo

    BERLIN = ZoneInfo("Europe/Berlin")
    SLOT_TIMES = {1: "10:30", 2: "10:50", 3: "11:10"}
    SLOT_HOURS = {1: (10, 30), 2: (10, 50), 3: (11, 10)}

    # Resolve date from natural language
    date_param = str(params.get("date", "tomorrow")).lower()
    now = datetime.now(BERLIN)
    if date_param in ("today", ""):
        meeting_date = now.date()
    elif date_param == "tomorrow":
        meeting_date = (now + timedelta(days=1)).date()
    else:
        try:
            meeting_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            # Fallback to next weekday
            meeting_date = (now + timedelta(days=1)).date()

    # Resolve slot number
    raw_slot = params.get("slot", 1)
    slot_str_map = {"one": 1, "two": 2, "three": 3, "1": 1, "2": 2, "3": 3}
    if isinstance(raw_slot, str):
        slot_number = slot_str_map.get(raw_slot.strip().lower(), 1)
    else:
        slot_number = int(raw_slot) if raw_slot in (1, 2, 3) else 1

    slot_time_str = SLOT_TIMES[slot_number]
    slot_hour, slot_min = SLOT_HOURS[slot_number]
    start_time = datetime.combine(meeting_date, dt_time(slot_hour, slot_min), tzinfo=BERLIN)

    # Resolve attendee from DB
    attendee_name = params.get("attendee_name", "") or params.get("lead_name", "")
    attendee_email = params.get("email", "")
    entity_id = None
    meeting_track = track if track in ("client", "investor") else "client"

    if attendee_name:
        parts = attendee_name.split()
        first = parts[0] if parts else ""
        leads = supabase.table("leads").select("id,first_name,last_name,email").ilike(
            "first_name", f"%{first}%"
        ).execute().data or []
        if leads:
            lead = leads[0]
            attendee_email = lead.get("email", attendee_email)
            entity_id = lead["id"]
            meeting_track = "client"
        else:
            investors = supabase.table("investor_targets").select(
                "id,contact_name,contact_email,firm_name"
            ).ilike("firm_name", f"%{attendee_name}%").execute().data or []
            if not investors:
                investors = supabase.table("investor_targets").select(
                    "id,contact_name,contact_email,firm_name"
                ).ilike("contact_name", f"%{attendee_name}%").execute().data or []
            if investors:
                inv = investors[0]
                attendee_email = inv.get("contact_email", attendee_email)
                entity_id = inv["id"]
                meeting_track = "investor"

    # Cal.com booking
    cal_event_id = None
    try:
        booking = calcom_client.create_booking(
            slot_time=slot_time_str,
            attendee_name=attendee_name or "Guest",
            attendee_email=attendee_email or "",
            notes=f"First Wave AI pipeline meeting — {meeting_track} track",
        )
        cal_event_id = booking.get("cal_event_id")
    except Exception as e:
        logger.warning("Cal.com booking failed: %s", e)

    # Google Calendar event
    google_event_id = None
    try:
        google_event_id = calendar_client.create_event(
            title=f"First Wave AI — {attendee_name or 'Guest'}",
            start_time=start_time,
            duration_minutes=20,
            attendee_email=attendee_email or "",
            description=f"Pipeline meeting ({meeting_track} track). Booked via voice.",
        )
    except Exception as e:
        logger.warning("Google Calendar event creation failed: %s", e)

    # Supabase meeting record
    meeting_data: dict = {
        "track": meeting_track,
        "slot_number": slot_number,
        "scheduled_at": start_time.isoformat(),
        "duration_minutes": 20,
        "status": "scheduled",
    }
    if cal_event_id:
        meeting_data["cal_event_id"] = cal_event_id
    if google_event_id:
        meeting_data["google_event_id"] = google_event_id
    if meeting_track == "client" and entity_id:
        meeting_data["lead_id"] = entity_id
    elif meeting_track == "investor" and entity_id:
        meeting_data["investor_id"] = entity_id

    meeting_result = supabase.table("meetings").insert(meeting_data).execute()
    meeting = meeting_result.data[0] if meeting_result.data else {}

    msg = (
        f"Meeting booked: {attendee_name or 'Guest'} "
        f"at {slot_time_str} on {meeting_date.strftime('%a %d %b')}"
    )
    return {"success": True, "message": msg, "data": meeting}


def _handle_pre_meeting_briefing(params: dict, track: str) -> dict:
    """Show the next meeting briefing."""
    meetings = supabase.table("meetings").select(
        "id, scheduled_at, track, leads(first_name, last_name), investor_targets(contact_name, firm_name)"
    ).eq("status", "scheduled").order("scheduled_at").limit(1).execute().data or []

    if not meetings:
        return {"success": True, "message": "No upcoming meetings scheduled.", "data": None}

    m = meetings[0]
    track_val = m.get("track", "client")
    if track_val == "client":
        entity = m.get("leads") or {}
        name = f"{entity.get('first_name', '')} {entity.get('last_name', '')}".strip()
    else:
        entity = m.get("investor_targets") or {}
        name = entity.get("contact_name") or entity.get("firm_name", "")

    return {
        "success": True,
        "message": f"Next meeting: {name} at {m.get('scheduled_at', '')}. Use POST /meetings/{m['id']}/briefing to generate briefing.",
        "data": m,
    }


def _handle_post_meeting_feedback(params: dict, track: str) -> dict:
    """Process post-meeting voice feedback: generate follow-up draft and send to operator."""
    from backend.agents.followup import generate_followup

    feedback_text = params.get("feedback_text", "")
    if not feedback_text:
        return {"success": False, "message": "No feedback text found in transcript. Please try again.", "data": None}

    # Find the most recently completed meeting without feedback
    meetings = supabase.table("meetings").select("id, track").in_(
        "status", ["completed", "scheduled"]
    ).is_("voice_feedback_raw", "null").order("scheduled_at", desc=True).limit(1).execute().data or []

    if not meetings:
        return {"success": False, "message": "No recent meeting found to attach feedback to.", "data": None}

    meeting_id = meetings[0]["id"]

    try:
        result = generate_followup(meeting_id, feedback_text)
    except Exception as e:
        return {"success": False, "message": f"Failed to generate follow-up: {e}", "data": None}

    draft = result.get("follow_up_draft", "")
    outcome = result.get("outcome", "")

    confirmation_msg = (
        f"Got it. Outcome: {outcome}.\n\n"
        f"Here's your follow-up draft:\n{draft[:600]}\n\n"
        f"Reply YES or type /confirm to send it."
    )

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(telegram_bot.send_operator_message(confirmation_msg))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(telegram_bot.send_operator_message(confirmation_msg))
        finally:
            loop.close()
    except Exception:
        logger.exception("Failed to send confirmation message")

    return {
        "success": True,
        "message": f"Follow-up draft ready (outcome: {outcome}). Reply YES to send.",
        "data": {"meeting_id": meeting_id, "outcome": outcome},
    }


def _handle_send_followup(params: dict, track: str) -> dict:
    """Send the most recent pending follow-up draft after operator confirms."""

    # Find the most recent meeting with a follow_up_draft but follow_up_sent=False
    meetings = supabase.table("meetings").select(
        "*, leads(email, first_name, last_name), investor_targets(contact_email, contact_name, firm_name)"
    ).eq("follow_up_sent", False).not_.is_("follow_up_draft", "null").order(
        "scheduled_at", desc=True
    ).limit(1).execute().data or []

    if not meetings:
        return {"success": False, "message": "No pending follow-ups found.", "data": None}

    meeting = meetings[0]
    meeting_id = meeting["id"]
    meeting_track = meeting.get("track", "client")
    outcome = meeting.get("outcome", "warm")
    draft = meeting.get("follow_up_draft", "")

    if meeting_track == "client":
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
        return {"success": False, "message": "No email address found for this meeting attendee.", "data": None}

    try:
        gmail_client.send_email(
            to=to_email,
            subject="Following up on our conversation",
            body=draft,
        )
    except Exception as e:
        return {"success": False, "message": f"Gmail send failed: {e}", "data": None}

    supabase.table("meetings").update({"follow_up_sent": True}).eq("id", meeting_id).execute()

    if entity_id:
        supabase.table(table).update({"pipeline_stage": new_stage}).eq("id", entity_id).execute()

    msg = f"Follow-up sent to {name}"
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(telegram_bot.send_operator_message(msg))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(telegram_bot.send_operator_message(msg))
        finally:
            loop.close()
    except Exception:
        logger.exception("Failed to send Telegram confirmation")

    return {"success": True, "message": msg, "data": None}


def _handle_pause_sequence(params: dict, track: str) -> dict:
    lead_name = params.get("lead_name")
    return {"success": True, "message": f"Use PATCH /leads/{{id}} with status='paused' to pause sequence{' for ' + lead_name if lead_name else ''}.", "data": params}


def _handle_edit_outreach(params: dict, track: str) -> dict:
    return {"success": True, "message": "Use POST /review-queue/{id}/edit with new_subject and new_body.", "data": params}


def _handle_cancel_meeting(params: dict, track: str) -> dict:
    return {"success": True, "message": "Use DELETE /meetings/{id} to cancel a meeting.", "data": params}
