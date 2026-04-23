import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.integrations.supabase_client import supabase
from backend.integrations import telegram_bot

logger = logging.getLogger(__name__)
router = APIRouter()


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


class DiscoveryFilters(BaseModel):
    titles: list[str] = []
    geography: list[str] = []
    industry: str = "hospitality"
    min_employees: int = 0
    limit: int = 20


class DiscoveryRequest(BaseModel):
    track: str  # 'client' | 'investor'
    source: str  # 'apollo' | 'phantombuster' | 'manual'
    filters: DiscoveryFilters = DiscoveryFilters()
    # For 'manual' source: provide lead data directly
    leads: list[dict] = []
    # For 'phantombuster' source: provide a LinkedIn search URL
    linkedin_search_url: Optional[str] = None


def _deduplicate(new_leads: list[dict]) -> list[dict]:
    """Remove leads that already exist in Supabase (by linkedin_url or email)."""
    unique = []
    for lead in new_leads:
        linkedin_url = lead.get("linkedin_url")
        email = lead.get("email")

        exists = False
        if linkedin_url:
            r = supabase.table("leads").select("id").eq("linkedin_url", linkedin_url).execute()
            exists = bool(r.data)
        if not exists and email:
            r = supabase.table("leads").select("id").eq("email", email).execute()
            exists = bool(r.data)

        if not exists:
            unique.append(lead)

    return unique


@router.post("/discovery/run")
def run_discovery(body: DiscoveryRequest) -> dict:
    """Run a discovery pass for new leads or investors.

    For client track:
      - Fetches from Apollo, PhantomBuster, or accepts manual input
      - Deduplicates against existing Supabase records
      - Creates lead records in 'discovered' stage
      - Triggers enrichment + outreach generation for each new lead
      - Sends Telegram notification with result count

    For investor track:
      - Only 'manual' source is supported (investor list is pre-seeded)
      - Updates stage to 'research_needed' for new targets

    Returns:
        Summary with found, added, and review_queue counts.
    """
    if body.track not in ("client", "investor"):
        raise HTTPException(status_code=400, detail="track must be 'client' or 'investor'")

    if body.track == "investor" and body.source != "manual":
        raise HTTPException(
            status_code=400,
            detail="Investor track only supports 'manual' source — investor list is pre-seeded",
        )

    raw_leads: list[dict] = []

    if body.source == "manual":
        raw_leads = body.leads

    elif body.source == "apollo":
        from backend.integrations.apollo_client import search_leads
        raw_leads = search_leads(
            job_titles=body.filters.titles,
            industry=body.filters.industry,
            min_employees=body.filters.min_employees,
            geography=body.filters.geography,
            limit=min(body.filters.limit, 20),
        )

    elif body.source == "phantombuster":
        if not body.linkedin_search_url:
            raise HTTPException(status_code=400, detail="linkedin_search_url required for phantombuster source")
        from backend.integrations.phantombuster_client import (
            launch_linkedin_search_scraper,
            get_scraper_results,
        )
        container_id = launch_linkedin_search_scraper(
            search_url=body.linkedin_search_url,
            limit=min(body.filters.limit, 25),
        )
        raw_leads = get_scraper_results(container_id)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown source: {body.source}")

    new_leads = _deduplicate(raw_leads)
    added = 0
    review_queue_count = 0

    for lead_data in new_leads:
        # Normalise field names from different sources
        record = {
            "first_name": lead_data.get("first_name") or lead_data.get("firstName", ""),
            "last_name": lead_data.get("last_name") or lead_data.get("lastName", ""),
            "title": lead_data.get("title") or lead_data.get("job_title", ""),
            "email": lead_data.get("email", ""),
            "linkedin_url": lead_data.get("linkedin_url") or lead_data.get("linkedInUrl", ""),
            "phone": lead_data.get("phone", ""),
            "location": lead_data.get("location") or lead_data.get("city", ""),
            "company": lead_data.get("company") or lead_data.get("company_name", ""),
            "company_website": lead_data.get("company_website") or lead_data.get("website", ""),
            "pipeline_stage": "discovered",
            "source": body.source,
        }

        # Create the lead record
        insert_result = supabase.table("leads").insert(record).execute()
        if not insert_result.data:
            logger.warning("Failed to insert lead: %s", record.get("email"))
            continue

        new_lead = insert_result.data[0]
        lead_id = new_lead["id"]
        added += 1

        # Trigger enrichment + outreach generation
        try:
            from backend.agents.enrichment import enrich_lead
            lead_for_enrichment = {**new_lead, "company_website": record.get("company_website", "")}
            enrich_lead(lead_for_enrichment)

            from backend.agents.outreach import generate_client_outreach
            generate_client_outreach(lead_id)
            review_queue_count += 1
        except Exception:
            logger.exception("Enrichment/outreach failed for lead %s", lead_id)

    _send_telegram(
        f"Discovery complete ({body.source})\n"
        f"Found: {len(raw_leads)} | New: {added} | Added to review queue: {review_queue_count}"
    )

    return {
        "found": len(raw_leads),
        "deduplicated": len(raw_leads) - len(new_leads),
        "added": added,
        "review_queue": review_queue_count,
    }


@router.post("/discovery/phantombuster-launch")
def launch_phantombuster_daily() -> dict:
    """Launch the PhantomBuster LinkedIn scraper using the configured default search URL.

    Intended to be called by n8n daily at 06:00 to preserve the 10min/day free quota.
    Results are fetched asynchronously — call /discovery/run with source='phantombuster'
    once results are ready.
    """
    import os
    from backend.integrations.phantombuster_client import launch_linkedin_search_scraper

    default_url = os.getenv("PHANTOMBUSTER_DEFAULT_SEARCH_URL", "")
    if not default_url:
        raise HTTPException(
            status_code=400,
            detail="PHANTOMBUSTER_DEFAULT_SEARCH_URL not set in .env",
        )

    container_id = launch_linkedin_search_scraper(search_url=default_url, limit=25)
    logger.info("PhantomBuster daily launch: container_id=%s", container_id)

    return {"status": "launched", "container_id": container_id}
