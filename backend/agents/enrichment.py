import json
import logging
from backend.integrations.supabase_client import supabase
from backend.integrations.website_checker import check_for_chatbot
from backend.integrations.web_researcher import apollo_enrich_person, scrape_website_text, search_web
from backend.utils.anthropic_client import generate
from backend.prompts.system_prompts import ENRICHMENT_SYSTEM_PROMPT, INVESTOR_ENRICHMENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _gather_research(lead_data: dict) -> dict:
    """Run all research steps and return a consolidated context dict."""
    first = lead_data.get("first_name", "")
    last = lead_data.get("last_name", "")
    company = lead_data.get("company", "")
    website = lead_data.get("company_website", "")
    linkedin = lead_data.get("linkedin_url", "")

    logger.info("Researching %s %s at %s", first, last, company)

    # 1. Apollo — full LinkedIn profile + employment history + company data
    apollo = apollo_enrich_person(
        first_name=first,
        last_name=last,
        company_domain=website,
        linkedin_url=linkedin,
    )
    if apollo:
        logger.info("Apollo profile found for %s %s (%d past roles)",
                    first, last, len(apollo.get("employment_history", [])))

    # 2. Company website text
    website_text = scrape_website_text(website) if website else ""

    # 3. Web search — person mentions + company news
    person_query = f'"{first} {last}" "{company}" hospitality hotel'
    company_query = f'"{company}" hotel 2025 2026'
    person_results = search_web(person_query, max_results=4)
    company_results = search_web(company_query, max_results=4)

    return {
        "apollo": apollo,
        "website_text": website_text,
        "person_search": [
            {"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")}
            for r in person_results
        ],
        "company_search": [
            {"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")}
            for r in company_results
        ],
    }


def enrich_lead(lead_data: dict) -> dict:
    """Enrich a single lead with real web research, then Claude synthesis.

    Gathers:
    - Apollo person profile (LinkedIn, employment history, company data)
    - Company website text
    - DuckDuckGo search results for person + company

    Passes all real data to Claude Sonnet for structured enrichment output.
    Updates the Supabase lead record and returns the enrichment dict.
    """
    lead_id = lead_data.get("id")
    website = lead_data.get("company_website", "")

    # Chatbot check (score penalty)
    chatbot_detected = check_for_chatbot(website) if website else False
    if chatbot_detected:
        logger.info("Chatbot detected on %s — penalty will apply to lead %s", website, lead_id)

    # Gather all research data
    research = _gather_research(lead_data)
    apollo = research["apollo"]

    # Build the user message with all real research data
    employment_text = ""
    if apollo.get("employment_history"):
        lines = []
        for job in apollo["employment_history"]:
            end = job["end"] if not job["current"] else "present"
            lines.append(f"  {job['start']}–{end}: {job['title']} at {job['company']}")
        employment_text = "\n".join(lines)

    company_profile = apollo.get("company_profile", {})
    company_profile_text = ""
    if company_profile:
        parts = []
        if company_profile.get("description"):
            parts.append(f"Description: {company_profile['description']}")
        if company_profile.get("industry"):
            parts.append(f"Industry: {company_profile['industry']}")
        if company_profile.get("employees"):
            parts.append(f"Employees: ~{company_profile['employees']}")
        if company_profile.get("num_locations"):
            parts.append(f"Locations: {company_profile['num_locations']}")
        if company_profile.get("annual_revenue"):
            parts.append(f"Revenue: {company_profile['annual_revenue']}")
        if company_profile.get("keywords"):
            parts.append(f"Keywords: {', '.join(company_profile['keywords'])}")
        company_profile_text = "\n".join(parts)

    person_snippets = "\n".join(
        f"- {r['title']}: {r['snippet']}" for r in research["person_search"] if r["snippet"]
    ) or "No results found."

    company_snippets = "\n".join(
        f"- {r['title']}: {r['snippet']}" for r in research["company_search"] if r["snippet"]
    ) or "No results found."

    user_message = f"""Enrich this lead using the research data below.

LEAD:
  Name: {lead_data.get('first_name', '')} {lead_data.get('last_name', '')}
  Title: {lead_data.get('title', 'Unknown')}
  Company: {lead_data.get('company', 'Unknown')}
  Location: {lead_data.get('location', 'Unknown')}
  Email: {lead_data.get('email', 'Unknown')}
  LinkedIn: {lead_data.get('linkedin_url', 'Not provided')}
  Website: {lead_data.get('company_website', 'Not provided')}

APOLLO PROFILE:
  Headline: {apollo.get('headline', 'Not found')}
  Location: {apollo.get('city', '')}, {apollo.get('country', '')}
  Employment history:
{employment_text or '  Not found'}

COMPANY PROFILE (from Apollo):
{company_profile_text or '  Not found'}

COMPANY WEBSITE CONTENT:
{research['website_text'][:1500] or 'Could not fetch.'}

WEB SEARCH — PERSON MENTIONS:
{person_snippets}

WEB SEARCH — COMPANY NEWS:
{company_snippets}

Return valid JSON only — no markdown, no explanation."""

    raw = generate(ENRICHMENT_SYSTEM_PROMPT, user_message)

    try:
        enrichment = json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            enrichment = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse enrichment JSON for lead %s: %s", lead_id, raw[:200])
            enrichment = {
                "lead_score": 0,
                "warmth": "cold",
                "pain_signals": [],
                "personalisation_hooks": [],
                "company_context": "Enrichment parse error",
                "notes": raw[:500],
            }

    if lead_id:
        raw_score = enrichment.get("lead_score", 0)
        final_score = max(0, raw_score - 20) if chatbot_detected else raw_score

        enrichment["chatbot_detected"] = chatbot_detected
        enrichment["lead_score"] = final_score
        # Store the raw Apollo data for display in the UI
        if apollo:
            enrichment["apollo_profile"] = apollo

        update_payload = {
            "enrichment_data": enrichment,
            "lead_score": final_score,
            "warmth": enrichment.get("warmth", "cold"),
            "pain_signals": enrichment.get("pain_signals", []),
            "personalisation_hooks": enrichment.get("personalisation_hooks", []),
            "chatbot_detected": chatbot_detected,
            "pipeline_stage": "enriched",
        }
        # Backfill email from Apollo if not already set
        if apollo.get("email") and not lead_data.get("email"):
            update_payload["email"] = apollo["email"]

        supabase.table("leads").update(update_payload).eq("id", lead_id).execute()
        logger.info(
            "Lead %s enriched — score %s%s, warmth %s",
            lead_id, final_score,
            " (chatbot penalty)" if chatbot_detected else "",
            enrichment.get("warmth"),
        )

    return enrichment


