import json
import logging
import re
from backend.integrations.supabase_client import supabase
from backend.integrations.web_researcher import search_web
from backend.utils.anthropic_client import classify, generate
from backend.prompts.system_prompts import (
    CLIENT_OUTREACH_SYSTEM_PROMPT,
    INVESTOR_OUTREACH_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


def _parse_outreach_json(raw: str, entity_id: str) -> dict:
    """Parse JSON from Claude response, stripping markdown if needed."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse outreach JSON for %s: %s", entity_id, raw[:200])
            return {"error": "parse_failed", "raw": raw[:1000]}


_PLACEHOLDER_RE = re.compile(r'\[([^\]]{3,60})\]')

_PLACEHOLDER_RESOLVER_SYSTEM = (
    "You are a research assistant. Given a placeholder label, web search results, "
    "and context about who the email is for, return ONLY the specific short phrase "
    "that should replace the placeholder — no explanation, no punctuation around it. "
    "If the search results don't contain a confident answer, return the empty string."
)


def _resolve_placeholder(label: str, investor_context: dict) -> str:
    """Web-search for a placeholder value and return the replacement string (or '' if not found)."""
    firm = investor_context.get("firm_name", "")
    contact = investor_context.get("contact_name", "")
    query = f'"{firm}" {label} site:linkedin.com OR site:crunchbase.com OR site:pitchbook.com OR "{firm}" {label}'
    results = search_web(query, max_results=5)
    if not results:
        return ""

    snippets = "\n".join(
        f"- {r.get('title', '')}: {r.get('body', r.get('snippet', ''))}"
        for r in results
    )
    prompt = (
        f"Placeholder to fill: [{label}]\n"
        f"Investor: {contact} at {firm}\n"
        f"Email context: B2B outreach from a hotel AI startup to this investor\n\n"
        f"Search results:\n{snippets}\n\n"
        f"Return only the replacement text for [{label}], e.g. a company name, fund name, or specific fact. "
        f"Keep it concise (2–5 words). If unsure, return empty string."
    )
    result = classify(_PLACEHOLDER_RESOLVER_SYSTEM, prompt).strip().strip('"').strip("'")
    # Reject if the model returned something that looks like a refusal or is too long
    if len(result) > 80 or result.lower().startswith(("i ", "the search", "based on", "i don")):
        return ""
    return result


def resolve_draft_placeholders(draft_text: str, investor_context: dict) -> str:
    """Find all [placeholder] patterns in draft_text and replace with researched values."""
    placeholders = list(dict.fromkeys(_PLACEHOLDER_RE.findall(draft_text)))  # unique, order-preserving
    if not placeholders:
        return draft_text

    for label in placeholders:
        value = _resolve_placeholder(label, investor_context)
        if value:
            logger.info("Resolved [%s] → %s for %s", label, value, investor_context.get("firm_name"))
            draft_text = draft_text.replace(f"[{label}]", value)
        else:
            logger.warning("Could not resolve placeholder [%s] for %s", label, investor_context.get("firm_name"))

    return draft_text


def generate_client_outreach(lead_id: str) -> dict:
    """Generate email drafts for a client lead and store in Supabase.

    Fetches lead + enrichment data, calls Claude Sonnet with CLIENT_OUTREACH_SYSTEM_PROMPT,
    stores email_1 and email_2 drafts, moves stage to 'review_queue'.

    Returns:
        Dict with email_1_subject, email_1_body, email_2_subject, email_2_body.
    """
    response = supabase.table("leads").select("*").eq("id", lead_id).single().execute()
    lead = response.data
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    enrichment = lead.get("enrichment_data") or {}
    user_message = (
        f"Write outreach emails for this lead.\n\n"
        f"Lead:\n"
        f"  Name: {lead.get('first_name', '')} {lead.get('last_name', '')}\n"
        f"  Title: {lead.get('title', 'Unknown')}\n"
        f"  Company: {lead.get('company', 'Unknown')}\n"
        f"  Email: {lead.get('email', 'Unknown')}\n\n"
        f"Enrichment data:\n{json.dumps(enrichment, indent=2)}\n\n"
        f"Return JSON only:\n"
        f'{{"email_1_subject": "...", "email_1_body": "...", "email_2_subject": "...", "email_2_body": "..."}}'
    )

    raw = generate(CLIENT_OUTREACH_SYSTEM_PROMPT, user_message)
    draft = _parse_outreach_json(raw, lead_id)

    if "error" not in draft:
        supabase.table("leads").update({
            "outreach_email_1": json.dumps({
                "subject": draft.get("email_1_subject", ""),
                "body": draft.get("email_1_body", ""),
            }),
            "outreach_email_2": json.dumps({
                "subject": draft.get("email_2_subject", ""),
                "body": draft.get("email_2_body", ""),
            }),
            "pipeline_stage": "review_queue",
            "outreach_approved": False,
        }).eq("id", lead_id).execute()
        logger.info("Client outreach draft generated for lead %s", lead_id)

    return draft


def generate_investor_outreach(investor_id: str) -> dict:
    """Generate outreach draft for an investor target and store in Supabase.

    Fetches investor data, calls Claude Sonnet with INVESTOR_OUTREACH_SYSTEM_PROMPT,
    stores outreach_draft, advances stage to 'ready_to_contact'.

    Returns:
        Dict with email_1_subject, email_1_body, email_2_subject, email_2_body.
    """
    response = supabase.table("investor_targets").select("*").eq("id", investor_id).single().execute()
    investor = response.data
    if not investor:
        raise ValueError(f"Investor {investor_id} not found")

    user_message = (
        f"Write outreach emails for this investor.\n\n"
        f"Investor:\n"
        f"  Firm: {investor.get('firm_name', 'Unknown')}\n"
        f"  Type: {investor.get('investor_type', 'Unknown')}\n"
        f"  Tier: {investor.get('tier', 'Unknown')}\n"
        f"  Contact: {investor.get('contact_name', 'Unknown')}\n"
        f"  Why fit: {investor.get('why_fit', '')}\n"
        f"  Warm path: {investor.get('warm_path', 'None')}\n\n"
        f"Return JSON only:\n"
        f'{{"email_1_subject": "...", "email_1_body": "...", "email_2_subject": "...", "email_2_body": "..."}}'
    )

    raw = generate(INVESTOR_OUTREACH_SYSTEM_PROMPT, user_message)
    draft = _parse_outreach_json(raw, investor_id)

    if "error" not in draft:
        # Resolve any [placeholder] patterns left by the model before saving
        email_1_body = resolve_draft_placeholders(draft.get("email_1_body", ""), investor)
        email_2_body = resolve_draft_placeholders(draft.get("email_2_body", ""), investor)

        combined = json.dumps({
            "email_1": {"subject": draft.get("email_1_subject", ""), "body": email_1_body},
            "email_2": {"subject": draft.get("email_2_subject", ""), "body": email_2_body},
        })
        new_stage = "ready_to_contact" if investor.get("pipeline_stage") == "research_needed" else investor.get("pipeline_stage")
        supabase.table("investor_targets").update({
            "outreach_draft": combined,
            "outreach_approved": False,
            "pipeline_stage": new_stage,
        }).eq("id", investor_id).execute()
        logger.info("Investor outreach draft generated for %s", investor_id)

    return draft


def regenerate_with_feedback(entity_id: str, track: str, feedback: str) -> dict:
    """Regenerate an outreach draft incorporating human feedback.

    Args:
        entity_id: UUID of lead or investor_target
        track: 'client' or 'investor'
        feedback: Free-text feedback from operator (e.g. "too generic, reference their Maldives property")

    Returns:
        New draft dict with email_1_subject, email_1_body, email_2_subject, email_2_body.
    """
    if track == "client":
        response = supabase.table("leads").select("*").eq("id", entity_id).single().execute()
        entity = response.data
        system_prompt = CLIENT_OUTREACH_SYSTEM_PROMPT
        existing_draft = {
            "email_1": entity.get("outreach_email_1", ""),
            "email_2": entity.get("outreach_email_2", ""),
        }
    else:
        response = supabase.table("investor_targets").select("*").eq("id", entity_id).single().execute()
        entity = response.data
        system_prompt = INVESTOR_OUTREACH_SYSTEM_PROMPT
        existing_draft = entity.get("outreach_draft", "")

    if not entity:
        raise ValueError(f"Entity {entity_id} not found in track '{track}'")

    user_message = (
        f"Regenerate the outreach for this entity incorporating the feedback.\n\n"
        f"Entity data:\n{json.dumps(entity, indent=2, default=str)}\n\n"
        f"Existing draft:\n{existing_draft}\n\n"
        f"Operator feedback: {feedback}\n\n"
        f"Return JSON only:\n"
        f'{{"email_1_subject": "...", "email_1_body": "...", "email_2_subject": "...", "email_2_body": "..."}}'
    )

    raw = generate(system_prompt, user_message)
    draft = _parse_outreach_json(raw, entity_id)

    if "error" not in draft:
        if track == "client":
            supabase.table("leads").update({
                "outreach_email_1": json.dumps({
                    "subject": draft.get("email_1_subject", ""),
                    "body": draft.get("email_1_body", ""),
                }),
                "outreach_email_2": json.dumps({
                    "subject": draft.get("email_2_subject", ""),
                    "body": draft.get("email_2_body", ""),
                }),
            }).eq("id", entity_id).execute()
        else:
            supabase.table("investor_targets").update({
                "outreach_draft": json.dumps({
                    "email_1": {"subject": draft.get("email_1_subject", ""), "body": draft.get("email_1_body", "")},
                    "email_2": {"subject": draft.get("email_2_subject", ""), "body": draft.get("email_2_body", "")},
                }),
            }).eq("id", entity_id).execute()
        logger.info("Outreach regenerated with feedback for %s (%s)", entity_id, track)

    return draft


_REENGAGEMENT_SYSTEM = (
    "You are a B2B cold email copywriter writing re-engagement emails. "
    "The prospect was contacted 30+ days ago and did not reply. "
    "Use one of these angles depending on what fits best: "
    "(1) a new relevant stat or data point, "
    "(2) a seasonal or timely hook, "
    "(3) an explicit closing-the-loop ('I don't want to keep emailing if now isn't the right time'). "
    "Max 60 words for the body. Return JSON only: "
    '{"subject": "...", "body": "..."}'
)


def generate_reengagement_email(lead_id: str) -> dict:
    """Generate a re-engagement email for a cold lead using Claude Haiku.

    Args:
        lead_id: UUID of the lead.

    Returns:
        Dict with subject and body strings.
    """
    lead = (
        supabase.table("leads")
        .select("first_name, last_name, company, title, outreach_email_1")
        .eq("id", lead_id)
        .single()
        .execute()
        .data or {}
    )
    name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    company = lead.get("company", "")

    # Get original subject for context
    original_subject = ""
    raw = lead.get("outreach_email_1")
    if raw:
        try:
            e1 = json.loads(raw) if isinstance(raw, str) else raw
            original_subject = e1.get("subject", "")
        except Exception:
            pass

    prompt = (
        f"Lead: {name} at {company} ({lead.get('title', '')})\n"
        f"Original email subject: {original_subject}\n"
        f"They did not reply to 3 emails. Write a re-engagement email now."
    )

    raw_response = classify(_REENGAGEMENT_SYSTEM, prompt)
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        cleaned = raw_response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse reengagement JSON for %s: %s", lead_id, raw_response[:200])
            return {
                "subject": f"Following up — {company}",
                "body": "I wanted to check in one more time. If now isn't the right time, no worries at all. Happy to reconnect whenever makes sense.",
            }
