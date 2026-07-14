"""Global email suppression list — the do-not-email gate.

Once an address unsubscribes, hard-bounces, or complains it is recorded here and
never emailed again, across all campaigns and all leads sharing that address.
This is enforced in the send path (`sequence_executor.process_due_sequences`)
and in `routers/leads.send_reply`.
"""

import logging

from backend.integrations.supabase_client import supabase

logger = logging.getLogger(__name__)

VALID_REASONS = ("unsubscribe", "bounce", "complaint", "manual")


def _norm(email: str) -> str:
    return (email or "").strip().lower()


def is_suppressed(email: str) -> bool:
    """True if the address is on the suppression list (case-insensitive)."""
    e = _norm(email)
    if "@" not in e:
        return False
    try:
        r = supabase.table("suppression_list").select("id").eq("email", e).limit(1).execute()
        return bool(r.data)
    except Exception:
        # Fail SAFE: if we cannot verify suppression, do not send.
        logger.exception("Suppression check failed for %s — treating as suppressed", e)
        return True


def add_suppression(
    email: str,
    reason: str,
    source_campaign: str | None = None,
    notes: str | None = None,
) -> None:
    """Add an address to the suppression list and skip its pending sequences.

    Idempotent — a second call for an already-suppressed address is a no-op.
    """
    e = _norm(email)
    if "@" not in e:
        return
    if reason not in VALID_REASONS:
        reason = "manual"

    if not is_suppressed(e):
        try:
            supabase.table("suppression_list").insert({
                "email": e,
                "reason": reason,
                "source_campaign": source_campaign,
                "notes": notes,
            }).execute()
            logger.info("Suppressed %s (reason=%s)", e, reason)
        except Exception:
            logger.exception("Failed to insert suppression row for %s", e)

    # Flag any leads with this address and skip their pending sequence steps.
    try:
        leads = supabase.table("leads").select("id").eq("email", e).execute().data or []
        for lead in leads:
            supabase.table("leads").update(
                {"suppressed_at": "now()"}
            ).eq("id", lead["id"]).execute()
            supabase.table("email_sequences").update(
                {"status": "skipped"}
            ).eq("lead_id", lead["id"]).eq("status", "pending").execute()
    except Exception:
        logger.exception("Failed to flag leads / skip sequences for %s", e)
