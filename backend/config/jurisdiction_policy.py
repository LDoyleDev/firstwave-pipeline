"""Per-jurisdiction B2B cold-email policy — config-as-code.

Each country maps to a compliance route. The route drives the send-path gate in
`backend/agents/sequence_executor.py` (via `backend/integrations/jurisdiction.py`):

  A  — Legitimate-interest + opt-out (EU/EEA + opt-out regimes).
       Send permitted with: generic role address, documented LIA, sender ID +
       postal address + working unsubscribe, GDPR Art 14 privacy notice.
  B  — Conspicuous-publication implied consent (Canada/Australia/New Zealand).
       Send permitted ONLY when the address was sourced from the hotel's own
       published contact page (`email_source == 'website_published'`), plus full
       message compliance.
  C  — Prior consent required (Germany/Austria/Switzerland). No compliant
       cold-email route — the first contact must be a non-email channel and
       consent must be logged before any marketing email. Gated out of sends.
  do_not_send — fail-closed: unmapped/unknown jurisdiction, never emailed.

This is a structured framework for self-assessment, not legal advice — see
docs plan `consider-the-work-that-async-snowflake.md`.
"""

DEFAULT_ROUTE = "do_not_send"  # fail-closed for any country not explicitly mapped

# ISO 3166-1 alpha-2 -> route
JURISDICTION_POLICY: dict[str, str] = {
    # Route A — EU/EEA legitimate-interest + opt-out, and opt-out regimes
    "GB": "A", "IE": "A", "FR": "A", "ES": "A", "IT": "A", "NL": "A",
    "BE": "A", "PT": "A", "LU": "A", "DK": "A", "SE": "A", "NO": "A",
    "FI": "A", "IS": "A", "PL": "A", "CZ": "A", "HU": "A", "SK": "A",
    "RO": "A", "BG": "A", "HR": "A", "SI": "A", "EE": "A", "LV": "A",
    "LT": "A", "GR": "A", "CY": "A", "MT": "A", "US": "A",
    # Route B — conspicuous-publication implied consent
    "CA": "B", "AU": "B", "NZ": "B",
    # Route C — prior consent required, no cold-email route
    "DE": "C", "AT": "C", "CH": "C",
    # Serbia — non-EU; B2B position unconfirmed. Fail-closed until assessed.
    "RS": "do_not_send",
}

# Full country name (lowercased) -> ISO alpha-2. Lead rows store English country
# names in `location` / `enrichment_data.country`; this normalises them.
COUNTRY_NAME_TO_ISO: dict[str, str] = {
    "united kingdom": "GB", "uk": "GB", "great britain": "GB", "england": "GB",
    "scotland": "GB", "wales": "GB",
    "ireland": "IE", "france": "FR", "spain": "ES", "italy": "IT",
    "netherlands": "NL", "the netherlands": "NL", "holland": "NL",
    "belgium": "BE", "portugal": "PT", "luxembourg": "LU",
    "denmark": "DK", "sweden": "SE", "norway": "NO", "finland": "FI",
    "iceland": "IS", "poland": "PL", "czech republic": "CZ", "czechia": "CZ",
    "hungary": "HU", "slovakia": "SK", "romania": "RO", "bulgaria": "BG",
    "croatia": "HR", "slovenia": "SI", "estonia": "EE", "latvia": "LV",
    "lithuania": "LT", "greece": "GR", "cyprus": "CY", "malta": "MT",
    "germany": "DE", "austria": "AT", "switzerland": "CH",
    "canada": "CA", "australia": "AU", "new zealand": "NZ",
    "serbia": "RS",
    "united states": "US", "united states of america": "US", "usa": "US", "us": "US",
}
