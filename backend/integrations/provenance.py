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
) -> dict:
    """Write email + provenance to a lead and derive its jurisdiction_route.

    Args:
        lead_id: UUID of the lead.
        email: the address being attached.
        source: one of VALID_SOURCES — how the address was obtained.
        address_type: generic_role | named_individual (auto-classified if omitted).
        country: optional country (ISO or name) — also (re)derives jurisdiction_route.

    Returns:
        The payload written.
    """
    if "@" not in (email or ""):
        raise ValueError("a valid email address is required")
    if source not in VALID_SOURCES:
        raise ValueError(f"source must be one of {VALID_SOURCES}")

    email = email.strip().lower()
    address_type = address_type or classify_address_type(email)
    if address_type not in VALID_TYPES:
        address_type = classify_address_type(email)

    payload: dict = {
        "email": email,
        "email_source": source,
        "email_sourced_at": datetime.now(timezone.utc).isoformat(),
        "email_address_type": address_type,
    }
    if country:
        payload["country"] = jurisdiction.to_iso(country) or country
        payload["jurisdiction_route"] = jurisdiction.classify(country)

    supabase.table("leads").update(payload).eq("id", lead_id).execute()
    logger.info("Set email for lead %s (source=%s, type=%s)", lead_id, source, address_type)
    return payload
