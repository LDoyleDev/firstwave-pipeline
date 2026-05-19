#!/usr/bin/env python3
"""
Group consolidation: classify hotels by parent chain/group and mark primary contacts.

Problem: Hotel chains (Marriott, Hilton, Accor, etc.) share sales teams.
Reaching out to 10 Marriott properties = 10 spam emails to the same person.

Solution:
1. Pull verified_hotel leads from Supabase
2. Haiku classifies each: parent_group (chain name) or "Independent"
3. Group by parent_group, mark one as primary_contact (usually flagship/largest)
4. Update Supabase records with grouping metadata in enrichment_data
5. Outreach filter: WHERE is_primary_contact = TRUE OR parent_group = 'Independent'
"""

import json
import sys
import logging
import argparse
from pathlib import Path
from collections import defaultdict
import time

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.utils.anthropic_client import classify, VybeTradingWindowError
from backend.integrations.supabase_client import supabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


GROUP_CLASSIFICATION_PROMPT = """You identify parent companies/chains for hotel properties.

Given a hotel name and location, identify the parent organization.

Common parent groups:
- Marriott International (Marriott, Ritz-Carlton, Sheraton, Westin, W Hotels, St. Regis, JW Marriott, Le Méridien, Renaissance, Courtyard, Residence Inn, Fairfield, Aloft, Edition, Bulgari, Autograph)
- Hilton Worldwide (Hilton, Waldorf Astoria, Conrad, Doubletree, Embassy Suites, Hampton, Hilton Garden Inn, Curio, Tapestry, LXR, Canopy, Tru, Motto)
- Accor (Sofitel, Pullman, Mövenpick, Novotel, Mercure, Ibis, Raffles, Fairmont, Swissôtel, MGallery, 25hours, SO/, Mantra)
- IHG (InterContinental, Crowne Plaza, Holiday Inn, Holiday Inn Express, Kimpton, Hotel Indigo, Six Senses, Regent, Hualuxe, EVEN, Voco, Staybridge, Candlewood, Atwell)
- Hyatt (Hyatt, Park Hyatt, Andaz, Grand Hyatt, Hyatt Regency, Hyatt Place, Hyatt House, Alila, Thompson, Caption, Joie de Vivre, Destination, Miraval, Dream)
- Wyndham (Wyndham, Ramada, Days Inn, Super 8, Travelodge, Howard Johnson, La Quinta, Microtel, Baymont, AmericInn, Esplendor, Dazzler, Trademark, TRYP)
- Choice Hotels (Comfort Inn, Quality Inn, Sleep Inn, Clarion, Cambria, Ascend, Econo Lodge, Suburban, Rodeway, MainStay, WoodSpring)
- Best Western (Best Western, Premier, Plus, Executive Residency, Sadie, Aiden, GLō)
- Radisson Hotel Group (Radisson, Park Plaza, Park Inn, Country Inn, Prizeotel)
- Meliá Hotels (Meliá, Paradisus, Innside, Sol, ME by Meliá, Gran Meliá)
- NH Hotel Group / Minor Hotels (NH, NH Collection, nhow, Anantara, Avani, Tivoli, Elewana)
- Four Seasons (Four Seasons)
- Mandarin Oriental (Mandarin Oriental)
- Rosewood (Rosewood)
- Aman (Aman)
- Belmond (Belmond, including Hotel Splendido, Cipriani, etc.)
- Kempinski (Kempinski)
- Shangri-La (Shangri-La, JEN)
- Six Senses (Six Senses - now IHG owned)
- Soneva (Soneva)
- Independent (single property, family-owned, boutique not part of chain)

Respond ONLY with valid JSON (no markdown, no explanation):
{
  "parent_group": "<group name from list above OR 'Independent'>",
  "confidence": <0.0-1.0>,
  "brand_signal": "<word in hotel name that indicates the chain, or 'none'>"
}
"""


def parse_json(response: str) -> dict:
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    return json.loads(response.strip())


def classify_group(hotel_name: str, location: str) -> dict:
    """Use Haiku to identify parent group."""
    user_msg = f"Hotel: {hotel_name}\nLocation: {location}\n\nIdentify parent group."
    try:
        response = classify(GROUP_CLASSIFICATION_PROMPT, user_msg)
        return parse_json(response)
    except (VybeTradingWindowError, json.JSONDecodeError) as e:
        logger.warning(f"  Classification error for '{hotel_name}': {e}")
        return {"parent_group": "Independent", "confidence": 0.5, "brand_signal": "fallback"}


