#!/usr/bin/env python3
"""
Score verified hotel leads on outreach priority (0-100).

Inputs from Supabase enrichment_data:
- operator_type (independent > boutique > franchise)
- pain_points (OTA/revenue/staff signals = high)
- parent_group (Independent gets boost; chains get small penalty)
- decision_maker_role (Owner/GM > VP > Marketing)
- country (target markets weighted)

Output: Updates each lead's lead_score field; writes report to data/phase2/priority_scored.json
"""

import json
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.integrations.supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


COUNTRY_WEIGHTS = {
    # Highest fit (EU + English-speaking)
    "United Kingdom": 1.0, "Ireland": 1.0, "Germany": 1.0, "France": 1.0,
    "Spain": 1.0, "Italy": 1.0, "Netherlands": 1.0, "Belgium": 1.0,
    "Austria": 1.0, "Switzerland": 1.0, "Portugal": 0.95,
    # Tier 2: Nordic & Mediterranean
    "Denmark": 0.95, "Sweden": 0.95, "Norway": 0.95, "Finland": 0.9,
    "Greece": 0.95, "Malta": 0.95, "Cyprus": 0.9, "Luxembourg": 0.95,
    # Tier 3: Eastern Europe
    "Poland": 0.85, "Czech Republic": 0.85, "Hungary": 0.85, "Slovakia": 0.8,
    "Romania": 0.8, "Bulgaria": 0.8, "Croatia": 0.85, "Slovenia": 0.85,
    "Estonia": 0.8, "Latvia": 0.8, "Lithuania": 0.8, "Iceland": 0.85,
    # Outside focus
    "Canada": 0.7, "Australia": 0.7, "New Zealand": 0.7,
    "United States": 0.5, "USA": 0.5, "US": 0.5,
}

OPERATOR_WEIGHTS = {
    "independent": 1.0,
    "boutique": 0.95,
    "family": 0.95,
    "franchise": 0.6,
    "chain": 0.5,
}

PAIN_POINT_WEIGHTS = {
    "ota dependency": 1.0,
    "ota": 1.0,
    "booking.com": 1.0,
    "expedia": 1.0,
    "revenue management": 1.0,
    "yield management": 1.0,
    "pricing power": 0.9,
    "occupancy": 0.85,
    "staff retention": 0.8,
    "staffing": 0.8,
    "labor cost": 0.8,
    "guest experience": 0.7,
    "personalization": 0.7,
    "marketing": 0.65,
    "social media": 0.5,
}

ROLE_WEIGHTS = {
    "owner": 1.0,
    "general manager": 1.0,
    "managing director": 0.95,
    "ceo": 0.95,
    "director": 0.85,
    "vp revenue": 0.9,
    "vp marketing": 0.85,
    "cmo": 0.85,
    "marketing manager": 0.7,
    "revenue manager": 0.85,
    "operations": 0.75,
    "guest relations": 0.5,
}


def score_lead(lead: dict) -> tuple[int, dict]:
    """Compute 0-100 score with breakdown."""
    enrichment_data = lead.get("enrichment_data") or {}
    enrichment = enrichment_data.get("enrichment") or {}
    classification = enrichment_data.get("classification") or {}

    breakdown = {}

    # Base: classification confidence (already in lead_score)
    confidence = classification.get("confidence", 0.5)
    breakdown["confidence"] = round(confidence * 30, 1)  # 0-30

    # Country weight (0-15)
    country = ""
    location = lead.get("location") or ""
    for c, w in COUNTRY_WEIGHTS.items():
        if c.lower() in location.lower():
            country = c
            break
    country_weight = COUNTRY_WEIGHTS.get(country, 0.7)
    breakdown["country"] = round(country_weight * 15, 1)

    # Operator type (0-20)
    op_type = (enrichment.get("operator_type") or "").lower().strip()
    op_weight = 0.5
    for k, w in OPERATOR_WEIGHTS.items():
        if k in op_type:
            op_weight = max(op_weight, w)
    breakdown["operator_type"] = round(op_weight * 20, 1)

    # Pain points (0-20)
    pain_points = enrichment.get("pain_points") or lead.get("pain_signals") or []
    pain_score = 0
    matched_pains = []
    for pp in pain_points:
        pp_l = (pp or "").lower()
        for k, w in PAIN_POINT_WEIGHTS.items():
            if k in pp_l:
                pain_score = max(pain_score, w)
                matched_pains.append(k)
                break
    breakdown["pain_points"] = round(pain_score * 20, 1)

    # Decision-maker role (0-15)
    role = (enrichment.get("decision_maker_role") or lead.get("title") or "").lower()
    role_weight = 0.5
    for k, w in ROLE_WEIGHTS.items():
        if k in role:
            role_weight = max(role_weight, w)
    breakdown["dm_role"] = round(role_weight * 15, 1)

    total = sum(breakdown.values())
    return int(total), breakdown


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=str, default="data/phase2/priority_scored.json")
    args = parser.parse_args()

    logger.info("Fetching verified leads from Supabase...")
    response = (
        supabase.table("leads")
        .select("id, first_name, last_name, title, location, enrichment_data, pain_signals, lead_score, source")
        .in_("source", ["haiku_pilot", "haiku_max_test"])
        .execute()
    )
    leads = response.data or []
    logger.info(f"  Found {len(leads)} leads")

    scored = []
    for lead in leads:
        ed = lead.get("enrichment_data") or {}
        if ed.get("verification_status") != "verified_hotel":
            continue
        score, breakdown = score_lead(lead)
        scored.append({
            "id": lead["id"],
            "name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
            "location": lead.get("location"),
            "score": score,
            "breakdown": breakdown,
        })

    scored.sort(key=lambda x: -x["score"])

    logger.info(f"Scored {len(scored)} verified leads")
    logger.info(f"Score distribution:")
    buckets = [0, 20, 40, 60, 80, 101]
    for i in range(len(buckets) - 1):
        count = sum(1 for s in scored if buckets[i] <= s["score"] < buckets[i+1])
        logger.info(f"  {buckets[i]:3d}-{buckets[i+1]-1:3d}: {count}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({"leads": scored}, f, indent=2, ensure_ascii=False)
    logger.info(f"✓ Wrote scores to {args.output}")

    if args.dry_run:
        logger.info("(dry-run: skipping Supabase updates)")
        return

    updated = 0
    for s in scored:
        try:
            supabase.table("leads").update({"lead_score": s["score"]}).eq("id", s["id"]).execute()
            updated += 1
        except Exception as e:
            logger.warning(f"Update failed {s['id']}: {e}")
    logger.info(f"✓ Updated {updated} Supabase records with new lead_score")


if __name__ == "__main__":
    sys.exit(main())
