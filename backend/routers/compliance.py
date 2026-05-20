"""Public compliance endpoints — one-click unsubscribe + manual suppression.

`GET/POST /u/{token}` are reached unauthenticated through the Cloudflare tunnel;
they are the targets of the in-body unsubscribe link and the RFC 8058
`List-Unsubscribe-Post` header set in `gmail_client.send_email`.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from backend.integrations import suppression
from backend.integrations.supabase_client import supabase

logger = logging.getLogger(__name__)
router = APIRouter()

_CONFIRM_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Unsubscribed</title></head>
<body style="font-family:system-ui,sans-serif;max-width:34rem;margin:4rem auto;padding:0 1rem;color:#1a1d2e">
<h2>You've been unsubscribed</h2>
<p>You will receive no further emails from First Wave AI. Thank you.</p>
<p style="color:#666;font-size:.9rem">
How we handle your data: <a href="https://firstwaveai.com/privacy">privacy notice</a>.</p>
</body></html>"""

_UNKNOWN_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Link not recognised</title></head>
<body style="font-family:system-ui,sans-serif;max-width:34rem;margin:4rem auto;padding:0 1rem">
<h2>Link not recognised</h2>
<p>This unsubscribe link is not valid. If you continue to receive unwanted email,
reply with "unsubscribe" and we will remove you.</p>
</body></html>"""


def _process_unsubscribe(token: str) -> bool:
    """Look up the lead by token and suppress its address. Returns False on unknown token."""
    try:
        r = (
            supabase.table("leads")
            .select("id, email")
            .eq("unsubscribe_token", token)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Unsubscribe lookup failed for token %s", token)
        return False
    if not r.data:
        return False
    email = (r.data[0].get("email") or "").strip()
    if email:
        suppression.add_suppression(email, reason="unsubscribe", source_campaign="unsubscribe_link")
    else:
        # No address on the lead yet — still mark it so it is never emailed.
        supabase.table("leads").update({"suppressed_at": "now()"}).eq("id", r.data[0]["id"]).execute()
    logger.info("Unsubscribe processed for lead %s", r.data[0]["id"])
    return True


@router.get("/u/{token}", response_class=HTMLResponse)
def unsubscribe_landing(token: str) -> HTMLResponse:
    """One-click unsubscribe landing page (link target in the email body)."""
    ok = _process_unsubscribe(token)
    return HTMLResponse(content=_CONFIRM_HTML if ok else _UNKNOWN_HTML, status_code=200)


@router.post("/u/{token}", response_class=PlainTextResponse)
def unsubscribe_one_click(token: str) -> PlainTextResponse:
    """RFC 8058 List-Unsubscribe-Post target. Idempotent; always 200."""
    _process_unsubscribe(token)
    return PlainTextResponse(content="unsubscribed", status_code=200)


class SuppressRequest(BaseModel):
    email: str
    reason: str = "manual"
    notes: str | None = None


@router.post("/suppress")
def manual_suppress(body: SuppressRequest) -> dict:
    """Operator endpoint — manually add an address to the suppression list."""
    if "@" not in (body.email or ""):
        raise HTTPException(status_code=400, detail="valid email required")
    suppression.add_suppression(
        body.email, reason=body.reason, source_campaign="manual_ops", notes=body.notes
    )
    return {"status": "suppressed", "email": body.email.strip().lower()}
