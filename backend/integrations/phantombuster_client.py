import csv
import io
import json
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

PHANTOMBUSTER_API_KEY = os.getenv("PHANTOMBUSTER_API_KEY", "")
PHANTOMBUSTER_AGENT_ID = os.getenv("PHANTOMBUSTER_ID", "")
BASE_URL = "https://api.phantombuster.com/api/v2"
_HEADERS = {
    "X-Phantombuster-Key": PHANTOMBUSTER_API_KEY,
    "Content-Type": "application/json",
}
_POLL_INTERVAL = 10  # seconds between status checks
_POLL_MAX = 12  # 2 minutes max wait (free tier: 10 min/day, so don't block long)


def launch_linkedin_search_scraper(search_url: str, limit: int = 25) -> str:
    """Launch the PhantomBuster LinkedIn search scraper.

    Args:
        search_url: LinkedIn search URL to scrape (Sales Navigator or regular search).
        limit: Max profiles to extract. Keep ≤ 25 to respect the 10 min/day free quota.

    Returns:
        container_id string — use with get_scraper_results() to poll for output.
    """
    payload = {
        "id": PHANTOMBUSTER_AGENT_ID,
        "argument": {
            "searches": search_url,
            "numberOfProfiles": limit,
            "sessionCookie": os.getenv("LINKEDIN_SESSION_COOKIE", ""),
        },
    }

    response = httpx.post(f"{BASE_URL}/agents/launch", headers=_HEADERS, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    container_id = data.get("containerId", data.get("id", ""))
    logger.info("PhantomBuster launched agent %s → container=%s", PHANTOMBUSTER_AGENT_ID, container_id)
    return container_id


def get_scraper_results(container_id: str) -> list[dict]:
    """Poll PhantomBuster until the scrape completes and return parsed leads.

    Args:
        container_id: Container ID returned by launch_linkedin_search_scraper().

    Returns:
        List of lead dicts: first_name, last_name, title, company, linkedin_url, location.
        Returns empty list if the agent errors or exceeds the poll timeout.
    """
    for attempt in range(_POLL_MAX):
        response = httpx.get(
            f"{BASE_URL}/agents/output",
            headers=_HEADERS,
            params={"id": PHANTOMBUSTER_AGENT_ID, "containerId": container_id},
            timeout=15,
        )

        if response.status_code != 200:
            logger.warning("PhantomBuster poll %d: HTTP %d", attempt, response.status_code)
            time.sleep(_POLL_INTERVAL)
            continue

        data = response.json()
        status = data.get("status", "")
        logger.info("PhantomBuster: status=%s attempt=%d/%d", status, attempt + 1, _POLL_MAX)

        if status in ("finished", "error", "stopped"):
            if status == "error":
                logger.error("PhantomBuster agent errored: %s", data.get("output", "")[:200])
                return []
            return _parse_output(data.get("output", ""))

        time.sleep(_POLL_INTERVAL)

    logger.warning("PhantomBuster: poll timeout for container %s", container_id)
    return []


def _parse_output(output: str) -> list[dict]:
    """Parse PhantomBuster JSON or CSV output into normalised lead dicts."""
    if not output:
        return []

    output = output.strip()

    if output.startswith("["):
        try:
            rows = json.loads(output)
        except json.JSONDecodeError:
            return []
    else:
        reader = csv.DictReader(io.StringIO(output))
        rows = list(reader)

    results = [
        {
            "first_name": r.get("firstName", r.get("first_name", "")),
            "last_name": r.get("lastName", r.get("last_name", "")),
            "title": r.get("jobTitle", r.get("title", "")),
            "company": r.get("companyName", r.get("company", "")),
            "linkedin_url": r.get("profileUrl", r.get("linkedin_url", "")),
            "location": r.get("location", ""),
        }
        for r in rows
    ]

    logger.info("PhantomBuster: parsed %d leads from output", len(results))
    return results
