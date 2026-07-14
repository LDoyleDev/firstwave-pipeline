"""Attach an email address to a lead with full provenance + jurisdiction routing.

Single chokepoint: no path should set `leads.email` without recording where the
address came from and when. That record is the GDPR Article 14 / CASL
implied-consent audit trail.
"""

import logging
from datetime import datetime, timezone

from backend.integrations import jurisdiction
from backend.integrations.supabase_client import supabase

logger = logging.getLogger(__name__)

VALID_SOURCES = ("website_published", "osm_tag", "apollo", "manual")
VALID_TYPES = ("generic_role", "named_individual")

# Local-parts that indicate a role/shared mailbox rather than a named individual.
_GENERIC_LOCALPARTS = {
    "info", "contact", "reservations", "reservation", "hotel", "booking", "stay",
    "mail", "office", "reception", "frontdesk", "front.desk", "hello", "enquiries",
    "enquiry", "sales", "admin", "welcome", "rooms", "stay", "book",
}


def classify_address_type(email: str) -> str:
    """Best-effort generic_role vs named_individual from the local-part."""
    local = email.split("@")[0].strip().lower()
    return "generic_role" if local in _GENERIC_LOCALPARTS else "named_individual"


def set_lead_email(
    lead_id: str,
    email: str,
    source: str,
    address_type: str | None = None,
    country: str | None = None,
    evidence: dict | None = None,
) -> dict:
    """Write email + provenance to a lead and derive its jurisdiction_route.

    Args:
        lead_id: UUID of the lead.
        email: the address being attached.
        source: one of VALID_SOURCES — how the address was obtained.
        address_type: generic_role | named_individual (auto-classified if omitted).
        country: optional country (ISO or name) — also (re)derives jurisdiction_route.
        evidence: optional sourcing-evidence bundle (source_url, source_page_title,
            context_snippet, robots_allowed, optout_disclaimer_seen,
            disclaimer_check_method, html_sha256, snapshot_path, notes). When given
            it is stored on `leads.email_provenance` AND appended to the
            `email_provenance` audit table — the GDPR Art 14 / CASL
            "conspicuous publication" defence trail (see migration 004).

    Returns:
        The payload written to the lead.
    """
    if "@" not in (email or ""):
        raise ValueError("a valid email address is required")
    if source not in VALID_SOURCES:
        raise ValueError(f"source must be one of {VALID_SOURCES}")

    email = email.strip().lower()
    address_type = address_type or classify_address_type(email)
    if address_type not in VALID_TYPES:
        address_type = classify_address_type(email)

    now_iso = datetime.now(timezone.utc).isoformat()
    route: str | None = None

    payload: dict = {
        "email": email,
        "email_source": source,
        "email_sourced_at": now_iso,
        "email_address_type": address_type,
    }
    if country:
        payload["country"] = jurisdiction.to_iso(country) or country
        route = jurisdiction.classify(country)
        payload["jurisdiction_route"] = route

    if evidence:
        # Denormalised latest-provenance summary on the lead row.
        payload["email_provenance"] = {**evidence, "email_source": source, "captured_at": now_iso}

    supabase.table("leads").update(payload).eq("id", lead_id).execute()
    logger.info("Set email for lead %s (source=%s, type=%s)", lead_id, source, address_type)

    if evidence:
        # Append-only audit row. Best-effort — the lead's email_provenance JSONB
        # written above is the durable fallback record if this insert fails.
        try:
            supabase.table("email_provenance").insert({
                "lead_id": lead_id,
                "email": email,
                "email_source": source,
                "email_address_type": address_type,
                "source_url": evidence.get("source_url"),
                "source_page_title": evidence.get("source_page_title"),
                "context_snippet": evidence.get("context_snippet"),
                "robots_allowed": evidence.get("robots_allowed"),
                "optout_disclaimer_seen": evidence.get("optout_disclaimer_seen", False),
                "disclaimer_check_method": evidence.get("disclaimer_check_method"),
                "html_sha256": evidence.get("html_sha256"),
                "snapshot_path": evidence.get("snapshot_path"),
                "jurisdiction_route": route,
                "notes": evidence.get("notes"),
            }).execute()
        except Exception:
            logger.exception("email_provenance audit insert failed for lead %s", lead_id)

    return payload
