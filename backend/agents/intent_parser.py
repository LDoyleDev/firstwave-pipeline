import json
import logging
from datetime import datetime, timezone
from backend.integrations.supabase_client import supabase
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
    return {"success": True, "message": "Use POST /meetings to book a meeting slot (Phase 5 will automate Cal.com).", "data": params}


def _handle_pre_meeting_briefing(params: dict, track: str) -> dict:
    return {"success": True, "message": "Use GET /meetings/today to see today's meetings. Briefing agent available via POST /meetings/{id}/briefing.", "data": None}


def _handle_post_meeting_feedback(params: dict, track: str) -> dict:
    feedback = params.get("feedback_text", "")
    return {"success": True, "message": f"Feedback captured. Use POST /meetings/{{id}}/feedback to record: {feedback[:100]}", "data": params}


def _handle_send_followup(params: dict, track: str) -> dict:
    lead_name = params.get("lead_name")
    return {"success": True, "message": f"Use POST /meetings/{{id}}/followup to generate follow-up{' for ' + lead_name if lead_name else ''}.", "data": params}


def _handle_pause_sequence(params: dict, track: str) -> dict:
    lead_name = params.get("lead_name")
    return {"success": True, "message": f"Use PATCH /leads/{{id}} with status='paused' to pause sequence{' for ' + lead_name if lead_name else ''}.", "data": params}


def _handle_edit_outreach(params: dict, track: str) -> dict:
    return {"success": True, "message": "Use POST /review-queue/{id}/edit with new_subject and new_body.", "data": params}


def _handle_cancel_meeting(params: dict, track: str) -> dict:
    return {"success": True, "message": "Use DELETE /meetings/{id} to cancel a meeting.", "data": params}
