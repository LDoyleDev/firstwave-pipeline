#!/usr/bin/env python3
"""
Scrape hotel businesses from OpenStreetMap via Overpass API.

Queries `tourism=hotel` nodes in target English-speaking + European countries.
Returns structured leads with name, address, phone, website, brand.

No authentication required. Rate limit: ~1 query/sec (we use 2s delay).
"""

import json
import sys
import logging
import argparse
from pathlib import Path
import time
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Target countries: English-speaking (excluding US) + European
TARGET_COUNTRIES = [
    # English-speaking (non-US)
    ("GB", "United Kingdom"),
    ("IE", "Ireland"),
    ("CA", "Canada"),
    ("AU", "Australia"),
    ("NZ", "New Zealand"),
    ("MT", "Malta"),
    # Western/Central Europe
    ("DE", "Germany"),
    ("FR", "France"),
    ("ES", "Spain"),
    ("IT", "Italy"),
    ("NL", "Netherlands"),
    ("BE", "Belgium"),
    ("AT", "Austria"),
    ("CH", "Switzerland"),
    ("PT", "Portugal"),
    ("LU", "Luxembourg"),
    # Nordic
    ("DK", "Denmark"),
    ("SE", "Sweden"),
    ("NO", "Norway"),
    ("FI", "Finland"),
    ("IS", "Iceland"),
    # Eastern Europe
    ("PL", "Poland"),
    ("CZ", "Czech Republic"),
    ("HU", "Hungary"),
    ("SK", "Slovakia"),
    ("RO", "Romania"),
    ("BG", "Bulgaria"),
    ("HR", "Croatia"),
    ("SI", "Slovenia"),
    ("EE", "Estonia"),
    ("LV", "Latvia"),
    ("LT", "Lithuania"),
    # Mediterranean
    ("GR", "Greece"),
    ("CY", "Cyprus"),
]


def query_overpass(country_code: str, country_name: str, timeout: int = 180) -> list[dict]:
    """Query Overpass API for hotels in a country.

    Returns: list of {name, address, country, phone, website, brand}
    """
    query = f"""
[out:json][timeout:{timeout - 30}];
area["ISO3166-1"="{country_code}"]->.searchArea;
node[tourism=hotel]["name"](area.searchArea);
out tags;
"""
    logger.info(f"Querying OSM for {country_name} ({country_code})...")

    headers = {
        "User-Agent": "firstwave-pipeline/1.0 (hotel lead research)",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        with httpx.Client(timeout=timeout, headers=headers) as client:
            resp = client.post(OVERPASS_URL, content=f"data={query}".encode("utf-8"))
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.warning(f"  ✗ HTTP error for {country_name}: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.warning(f"  ✗ JSON decode error for {country_name}: {e}")
        return []

    hotels: list[dict] = []
    for elem in data.get("elements", []):
        tags = elem.get("tags", {})
        name = tags.get("name", "").strip()
        if not name or len(name) < 3:
            continue

        addr_parts = []
        street = tags.get("addr:street", "").strip()
        housenumber = tags.get("addr:housenumber", "").strip()
        if street:
            addr_parts.append(f"{housenumber} {street}".strip())
        postcode = tags.get("addr:postcode", "").strip()
        if postcode:
            addr_parts.append(postcode)
        city = tags.get("addr:city", "").strip()
        if city:
            addr_parts.append(city)

        address = ", ".join(addr_parts) if addr_parts else f"{country_name}"

        phone = (
            tags.get("phone")
            or tags.get("contact:phone")
            or tags.get("phone:mobile", "")
        ).strip()
        website = (
            tags.get("website")
            or tags.get("contact:website")
            or tags.get("url", "")
        ).strip()
        brand = (tags.get("brand") or tags.get("operator", "")).strip()
        email = (tags.get("email") or tags.get("contact:email", "")).strip()
        stars = tags.get("stars", "").strip()

        hotels.append({
            "name": name,
            "address": address,
            "country": country_name,
            "phone": phone,
            "website": website,
            "email": email,
            "brand": brand,
            "stars": stars,
            # OSM element identity — lets a sourced osm_tag email cite its exact
            # provenance: https://www.openstreetmap.org/{osm_type}/{osm_id}
            "osm_type": elem.get("type", "node"),
            "osm_id": elem.get("id"),
        })

    logger.info(f"  ✓ {len(hotels)} hotels from {country_name}")
    return hotels


def main():
    parser = argparse.ArgumentParser(description="Scrape hotels from OpenStreetMap")
    parser.add_argument("--output", type=str, default="data/phase2/osm_hotels.json",
                        help="Output JSON file")
    parser.add_argument("--countries", type=str, default=None,
                        help="Comma-separated ISO codes (default: all targets)")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Delay between API queries (Overpass rate limit)")
    parser.add_argument("--timeout", type=int, default=180,
                        help="Query timeout per country (seconds)")
    args = parser.parse_args()

    if args.countries:
        wanted = {c.strip().upper() for c in args.countries.split(",")}
        targets = [(c, n) for c, n in TARGET_COUNTRIES if c in wanted]
    else:
        targets = TARGET_COUNTRIES

    logger.info(f"Querying {len(targets)} countries...")
    logger.info("")

    all_hotels: list[dict] = []
    by_country: dict[str, int] = {}

    for code, name in targets:
        hotels = query_overpass(code, name, timeout=args.timeout)
        all_hotels.extend(hotels)
        by_country[name] = len(hotels)
        time.sleep(args.delay)

    output = {"leads": all_hotels}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info("")
    logger.info("=== TOTAL: %d hotels from OSM ===", len(all_hotels))
    logger.info("By country:")
    for country, count in sorted(by_country.items(), key=lambda x: -x[1]):
        logger.info(f"  {country}: {count}")
    logger.info(f"✓ Wrote to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
