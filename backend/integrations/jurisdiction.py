"""Jurisdiction classification for the email send path.

Maps a lead's country (ISO alpha-2 or English name) to a compliance route.
See `backend/config/jurisdiction_policy.py` for the routes and their meaning.
"""

from backend.config.jurisdiction_policy import (
    COUNTRY_NAME_TO_ISO,
    DEFAULT_ROUTE,
    JURISDICTION_POLICY,
)


def to_iso(country: str | None) -> str | None:
    """Normalise a country string (ISO alpha-2 or English name) to ISO alpha-2."""
    if not country:
        return None
    c = country.strip()
    if len(c) == 2 and c.upper() in JURISDICTION_POLICY:
        return c.upper()
    return COUNTRY_NAME_TO_ISO.get(c.lower())


def classify(country: str | None) -> str:
    """Return the compliance route for a country: 'A' | 'B' | 'C' | 'do_not_send'.

    Unmapped / unrecognised countries fail closed to 'do_not_send'.
    """
    iso = to_iso(country)
    if not iso:
        return DEFAULT_ROUTE
    return JURISDICTION_POLICY.get(iso, DEFAULT_ROUTE)


def is_sendable(country: str | None, email_source: str | None) -> tuple[bool, str]:
    """Decide whether the send path may email a lead in this country.

    Returns (allowed, reason). Route A → allowed. Route B → allowed only if the
    address was sourced from a published page. Route C / do_not_send → blocked.
    """
    route = classify(country)
    if route == "A":
        return True, "route_A"
    if route == "B":
        if email_source == "website_published":
            return True, "route_B_published"
        return False, "route_B_requires_published_source"
    if route == "C":
        return False, "route_C_prior_consent_required"
    return False, "do_not_send"
