from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.integrations.supabase_client import supabase

router = APIRouter()


class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    company_id: Optional[str] = None
    source: Optional[str] = "manual"
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    pipeline_stage: Optional[str] = None
    lead_score: Optional[int] = None
    warmth: Optional[str] = None
    notes: Optional[str] = None
    outreach_approved: Optional[bool] = None
    next_action_at: Optional[str] = None


@router.get("")
def list_leads(pipeline_stage: Optional[str] = None) -> list:
    """List all leads with optional pipeline_stage filter."""
    query = supabase.table("leads").select("*").order("created_at", desc=True)
    if pipeline_stage:
        query = query.eq("pipeline_stage", pipeline_stage)
    result = query.execute()
    return result.data


@router.get("/{lead_id}")
def get_lead(lead_id: str) -> dict:
    """Fetch a single lead by ID."""
    result = supabase.table("leads").select("*").eq("id", lead_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead not found")
    return result.data


@router.post("", status_code=201)
def create_lead(lead: LeadCreate) -> dict:
    """Manually create a new lead record."""
    result = supabase.table("leads").insert(lead.model_dump(exclude_none=True)).execute()
    return result.data[0]


@router.post("/{lead_id}/enrich")
def enrich_lead_endpoint(lead_id: str) -> dict:
    """Trigger enrichment agent for a single lead."""
    from backend.agents.enrichment import enrich_lead
    result = supabase.table("leads").select("*").eq("id", lead_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead not found")
    enrichment = enrich_lead(result.data)
    return {"lead_id": lead_id, "enrichment": enrichment}


@router.post("/enrich-batch")
def enrich_batch_endpoint(lead_ids: list[str]) -> list:
    """Trigger enrichment for up to 5 leads (sequential, rate-limit safe)."""
    from backend.agents.enrichment import enrich_batch
    return enrich_batch(lead_ids)


@router.patch("/{lead_id}")
def update_lead(lead_id: str, update: LeadUpdate) -> dict:
    """Update a lead's stage, score, or notes."""
    payload = update.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    payload["updated_at"] = "now()"
    result = supabase.table("leads").update(payload).eq("id", lead_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead not found")
    return result.data[0]
