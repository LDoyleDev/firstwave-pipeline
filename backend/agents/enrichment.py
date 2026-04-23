import json
import logging
from backend.integrations.supabase_client import supabase
from backend.utils.anthropic_client import generate
from backend.prompts.system_prompts import ENRICHMENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def enrich_lead(lead_data: dict) -> dict:
    """Enrich a single lead using Claude Sonnet and update the Supabase record.

    Args:
        lead_data: dict with keys: id, first_name, last_name, title, company,
                   linkedin_url, company_website (id required for DB update)

    Returns:
        Enrichment result dict (also stored in lead record).
    """
    lead_id = lead_data.get("id")
    user_message = (
        f"Enrich this lead:\n"
        f"Name: {lead_data.get('first_name', '')} {lead_data.get('last_name', '')}\n"
        f"Title: {lead_data.get('title', 'Unknown')}\n"
        f"Company: {lead_data.get('company', 'Unknown')}\n"
        f"LinkedIn: {lead_data.get('linkedin_url', 'Not provided')}\n"
        f"Website: {lead_data.get('company_website', 'Not provided')}\n"
        f"\nReturn valid JSON only — no markdown, no explanation."
    )

    raw = generate(ENRICHMENT_SYSTEM_PROMPT, user_message)

    try:
        enrichment = json.loads(raw)
    except json.JSONDecodeError:
        # Strip markdown code fences if present
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            enrichment = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse enrichment JSON for lead %s: %s", lead_id, raw[:200])
            enrichment = {
                "lead_score": 0,
                "warmth": "cold",
                "pain_signals": [],
                "personalisation_hooks": [],
                "company_context": "Enrichment parse error",
                "notes": raw[:500],
            }

    if lead_id:
        update_payload = {
            "enrichment_data": enrichment,
            "lead_score": enrichment.get("lead_score", 0),
            "warmth": enrichment.get("warmth", "cold"),
            "pain_signals": enrichment.get("pain_signals", []),
            "personalisation_hooks": enrichment.get("personalisation_hooks", []),
            "pipeline_stage": "enriched",
        }
        supabase.table("leads").update(update_payload).eq("id", lead_id).execute()
        logger.info("Lead %s enriched — score %s, warmth %s", lead_id, enrichment.get("lead_score"), enrichment.get("warmth"))

    return enrichment


def enrich_batch(lead_ids: list[str]) -> list[dict]:
    """Enrich up to 5 leads sequentially (rate-limit protection).

    Args:
        lead_ids: list of lead UUIDs to enrich (max 5 enforced here)

    Returns:
        List of enrichment result dicts, one per lead.
    """
    if len(lead_ids) > 5:
        logger.warning("enrich_batch called with %d leads — capping at 5", len(lead_ids))
        lead_ids = lead_ids[:5]

    results = []
    for lead_id in lead_ids:
        response = supabase.table("leads").select("*").eq("id", lead_id).single().execute()
        lead = response.data
        if not lead:
            logger.warning("Lead %s not found — skipping", lead_id)
            results.append({"error": f"Lead {lead_id} not found"})
            continue
        result = enrich_lead(lead)
        results.append(result)

    return results
