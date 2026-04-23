"""Web research utilities for lead enrichment.

Provides three data sources:
- Apollo people/match — LinkedIn headline, employment history, company profile
- Website scraper — homepage text extraction
- DuckDuckGo search — recent news and mentions
"""

import logging
import os
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def apollo_enrich_person(
    first_name: str,
    last_name: str,
    company_domain: Optional[str] = None,
    linkedin_url: Optional[str] = None,
) -> dict:
    """Fetch full person profile from Apollo: LinkedIn data, employment history, company profile.

    Returns empty dict if Apollo is unavailable or person not found.
    """
    api_key = os.getenv("APOLLO_API_KEY", "")
    if not api_key:
        return {}

    payload: dict = {"first_name": first_name, "last_name": last_name, "reveal_personal_emails": False}
    if company_domain:
        payload["domain"] = _extract_domain(company_domain)
    if linkedin_url:
        payload["linkedin_url"] = linkedin_url

    try:
        resp = httpx.post(
            "https://api.apollo.io/v1/people/match",
            headers={"Content-Type": "application/json", "X-Api-Key": api_key},
            json=payload,
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning("Apollo people/match %d: %s", resp.status_code, resp.text[:200])
            return {}

        person = resp.json().get("person") or {}
        if not person:
            return {}

        org = person.get("organization") or {}

        employment = []
        for job in (person.get("employment_history") or [])[:6]:
            employment.append({
                "title": job.get("title", ""),
                "company": job.get("organization_name", ""),
                "start": (job.get("start_date") or "")[:4],
                "end": (job.get("end_date") or "")[:4] or "present",
                "current": bool(job.get("current")),
            })

        return {
            "headline": person.get("headline", ""),
            "city": person.get("city", ""),
            "country": person.get("country", ""),
            "linkedin_url": person.get("linkedin_url", ""),
            "email": person.get("email", ""),
            "employment_history": employment,
            "company_profile": {
                "name": org.get("name", ""),
                "description": org.get("short_description", ""),
                "industry": org.get("industry", ""),
                "employees": org.get("estimated_num_employees"),
                "founded": org.get("founded_year"),
                "num_locations": org.get("num_locations"),
                "annual_revenue": org.get("annual_revenue_printed", ""),
                "keywords": (org.get("keywords") or [])[:8],
                "linkedin_url": org.get("linkedin_url", ""),
            },
        }

    except Exception as e:
        logger.warning("Apollo enrichment failed for %s %s: %s", first_name, last_name, e)
        return {}


def scrape_website_text(url: str, max_chars: int = 2500) -> str:
    """Fetch a website homepage and return cleaned plain text."""
    if not url:
        return ""
    full_url = url if url.startswith("http") else f"https://{url}"
    try:
        resp = httpx.get(full_url, timeout=10, follow_redirects=True, headers=_BROWSER_HEADERS)
        if resp.status_code >= 400:
            return ""
        html = resp.text
        html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        logger.debug("Website scrape failed for %s: %s", url, e)
        return ""


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo and return list of {title, href, body} results."""
    try:
        from duckduckgo_search import DDGS
        results = DDGS().text(query, max_results=max_results)
        return results or []
    except Exception as e:
        logger.warning("Web search failed for '%s': %s", query, e)
        return []


def _extract_domain(url_or_domain: str) -> str:
    """Strip protocol and path to return bare domain."""
    domain = re.sub(r"https?://", "", url_or_domain)
    domain = domain.split("/")[0].strip()
    return domain
