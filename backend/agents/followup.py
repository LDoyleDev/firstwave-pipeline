import json
import logging
from datetime import datetime, timedelta, timezone
from backend.integrations.supabase_client import supabase
from backend.utils.anthropic_client import classify, generate
from backend.prompts.system_prompts import FOLLOWUP_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_CLOSING_SYSTEM = (
    "You are a concise B2B email copywriter. Write plain-text email bodies only — "
    "no subject line, no greeting header, no sign-off. Be brief and direct."
)


def generate_closing_email(entity_id: str, track: str, original_subject: str = "") -> str:
    """Generate a Day 14 closing-the-loop email body using Claude Haiku.

    Args:
        entity_id: UUID of the lead or investor_target.
        track: 'client' or 'investor'.
        original_subject: Subject of the first email in the sequence (for context).

    Returns:
        Plain-text email body string.
    """
    if track == "client":
        row = (
            supabase.table("leads")
            .select("first_name, last_name, company")
            .eq("id", entity_id)
            .single()
            .execute()
            .data or {}
        )
        name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
        company = row.get("company", "")
    else:
        row = (
            supabase.table("investor_targets")
            .select("contact_name, firm_name")
            .eq("id", entity_id)
            .single()
            .execute()
            .data or {}
        )
        name = row.get("contact_name") or row.get("firm_name", "")
        company = row.get("firm_name", "")

    prompt = (
        f"Write a 3-sentence closing-the-loop cold email body to {name} at {company}. "
        f"Original topic: {original_subject}. "
        "This is the final touchpoint — acknowledge it's the last email, keep the door open, "
        "and don't be pushy. Return only the body text."
    )
    return classify(_CLOSING_SYSTEM, prompt)


_REPLY_DRAFT_SYSTEM = (
    "You are a B2B sales email copywriter drafting replies to incoming cold email responses. "
    "Adapt tone and content based on outcome:\n"
    "- positive: enthusiastic, propose specific meeting slots (10:30, 10:50, or 11:10 Berlin time)\n"
    "- objection: acknowledge concern briefly, reframe with one data point, soften the ask\n"
    "- question: answer directly and concisely, then pivot to a call\n"
    "- wrong_person: thank them warmly, ask for an intro to the right person\n"
    "- out_of_office: brief note, reference their return date if given\n"
    "Rules: max 80 words, plain text only, no sign-off, no HTML, first line personalised."
)


def generate_reply_draft(
    entity_id: str,
    track: str,
    reply_snippet: str,
    classification: dict,
    feedback: str = "",
) -> str:
    """Draft a reply to an incoming email reply using Claude Sonnet.

    Args:
        entity_id: UUID of lead or investor_target.
        track: 'client' or 'investor'.
        reply_snippet: The reply text received.
        classification: Output from classify_reply().
        feedback: Optional operator feedback to refine a previous draft.

    Returns:
        Plain-text reply body.
    """
    if track == "client":
        row = (
            supabase.table("leads")
            .select("first_name, last_name, company, title")
            .eq("id", entity_id)
            .single()
            .execute()
            .data or {}
        )
        name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
        company = row.get("company", "")
    else:
        row = (
            supabase.table("investor_targets")
            .select("contact_name, firm_name")
            .eq("id", entity_id)
            .single()
            .execute()
            .data or {}
        )
        name = row.get("contact_name") or row.get("firm_name", "")
        company = row.get("firm_name", "")

    outcome = classification.get("outcome", "question")
    summary = classification.get("summary", "")

    user_message = (
        f"Contact: {name} at {company}\n"
        f"Reply outcome: {outcome}\n"
        f"What they said: {summary}\n"
        f"Reply snippet: {reply_snippet}\n\n"
    )
    if feedback:
        user_message += f"Operator feedback on previous draft: {feedback}\n\n"
    user_message += "Write the reply body now."

    return generate(_REPLY_DRAFT_SYSTEM, user_message)


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
