#!/usr/bin/env python3
"""
Lead enrichment pipeline: clarify + enrich hotel business leads using Haiku.

Phase 1 Pilot: Takes raw leads, classifies them as real hotel operators,
then enriches with operator type, team size, pain points, decision-maker role.

Respects trading-hours gates and batch constraints (max 5 leads per batch).
"""

import json
import sys
import logging
from pathlib import Path
from typing import TypedDict
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
import time

# Add parent directory to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.utils.anthropic_client import classify, generate, VybeTradingWindowError
from backend.integrations.supabase_client import supabase
from backend.integrations import jurisdiction  # module import — avoids classify() name clash

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class RawLead(TypedDict):
    name: str
    address: str
    phone: str
    country: str
    website: str | None


@dataclass
class ClarificationResult:
    classification: str  # "Verified Hotel Operator" | "Not a Hotel" | "Unclear - needs manual review"
    confidence: float  # 0.0 - 1.0
    reasoning: str


@dataclass
class EnrichmentResult:
    operator_type: str  # "independent" | "boutique" | "franchise"
    team_size_estimate: str  # e.g. "10-25 staff"
    pain_points: list[str]
    decision_maker_role: str  # "Owner" | "General Manager" | "CMO" | "VP Revenue"
    region: str


def clarify_lead(lead: RawLead) -> ClarificationResult:
    """
    Classify a single lead: is this a real hotel operator?

    Returns classification (verified/not/unclear) with confidence score.
    Raises VybeTradingWindowError if called during vybe-trading active hours.
    """
    system_prompt = """You are a hotel business verification specialist. Your job is to
classify hotel business leads with high precision.

Given a business name, address, phone, and country, determine:
1. Is this a real, operational hotel business (not an OTA, review site, or booking platform)?
2. How confident are you (0.0-1.0)?

Respond ONLY with valid JSON (no markdown, no explanation):
{
  "classification": "Verified Hotel Operator" | "Not a Hotel" | "Unclear - needs manual review",
  "confidence": <0.0 to 1.0>,
  "reasoning": "<brief explanation>"
}

High confidence criteria:
- Business name includes "hotel", "inn", "resort", "lodge", "motel"
- Address is in a major city or resort destination
- Phone matches country code
- Company registration exists (verified via web search if needed)

Reject:
- OTA sites (Booking.com, Expedia, Hotels.com)
- Review platforms (TripAdvisor)
- Real estate platforms
- Non-operational properties (under construction, planned)
"""

    lead_data = f"""
Business Name: {lead['name']}
Address: {lead['address']}
Country: {lead['country']}
Phone: {lead['phone']}
Website: {lead.get('website', 'N/A')}
"""

    try:
        response = classify(system_prompt, lead_data)
        # Handle markdown-wrapped JSON from Ollama
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]  # Remove 'json' marker
        response = response.strip()
        result = json.loads(response)
        return ClarificationResult(
            classification=result.get("classification", "Unclear - needs manual review"),
            confidence=float(result.get("confidence", 0.5)),
            reasoning=result.get("reasoning", "")
        )
    except json.JSONDecodeError:
        logger.error("Failed to parse clarification response: %s", response)
        return ClarificationResult(
            classification="Unclear - needs manual review",
            confidence=0.0,
            reasoning="JSON parse error"
        )


def enrich_lead(lead: RawLead) -> EnrichmentResult | None:
    """
    Enrich a verified lead with operator type, pain points, decision-maker role.

    Returns enrichment data, or None if enrichment fails.
    """
    system_prompt = """You are a hospitality market analyst enriching hotel business lead data.

Given a hotel business name, address, and basic contact info, infer:
1. Operator type: independent (single property), boutique (multi-unit with brand), or franchise
2. Estimated team size
3. Likely pain points (guest experience, OTA dependency, staff retention, pricing power)
4. Most likely decision-maker role for sales outreach

Respond ONLY with valid JSON:
{
  "operator_type": "independent" | "boutique" | "franchise",
  "team_size_estimate": "<e.g. '10-25 staff'>",
  "pain_points": ["<point1>", "<point2>", "<point3>"],
  "decision_maker_role": "Owner" | "General Manager" | "CMO" | "VP Revenue" | "Director of CX",
  "region": "<e.g. 'Central Europe' or 'US Midwest'>"
}

Base your inference on:
- Hotel name patterns (e.g., "Grand Hotel" suggests larger, multi-property)
- Location signals (tourism hotspot → boutique; suburbs → independent)
- Typical pain points for that market segment
"""

    lead_data = f"""
Hotel Name: {lead['name']}
Address: {lead['address']}
Country: {lead['country']}
Website: {lead.get('website', 'N/A')}
"""

    try:
        response = generate(system_prompt, lead_data)
        # Handle markdown-wrapped JSON from Ollama
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]  # Remove 'json' marker
        response = response.strip()
        result = json.loads(response)
        return EnrichmentResult(
            operator_type=result.get("operator_type", "independent"),
            team_size_estimate=result.get("team_size_estimate", "Unknown"),
            pain_points=result.get("pain_points", []),
            decision_maker_role=result.get("decision_maker_role", "General Manager"),
            region=result.get("region", "")
        )
    except json.JSONDecodeError:
        logger.error("Failed to parse enrichment response: %s", response)
        return None


