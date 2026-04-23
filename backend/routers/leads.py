from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.integrations.supabase_client import supabase
from backend.integrations import gmail_client

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


class RegenerateReplyRequest(BaseModel):
    feedback: str


@router.post("/{lead_id}/send-reply")
def send_reply(lead_id: str) -> dict:
    """Send the pending reply draft for a lead, threaded to the original conversation."""
    lead = (
        supabase.table("leads")
        .select("email, pending_reply_draft, first_name, last_name")
        .eq("id", lead_id)
        .single()
        .execute()
        .data
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    draft = lead.get("pending_reply_draft", "")
    if not draft:
        raise HTTPException(status_code=400, detail="No pending reply draft for this lead")

    # Thread against the most recent sent sequence
    seq_rows = (
        supabase.table("email_sequences")
        .select("gmail_message_id, subject")
        .eq("lead_id", lead_id)
        .eq("status", "sent")
        .order("sent_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    reply_to_id = seq_rows[0].get("gmail_message_id") if seq_rows else None
    subject = seq_rows[0].get("subject", "") if seq_rows else ""
    if subject and not subject.startswith("Re:"):
        subject = f"Re: {subject}"

    gmail_id = gmail_client.send_email(
        to=lead["email"],
        subject=subject or "Re: Following up",
        body=draft,
        reply_to_message_id=reply_to_id,
    )

    supabase.table("leads").update({"pending_reply_draft": None}).eq("id", lead_id).execute()
    return {"sent": True, "gmail_id": gmail_id}


@router.post("/{lead_id}/regenerate-reply")
def regenerate_reply(lead_id: str, body: RegenerateReplyRequest) -> dict:
    """Re-generate the pending reply draft with operator feedback."""
    lead = supabase.table("leads").select("*").eq("id", lead_id).single().execute().data
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    seq_rows = (
        supabase.table("email_sequences")
        .select("reply_snippet, subject")
        .eq("lead_id", lead_id)
        .not_.is_("reply_snippet", "null")
        .order("sent_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if not seq_rows:
        raise HTTPException(status_code=400, detail="No reply snippet found for this lead")

    reply_snippet = seq_rows[0].get("reply_snippet", "")
    lead_context = {
        "name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
        "company": lead.get("company", ""),
        "title": lead.get("title", ""),
        "subject": seq_rows[0].get("subject", ""),
    }

    from backend.agents.reply_classifier import classify_reply
    from backend.agents.followup import generate_reply_draft

    classification = classify_reply(reply_snippet, lead_context)
    new_draft = generate_reply_draft(lead_id, "client", reply_snippet, classification, feedback=body.feedback)
    supabase.table("leads").update({"pending_reply_draft": new_draft}).eq("id", lead_id).execute()
    return {"draft": new_draft}


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
