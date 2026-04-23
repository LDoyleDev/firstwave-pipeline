from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.integrations.supabase_client import supabase

router = APIRouter()


class InvestorUpdate(BaseModel):
    pipeline_stage: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_linkedin: Optional[str] = None
    warm_path: Optional[str] = None
    outreach_draft: Optional[str] = None
    outreach_approved: Optional[bool] = None
    notes: Optional[str] = None
    next_action_at: Optional[str] = None


@router.get("")
def list_investors(
    tier: Optional[int] = None,
    pipeline_stage: Optional[str] = None,
) -> list:
    """List investor targets with optional tier and stage filters."""
    query = supabase.table("investor_targets").select("*").order("tier").order("firm_name")
    if tier is not None:
        query = query.eq("tier", tier)
    if pipeline_stage:
        query = query.eq("pipeline_stage", pipeline_stage)
    result = query.execute()
    return result.data


@router.get("/{investor_id}")
def get_investor(investor_id: str) -> dict:
    """Fetch a single investor target by ID."""
    result = (
        supabase.table("investor_targets")
        .select("*")
        .eq("id", investor_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Investor not found")
    return result.data


@router.post("/{investor_id}/enrich")
def enrich_investor_endpoint(investor_id: str) -> dict:
    """Trigger enrichment agent for a single investor target."""
    from backend.agents.enrichment import enrich_investor
    result = supabase.table("investor_targets").select("*").eq("id", investor_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Investor not found")
    enrichment = enrich_investor(result.data)
    return {"investor_id": investor_id, "enrichment": enrichment}


@router.post("/{investor_id}/generate-outreach")
def generate_investor_outreach_endpoint(investor_id: str) -> dict:
    """Generate email drafts for a single investor target."""
    from backend.agents.outreach import generate_investor_outreach
    result = supabase.table("investor_targets").select("id").eq("id", investor_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Investor not found")
    draft = generate_investor_outreach(investor_id)
    return {"investor_id": investor_id, "draft": draft}


@router.patch("/{investor_id}")
def update_investor(investor_id: str, update: InvestorUpdate) -> dict:
    """Update an investor target record."""
    payload = update.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    payload["updated_at"] = "now()"
    result = (
        supabase.table("investor_targets")
        .update(payload)
        .eq("id", investor_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Investor not found")
    return result.data[0]