def process_batch(
    leads: list[RawLead],
    batch_id: str,
    force_allow: bool = False
) -> dict:
    """
    Process a batch of leads (max 5).

    Args:
        leads: Raw lead data (max 5)
        batch_id: Identifier for this batch (e.g. "batch_001")
        force_allow: Set FIRSTWAVE_LLM_ALWAYS_ALLOW=1 for testing

    Returns:
        {
            "batch_id": str,
            "processed": int,
            "verified": int,
            "unclear": int,
            "rejected": int,
            "results": [{"lead": RawLead, "classification": ..., "enrichment": ...}]
        }
    """
    if len(leads) > 5:
        logger.warning("Batch size exceeds 5, truncating to 5")
        leads = leads[:5]

    # Gate trading hours if needed
    if not force_allow:
        import os
        original = os.environ.get("FIRSTWAVE_LLM_ALWAYS_ALLOW", "")
        os.environ["FIRSTWAVE_LLM_ALWAYS_ALLOW"] = "0"
    else:
        import os
        os.environ["FIRSTWAVE_LLM_ALWAYS_ALLOW"] = "1"

    results = []
    verified_count = 0
    unclear_count = 0
    rejected_count = 0

    for idx, lead in enumerate(leads, 1):
        logger.info(f"[{batch_id}] Processing lead {idx}/5: {lead['name']}")

        try:
            # Clarify: is this a real hotel?
            clarification = clarify_lead(lead)
            logger.info(f"  Classification: {clarification.classification} "
                       f"(confidence: {clarification.confidence:.2f})")

            # Enrich if verified
            enrichment = None
            if clarification.classification == "Verified Hotel Operator" and clarification.confidence >= 0.75:
                enrichment = enrich_lead(lead)
                if enrichment:
                    logger.info(f"  Enriched: {enrichment.operator_type} | "
                               f"DM: {enrichment.decision_maker_role}")
                    verified_count += 1
                else:
                    unclear_count += 1
            elif clarification.confidence >= 0.75:
                unclear_count += 1
            else:
                rejected_count += 1

            results.append({
                "lead": lead,
                "classification": asdict(clarification),
                "enrichment": asdict(enrichment) if enrichment else None,
            })

            # Rate limit: 1-2 second delay between leads
            time.sleep(1)

        except VybeTradingWindowError as e:
            logger.error(f"  Trading hours gate: {e}")
            logger.info("  Batch deferred to off-peak window")
            return {
                "batch_id": batch_id,
                "error": "trading_hours_active",
                "deferred": True,
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"  Error processing lead: {e}")
            rejected_count += 1

    return {
        "batch_id": batch_id,
        "processed": len(leads),
        "verified": verified_count,
        "unclear": unclear_count,
        "rejected": rejected_count,
        "results": results,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def save_to_supabase(batch_result: dict) -> int:
    """
    Save batch results to Supabase leads table.

    Returns: number of records saved
    """
    if batch_result.get("deferred"):
        logger.warning("Batch deferred, skipping Supabase write")
        return 0

    saved = 0

    for item in batch_result.get("results", []):
        lead = item["lead"]
        classification = item["classification"]
        enrichment = item.get("enrichment")

        # Determine verification status (stored in enrichment_data, not as DB column)
        verification_status = "discarded"
        if classification["classification"] == "Verified Hotel Operator":
            verification_status = "verified_hotel"
        elif classification["classification"] == "Unclear - needs manual review":
            verification_status = "manual_review"

        # Skip if confidence too low
        if classification["confidence"] < 0.5:
            continue

        # Skip discarded leads (not hotels)
        if verification_status == "discarded":
            continue

        # Compliance provenance: persist email + normalised country so the
        # send-path jurisdiction gate and the GDPR/CASL audit trail have data.
        raw_country = lead.get("country")
        country_iso = jurisdiction.to_iso(raw_country) or raw_country
        email = (lead.get("email") or "").strip().lower()

        record = {
            "first_name": lead["name"].split()[0] if lead["name"] else "Unknown",
            "last_name": " ".join(lead["name"].split()[1:]) if len(lead["name"].split()) > 1 else lead["name"],
            "title": enrichment.get("decision_maker_role", "General Manager") if enrichment else None,
            "phone": lead.get("phone"),
            "location": f"{lead.get('address')}, {raw_country}",
            "country": country_iso,
            "jurisdiction_route": jurisdiction.classify(raw_country),
            "pipeline_stage": "discovered",
            "enrichment_data": {
                "raw_name": lead["name"],
                "verification_status": verification_status,
                "classification": classification,
                "enrichment": enrichment,
            },
            "pain_signals": enrichment.get("pain_points", []) if enrichment else [],
            "source": "haiku_pilot",
            "warmth": "cold",
            "lead_score": int(classification["confidence"] * 100),
        }
        if email and "@" in email:
            record["email"] = email
            record["email_source"] = "osm_tag"
            record["email_sourced_at"] = datetime.now(UTC).isoformat()
            record["email_address_type"] = "generic_role"

        try:
            # Use Supabase to insert
            response = supabase.table("leads").insert(record).execute()
            if response.data:
                saved += 1
                logger.info(f"  Saved to Supabase: {lead['name']}")
        except Exception as e:
            logger.error(f"  Supabase insert error: {e}")

    return saved


def load_sample_leads(file_path: str) -> list[RawLead]:
    """Load sample leads from JSON file."""
    try:
        with open(file_path) as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "leads" in data:
            return data["leads"]
        else:
            logger.error("Unexpected JSON structure")
            return []
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []


def main():
    """Run the lead enrichment pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description="Enrich hotel leads with Haiku")
    parser.add_argument(
        "--input",
        type=str,
        default="scripts/sample_leads.json",
        help="Path to input JSON file with raw leads"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Leads per batch (max 5, per system rules)"
    )
    parser.add_argument(
        "--force-allow",
        action="store_true",
        help="Skip trading-hours gate (for testing only)"
    )
    parser.add_argument(
        "--save-supabase",
        action="store_true",
        help="Save results to Supabase (default: JSON output only)"
    )

    args = parser.parse_args()

    if args.batch_size > 5:
        logger.warning("Batch size reduced to 5 per system rules")
        args.batch_size = 5

    # Load leads
    leads = load_sample_leads(args.input)
    if not leads:
        logger.error("No leads to process")
        return 1

    logger.info(f"Loaded {len(leads)} leads from {args.input}")

    # Process in batches
    all_results = []
    for i in range(0, len(leads), args.batch_size):
        batch = leads[i:i + args.batch_size]
        batch_id = f"batch_{i // args.batch_size + 1:03d}"

        logger.info(f"Processing {batch_id} ({len(batch)} leads)...")

        batch_result = process_batch(batch, batch_id, force_allow=args.force_allow)
        all_results.append(batch_result)

        # Save to Supabase if requested
        if args.save_supabase and not batch_result.get("deferred"):
            saved = save_to_supabase(batch_result)
            logger.info(f"Saved {saved} records to Supabase")

        # Delay between batches
        time.sleep(2)

    # Summary
    logger.info("=" * 60)
    logger.info("ENRICHMENT SUMMARY")
    logger.info("=" * 60)

    total_processed = sum(r.get("processed", 0) for r in all_results)
    total_verified = sum(r.get("verified", 0) for r in all_results)
    total_unclear = sum(r.get("unclear", 0) for r in all_results)
    total_rejected = sum(r.get("rejected", 0) for r in all_results)

    logger.info(f"Batches: {len(all_results)}")
    logger.info(f"Total processed: {total_processed}")
    logger.info(f"Verified hotel operators: {total_verified}")
    logger.info(f"Unclear / needs manual review: {total_unclear}")
    logger.info(f"Rejected: {total_rejected}")

    # Output JSON
    output = {
        "timestamp": datetime.now(UTC).isoformat(),
        "batches": all_results,
        "summary": {
            "total_processed": total_processed,
            "verified": total_verified,
            "unclear": total_unclear,
            "rejected": total_rejected,
        }
    }

    print(json.dumps(output, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
