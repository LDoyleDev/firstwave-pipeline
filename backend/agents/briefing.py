import json
import logging
from backend.integrations.supabase_client import supabase
from backend.utils.anthropic_client import generate
from backend.prompts.system_prompts import BRIEFING_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def generate_briefing(meeting_id: str) -> str:
    """Generate a pre-meeting briefing and store it in the meeting record.

    Fetches meeting + lead/investor full profile, calls Claude Sonnet with
    BRIEFING_SYSTEM_PROMPT, stores the result in meeting.briefing_content,
    and marks briefing_sent = True.

    Args:
        meeting_id: UUID of the meeting record.

    Returns:
        Formatted briefing text (Telegram-friendly, under 300 words).
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

    meeting_time = meeting.get("scheduled_at", "")
    user_message = (
        f"Generate a pre-meeting briefing.\n\n"
        f"Meeting time: {meeting_time}\n"
        f"Track: {track}\n\n"
        f"Contact profile:\n{json.dumps(entity_profile, indent=2, default=str)}\n\n"
        f"Return the briefing as formatted text (no JSON). Keep under 300 words."
    )

    briefing = generate(BRIEFING_SYSTEM_PROMPT, user_message)

    supabase.table("meetings").update({
        "briefing_content": briefing,
        "briefing_sent": True,
    }).eq("id", meeting_id).execute()

    logger.info("Briefing generated for meeting %s (%s)", meeting_id, track)
    return briefing