def enrich_investor(investor_data: dict) -> dict:
    """Enrich an investor target with real web research, then Claude synthesis.

    Gathers Apollo contact profile, firm website, and web search results for
    the contact person and firm. Stores structured enrichment_data in Supabase.
    """
    investor_id = investor_data.get("id")
    firm = investor_data.get("firm_name", "")
    contact = investor_data.get("contact_name", "")
    contact_linkedin = investor_data.get("contact_linkedin", "")
    website = investor_data.get("website_url", "")

    first, *rest = contact.split(" ") if contact else ("", [])
    last = " ".join(rest) if rest else ""

    logger.info("Researching investor contact %s at %s", contact, firm)

    apollo = apollo_enrich_person(
        first_name=first,
        last_name=last,
        company_domain=website,
        linkedin_url=contact_linkedin,
    )

    website_text = scrape_website_text(website) if website else ""

    person_results = search_web(f'"{contact}" "{firm}" investor venture', max_results=4)
    firm_results = search_web(f'"{firm}" portfolio investment hospitality AI SaaS 2024 2025', max_results=4)

    employment_text = ""
    if apollo.get("employment_history"):
        lines = [
            f"  {j['start']}–{j['end'] if not j['current'] else 'present'}: {j['title']} at {j['company']}"
            for j in apollo["employment_history"]
        ]
        employment_text = "\n".join(lines)

    person_snippets = "\n".join(
        f"- {r['title']}: {r['snippet']}" for r in person_results if r.get("snippet")
    ) or "No results."

    firm_snippets = "\n".join(
        f"- {r['title']}: {r['snippet']}" for r in firm_results if r.get("snippet")
    ) or "No results."

    user_message = f"""Research this investor contact and produce a structured enrichment profile.

INVESTOR TARGET:
  Firm: {firm}
  Type: {investor_data.get('investor_type', 'Unknown')}
  Tier: {investor_data.get('tier', 'Unknown')}
  Contact: {contact}
  Contact LinkedIn: {contact_linkedin or 'Not provided'}
  Why fit (existing notes): {investor_data.get('why_fit', 'Not provided')}
  Warm path (existing notes): {investor_data.get('warm_path', 'None')}
  Check size: {investor_data.get('check_size_range', 'Unknown')}

APOLLO CONTACT PROFILE:
  Headline: {apollo.get('headline', 'Not found')}
  Location: {apollo.get('city', '')}, {apollo.get('country', '')}
  Employment history:
{employment_text or '  Not found'}

FIRM WEBSITE:
{website_text[:1500] or 'Could not fetch.'}

WEB SEARCH — CONTACT MENTIONS:
{person_snippets}

WEB SEARCH — FIRM / PORTFOLIO NEWS:
{firm_snippets}

Return valid JSON only — no markdown, no explanation."""

    raw = generate(INVESTOR_ENRICHMENT_SYSTEM_PROMPT, user_message)

    try:
        enrichment = json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            enrichment = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse investor enrichment JSON for %s: %s", investor_id, raw[:200])
            enrichment = {"fit_score": 0, "notes": raw[:500]}

    if investor_id:
        if apollo:
            enrichment["apollo_profile"] = apollo

        update_payload = {
            "enrichment_data": enrichment,
            "pipeline_stage": "research_needed"
            if investor_data.get("pipeline_stage") == "identified"
            else investor_data.get("pipeline_stage"),
        }
        if apollo.get("email") and not investor_data.get("contact_email"):
            update_payload["contact_email"] = apollo["email"]
        if apollo.get("linkedin_url") and not investor_data.get("contact_linkedin"):
            update_payload["contact_linkedin"] = apollo["linkedin_url"]

        supabase.table("investor_targets").update(update_payload).eq("id", investor_id).execute()
        logger.info("Investor %s (%s) enriched — fit score %s", firm, contact, enrichment.get("fit_score"))

    return enrichment


def enrich_batch(lead_ids: list[str]) -> list[dict]:
    """Enrich up to 5 leads sequentially (rate-limit protection)."""
    if len(lead_ids) > 5:
        logger.warning("enrich_batch called with %d leads — capping at 5", len(lead_ids))
        lead_ids = lead_ids[:5]

    results = []
    for lead_id in lead_ids:
        response = supabase.table("leads").select("*").eq("id", lead_id).single().execute()
        lead = response.data
        if not lead:
            logger.warning("Lead %s not found — skipping", lead_id)
            results.append({"error": f"Lead {lead_id} not found"})
            continue
        result = enrich_lead(lead)
        results.append(result)

    return results
