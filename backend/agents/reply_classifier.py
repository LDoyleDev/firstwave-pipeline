import json
import logging
from backend.utils.anthropic_client import classify

logger = logging.getLogger(__name__)

_SYSTEM = """You are classifying cold email replies for a B2B sales pipeline.
Given a reply snippet and lead context, return a JSON object with:
- outcome: "positive" | "objection" | "question" | "wrong_person" | "out_of_office"
- summary: 1-line plain English summary of what they said
- next_action: suggested next step for the operator

Outcome definitions:
- positive: interested, wants to talk, or asking about next steps
- objection: not interested but gave a reason (price, timing, not their decision, etc.)
- question: wants more information before deciding
- wrong_person: forwarding to someone else, not the right contact
- out_of_office: auto-reply, holiday, or similar

Return valid JSON only, no markdown fences."""


def classify_reply(reply_snippet: str, lead_context: dict) -> dict:
    """Classify an incoming email reply using Claude Haiku.

    Args:
        reply_snippet: The reply text from email_sequences.reply_snippet.
        lead_context: Dict with name, company, title, subject keys.

    Returns:
        {outcome, summary, next_action}
    """
    user_message = (
        f"Lead: {lead_context.get('name', 'Unknown')} at {lead_context.get('company', '')} "
        f"({lead_context.get('title', '')})\n"
        f"Original email subject: {lead_context.get('subject', '')}\n\n"
        f"Reply:\n{reply_snippet}\n\n"
        'Return JSON only: {"outcome": "...", "summary": "...", "next_action": "..."}'
    )

    raw = classify(_SYSTEM, user_message)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("classify_reply failed to parse JSON: %s", raw[:200])
            return {
                "outcome": "question",
                "summary": reply_snippet[:100],
                "next_action": "Review manually in Gmail",
            }
