#!/usr/bin/env python3
"""
Generic web scraper: WebFetch URL → Haiku extracts hotel leads → JSON.

Used by scrape_coordinator.sh to run 5 parallel Haiku extraction workers
across ~100 source URLs (Wikipedia, Relais & Châteaux, tourism boards, etc.).

Token-efficient: Haiku at ~$0.006/page vs Opus at ~$0.075/page.
"""

import json
import sys
import logging
import argparse
from pathlib import Path
from typing import TypedDict
import time

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.utils.anthropic_client import classify, VybeTradingWindowError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("scrape_haiku")


class Lead(TypedDict):
    name: str
    address: str
    country: str
    phone: str
    website: str | None


EXTRACTION_SYSTEM_PROMPT = """You are a hotel data extraction specialist.

Given the text content of a webpage (which may contain hotel listings,
directories, or articles), extract all hotel businesses you can find.

Return ONLY valid JSON (no markdown, no explanation):
{
  "hotels": [
    {
      "name": "<hotel name>",
      "address": "<full address or city, country>",
      "country": "<country name>",
      "phone": "<phone if found, else empty string>",
      "website": "<URL if found, else empty string>"
    }
  ]
}

Rules:
- Only include real hotel businesses (not OTAs, review sites, or booking platforms)
- Skip generic results like "Booking.com", "Hotels.com", "TripAdvisor", "Expedia"
- Include hotels with at least name + city/address
- Extract up to 30 hotels per page
- If no hotels found, return {"hotels": []}
"""


def fetch_url(url: str, timeout: int = 30) -> str:
    """Fetch URL content and strip to clean text."""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [line for line in text.split("\n") if line.strip()]
    cleaned = "\n".join(lines)

    if len(cleaned) > 15000:
        cleaned = cleaned[:15000]

    return cleaned


def parse_haiku_json(response: str) -> dict:
    """Parse Haiku JSON response, handling markdown wrappers."""
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    response = response.strip()
    return json.loads(response)


def extract_hotels(content: str, country_hint: str = "") -> list[Lead]:
    """Use Haiku to extract structured hotel data from web content."""
    user_message = f"Country context: {country_hint}\n\nWebpage content:\n{content}"
    try:
        response = classify(EXTRACTION_SYSTEM_PROMPT, user_message)
        result = parse_haiku_json(response)
        hotels = result.get("hotels", [])

        for h in hotels:
            if not h.get("country") and country_hint:
                h["country"] = country_hint
            for field in ["name", "address", "country", "phone", "website"]:
                if field not in h:
                    h[field] = ""

        return hotels
    except VybeTradingWindowError:
        logger.error("Trading window active - skipping")
        return []
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e}")
        return []
    except Exception as e:
        logger.warning(f"Extraction error: {e}")
        return []


def scrape_url(url: str, country: str = "") -> list[Lead]:
    """Fetch a URL and extract hotels via Haiku."""
    logger.info(f"  Fetching: {url}")
    try:
        content = fetch_url(url)
        logger.info(f"  Got {len(content)} chars, extracting via Haiku...")
        hotels = extract_hotels(content, country)
        logger.info(f"  ✓ Extracted {len(hotels)} hotels from {url}")
        return hotels
    except httpx.HTTPError as e:
        logger.warning(f"  ✗ HTTP error for {url}: {e}")
        return []
    except Exception as e:
        logger.warning(f"  ✗ Error scraping {url}: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Haiku-powered web scraper")
    parser.add_argument("--input", type=str, required=True,
                        help="JSON file with sources: [{url, country}, ...]")
    parser.add_argument("--output", type=str, required=True,
                        help="Output JSON file for extracted leads")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of URLs to scrape (testing)")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Delay between requests (seconds)")

    args = parser.parse_args()

    with open(args.input) as f:
        sources = json.load(f)

    if args.limit:
        sources = sources[:args.limit]

    logger.info(f"Scraping {len(sources)} URLs → {args.output}")

    all_leads: list[Lead] = []
    for i, source in enumerate(sources, 1):
        url = source["url"]
        country = source.get("country", "")
        logger.info(f"[{i}/{len(sources)}] {country or 'unknown'}: {url}")

        leads = scrape_url(url, country)
        all_leads.extend(leads)

        if i < len(sources):
            time.sleep(args.delay)

    output_data = {"leads": all_leads}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logger.info(f"✓ Wrote {len(all_leads)} leads to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
