import json
import logging
from datetime import datetime, timedelta, timezone
from backend.integrations.supabase_client import supabase
from backend.utils.anthropic_client import generate
from backend.prompts.system_prompts import FOLLOWUP_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_OUTCOME_DELAYS = {
    "hot": 1,
    "warm": 4,
    "cold": 14,
    "dead": None,
}


def generate_followup(meeting_id: str, feedback_text: str) -> dict:
    """Generate a follow-up plan and email draft from post-meeting feedback.

    Fetches meeting + lead/investor data, calls Claude Sonnet, updates the
    meeting record, and schedules a follow-up in email_sequences.

    Args:
        meeting_id: UUID of the meeting record.
        feedback_text: Operator's spoken/typed meeting feedback.

    Returns:
        Dict with outcome, next_action, next_action_at, follow_up_draft.
    """
    meeting_resp = supabase.table("meetings").select("*").eq("id", meeting_id).single().execute()
    meeting = meeting_resp.data
    if not meeting:
        raise ValueError(f"Meeting {meeting_id} not found")

    track = meeting.get("track", "client")
    entity_profile = {}

    if track == "client" and meeting.get("lead_id"):
        lead_resp = supabase.table("leads").select("*").eq("id", meeting["lead_id"]).single().execute()
        entity_profile = lead_resp.data or {}
    elif track == "investor" and meeting.get("investor_id"):
        inv_resp = supabase.table("investor_targets").select("*").eq("id", meeting["investor_id"]).single().execute()
        entity_profile = inv_resp.data or {}

    user_message = (
        f"Meeting details:\n{json.dumps(meeting, indent=2, default=str)}\n\n"
        f"Contact profile:\n{json.dumps(entity_profile, indent=2, default=str)}\n\n"
        f"Operator feedback: {feedback_text}\n\n"
        f"Return JSON only:\n"
        f'{{"outcome": "hot|warm|cold|dead", "next_action": "...", "next_action_at": "ISO date", "follow_up_draft": "..."}}'
    )

    raw = generate(FOLLOWUP_SYSTEM_PROMPT, user_message)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse followup JSON for meeting %s: %s", meeting_id, raw[:200])
            result = {
                "outcome": "cold",
                "next_action": "Review manually",
                "next_action_at": None,
                "follow_up_draft": raw[:1000],
            }

    outcome = result.get("outcome", "cold")
    delay_days = _OUTCOME_DELAYS.get(outcome)
    next_action_at = result.get("next_action_at")
    if not next_action_at and delay_days is not None:
        next_action_at = (datetime.now(timezone.utc) + timedelta(days=delay_days)).isoformat()

    supabase.table("meetings").update({
        "outcome": outcome,
        "next_action": result.get("next_action"),
        "next_action_at": next_action_at,
        "follow_up_draft": result.get("follow_up_draft"),
        "status": "completed",
    }).eq("id", meeting_id).execute()

    if outcome != "dead" and entity_profile.get("id") and delay_days is not None:
        scheduled_for = (datetime.now(timezone.utc) + timedelta(days=delay_days)).isoformat()
        entity_id_field = "lead_id" if track == "client" else "investor_id"
        supabase.table("email_sequences").insert({
            entity_id_field: entity_profile["id"],
            "track": track,
            "step": 3,
            "subject": f"Follow-up: {entity_profile.get('company') or entity_profile.get('firm_name', '')}",
            "body": result.get("follow_up_draft", ""),
            "status": "pending",
            "scheduled_for": scheduled_for,
        }).execute()

    logger.info("Follow-up generated for meeting %s — outcome: %s", meeting_id, outcome)
    return result