def fetch_verified_leads() -> list[dict]:
    """Pull verified_hotel leads from Supabase (verification_status inside enrichment_data)."""
    logger.info("Fetching verified leads from Supabase...")
    response = (
        supabase.table("leads")
        .select("id, first_name, last_name, location, enrichment_data, source")
        .eq("source", "haiku_pilot")
        .execute()
    )
    all_leads = response.data or []
    leads = [
        l for l in all_leads
        if (l.get("enrichment_data") or {}).get("verification_status") == "verified_hotel"
    ]
    logger.info(f"  Found {len(leads)} verified leads (of {len(all_leads)} haiku_pilot total)")
    return leads


def update_lead_grouping(lead_id: str, parent_group: str, is_primary: bool, group_size: int) -> bool:
    """Update a lead's enrichment_data with grouping info."""
    try:
        current = (
            supabase.table("leads")
            .select("enrichment_data")
            .eq("id", lead_id)
            .single()
            .execute()
        )
        enrichment_data = current.data.get("enrichment_data") or {}
        enrichment_data["parent_group"] = parent_group
        enrichment_data["is_primary_contact"] = is_primary
        enrichment_data["group_property_count"] = group_size

        supabase.table("leads").update({
            "enrichment_data": enrichment_data,
            "outreach_approved": is_primary or parent_group == "Independent",
        }).eq("id", lead_id).execute()
        return True
    except Exception as e:
        logger.error(f"  Update error for {lead_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Group hotels by parent chain")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't update Supabase, just print results")
    parser.add_argument("--output", type=str, default="data/phase2/grouped_leads.json",
                        help="Write grouping report to this file")
    args = parser.parse_args()

    leads = fetch_verified_leads()
    if not leads:
        logger.warning("No verified leads found. Run Phase 3 enrichment first.")
        return 1

    logger.info(f"Classifying parent groups for {len(leads)} leads...")
    classified = []
    for i, lead in enumerate(leads, 1):
        full_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
        location = lead.get("location", "")
        logger.info(f"  [{i}/{len(leads)}] {full_name}")

        group_info = classify_group(full_name, location)
        classified.append({
            "id": lead["id"],
            "name": full_name,
            "location": location,
            "parent_group": group_info["parent_group"],
            "confidence": group_info["confidence"],
            "brand_signal": group_info.get("brand_signal", "none"),
        })

        time.sleep(0.5)

    logger.info("Grouping by parent...")
    groups: dict[str, list[dict]] = defaultdict(list)
    for c in classified:
        groups[c["parent_group"]].append(c)

    logger.info("")
    logger.info("=== Group Summary ===")
    sorted_groups = sorted(groups.items(), key=lambda x: -len(x[1]))
    for parent, members in sorted_groups:
        logger.info(f"  {parent}: {len(members)} properties")

    logger.info("")
    primary_count = 0
    secondary_count = 0
    for parent, members in groups.items():
        if parent == "Independent":
            for m in members:
                m["is_primary_contact"] = True
            primary_count += len(members)
        else:
            members_sorted = sorted(members, key=lambda m: (-m["confidence"], len(m["name"])))
            for i, m in enumerate(members_sorted):
                m["is_primary_contact"] = (i == 0)
                if i == 0:
                    primary_count += 1
                else:
                    secondary_count += 1

    logger.info(f"Outreach targets: {primary_count} (primaries)")
    logger.info(f"Suppressed: {secondary_count} (secondaries in chains)")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    report = {
        "total_leads": len(classified),
        "primary_count": primary_count,
        "secondary_count": secondary_count,
        "groups": {p: len(m) for p, m in sorted_groups},
        "leads": classified,
    }
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"✓ Report written to {args.output}")

    if args.dry_run:
        logger.info("(dry-run: not updating Supabase)")
        return 0

    logger.info("Updating Supabase records...")
    updated = 0
    for c in classified:
        group_size = len(groups[c["parent_group"]])
        if update_lead_grouping(c["id"], c["parent_group"], c["is_primary_contact"], group_size):
            updated += 1

    logger.info(f"✓ Updated {updated}/{len(classified)} Supabase records")
    logger.info(f"  Set outreach_approved=TRUE for {primary_count} primary contacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
