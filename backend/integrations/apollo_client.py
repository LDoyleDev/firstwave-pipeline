import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
BASE_URL = "https://api.apollo.io/v1"
_HEADERS = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
_RATE_LIMIT_DELAY = 2.0  # seconds between requests — Apollo free tier rate limit


def find_person_email(
    first_name: str,
    last_name: str,
    company_domain: str,
) -> Optional[str]:
    """Look up a person's work email via Apollo enrichment.

    Args:
        first_name: Person's first name.
        last_name: Person's last name.
        company_domain: Company domain (e.g. "grandhotelgroup.com").

    Returns:
        Email string if found, None otherwise.
    """
    time.sleep(_RATE_LIMIT_DELAY)

    response = httpx.post(
        f"{BASE_URL}/people/match",
        headers=_HEADERS,
        json={
            "api_key": APOLLO_API_KEY,
            "first_name": first_name,
            "last_name": last_name,
            "domain": company_domain,
            "reveal_personal_emails": False,
        },
        timeout=15,
    )

    if response.status_code != 200:
        logger.warning("Apollo people/match returned %d: %s", response.status_code, response.text[:200])
        return None

    person = response.json().get("person") or {}
    email = person.get("email", "")
    if email and "@" in email:
        logger.info("Apollo found email for %s %s: %s", first_name, last_name, email)
        return email

    return None


def search_leads(
    job_titles: list[str],
    industry: str,
    geography: list[str],
    min_employees: int = 10,
    limit: int = 20,
) -> list[dict]:
    """Search for leads matching the given criteria.

    Args:
        job_titles: List of job titles to target (e.g. ["VP Revenue", "Revenue Manager"]).
        industry: Industry keyword (e.g. "hospitality hotels").
        geography: List of location strings (e.g. ["Germany", "Austria", "Switzerland"]).
        min_employees: Minimum company headcount filter.
        limit: Maximum results to return (capped at 25 per free tier page limit).

    Returns:
        List of prospect dicts: first_name, last_name, title, company, email, linkedin_url, location.
    """
    time.sleep(_RATE_LIMIT_DELAY)

    response = httpx.post(
        f"{BASE_URL}/mixed_people/search",
        headers=_HEADERS,
        json={
            "api_key": APOLLO_API_KEY,
            "page": 1,
            "per_page": min(limit, 25),
            "person_titles": job_titles,
            "person_locations": geography,
            "organization_num_employees_ranges": [f"{min_employees},10000"],
            "q_keywords": industry,
        },
        timeout=20,
    )

    if response.status_code != 200:
        logger.warning("Apollo search returned %d: %s", response.status_code, response.text[:200])
        return []

    people = response.json().get("people", [])
    results = [
        {
            "first_name": p.get("first_name", ""),
            "last_name": p.get("last_name", ""),
            "title": p.get("title", ""),
            "company": (p.get("organization") or {}).get("name", ""),
            "email": p.get("email", ""),
            "linkedin_url": p.get("linkedin_url", ""),
            "location": p.get("city", ""),
        }
        for p in people
    ]

    logger.info("Apollo search: %d leads for titles=%s", len(results), job_titles)
    return results
