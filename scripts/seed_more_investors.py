"""Seed 52 additional investor targets: voice/AI, CX automation, European, APAC, accelerators, angels."""
from dotenv import load_dotenv

load_dotenv()

from backend.integrations.supabase_client import supabase

INVESTORS = [
    # --- VOICE / AI SPECIALISTS ---
    {"firm_name": "Conviction", "contact_name": "Sarah Guo", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "Former a16z GP focused on AI. Voice AI thesis aligns directly with First Wave product.", "pipeline_stage": "identified"},
    {"firm_name": "AIX Ventures", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "AI-first seed fund. Operational AI in hospitality is core to their thesis.", "pipeline_stage": "identified"},
    {"firm_name": "Unusual Ventures", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "Known for enterprise AI investments. Deep founder support and strong B2B SaaS track record.", "pipeline_stage": "identified"},
    {"firm_name": "Madrona Venture Group", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "Seattle-based, strong AI infrastructure and applied AI portfolio.", "pipeline_stage": "identified"},
    {"firm_name": "Costanoa Ventures", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "B2B SaaS focus with enterprise AI orientation. Good fit for sales automation angle.", "pipeline_stage": "identified"},

    # --- CX AUTOMATION ---
    {"firm_name": "Emergence Capital", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "Cloud enterprise software specialist. CX automation and AI sales tooling is in their wheelhouse.", "pipeline_stage": "identified"},
    {"firm_name": "Bain Capital Ventures", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "Strong enterprise software track record. CX and B2B AI portfolio.", "pipeline_stage": "identified"},
    {"firm_name": "Ridge Ventures", "investor_type": "seed_vc", "tier": 3,
     "why_fit": "Enterprise SaaS seed investor. CX tooling focus.", "pipeline_stage": "identified"},
    {"firm_name": "Wing VC", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "Enterprise AI and automation focus. Proactive value-add investors.", "pipeline_stage": "identified"},

    # --- EUROPEAN VCs ---
    {"firm_name": "Fly Ventures", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "Berlin-based seed fund with strong B2B SaaS thesis. Natural fit for Berlin-based First Wave AI.", "pipeline_stage": "identified"},
    {"firm_name": "HV Capital", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "One of Europe's largest tech VCs. Strong consumer and enterprise portfolio.", "pipeline_stage": "identified"},
    {"firm_name": "Point Nine Capital", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "Berlin-based SaaS specialist. Backed multiple AI B2B companies. Strong network in DACH.", "pipeline_stage": "identified"},
    {"firm_name": "Cherry Ventures", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "Berlin seed fund with deep SaaS and AI portfolio. Liam's Berlin base is a warm signal.", "pipeline_stage": "identified"},
    {"firm_name": "La Famiglia", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "European VC backed by European business families. Hospitality networks are directly relevant.", "pipeline_stage": "identified"},
    {"firm_name": "Project A Ventures", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "Berlin operational VC with in-house engineering and marketing support. B2B SaaS focus.", "pipeline_stage": "identified"},
    {"firm_name": "42CAP", "investor_type": "seed_vc", "tier": 3,
     "why_fit": "Munich-based B2B SaaS seed fund. DACH market expertise.", "pipeline_stage": "identified"},
    {"firm_name": "Dawn Capital", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "European enterprise software specialist. B2B AI is a key area.", "pipeline_stage": "identified"},
    {"firm_name": "Balderton Capital", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "Pan-European VC. Strong B2B and enterprise track record.", "pipeline_stage": "identified"},
    {"firm_name": "LocalGlobe", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "London seed fund. Deep European tech network and B2B SaaS focus.", "pipeline_stage": "identified"},
    {"firm_name": "Notion Capital", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "Backed Mews (hotel PMS) — direct warm signal for hospitality tech understanding.", "pipeline_stage": "identified"},

    # --- APAC ---
    {"firm_name": "Jungle Ventures", "investor_type": "seed_vc", "tier": 3,
     "why_fit": "Southeast Asia focused. Singapore hotel group market relevance.", "pipeline_stage": "identified"},
    {"firm_name": "Wavemaker Partners", "investor_type": "seed_vc", "tier": 3,
     "why_fit": "SEA B2B tech specialist. Good fit for Singapore/HK market campaigns.", "pipeline_stage": "identified"},
    {"firm_name": "Sequoia Capital India & SEA", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "India and SEA operations. India hotel market campaign alignment.", "pipeline_stage": "identified"},
    {"firm_name": "Antler India", "investor_type": "accelerator", "tier": 4,
     "why_fit": "Global accelerator with India operations. Good entry point for APAC expansion story.", "pipeline_stage": "identified"},

    # --- ACCELERATORS ---
    {"firm_name": "Antler", "investor_type": "accelerator", "tier": 4,
     "why_fit": "Global accelerator with Berlin operations. Relevant for European network and follow-on VCs.", "pipeline_stage": "identified"},
    {"firm_name": "Entrepreneur First (EF)", "investor_type": "accelerator", "tier": 4,
     "why_fit": "London/Berlin accelerator. Strong AI and deep tech track record.", "pipeline_stage": "identified"},
    {"firm_name": "Plug and Play Hospitality", "investor_type": "accelerator", "tier": 3,
     "why_fit": "Hospitality vertical accelerator. Corporate partners are direct potential clients.", "pipeline_stage": "identified"},
    {"firm_name": "Startupbootcamp", "investor_type": "accelerator", "tier": 4,
     "why_fit": "European accelerator with smart city and hospitality verticals.", "pipeline_stage": "identified"},

    # --- ANGELS ---
    {"firm_name": "Elad Gil", "contact_name": "Elad Gil", "investor_type": "angel", "tier": 2,
     "why_fit": "High-profile AI angel. Backed many AI-first B2B companies.", "pipeline_stage": "identified"},
    {"firm_name": "Nat Friedman", "contact_name": "Nat Friedman", "investor_type": "angel", "tier": 2,
     "why_fit": "Former GitHub CEO, active AI angel. Strong enterprise software perspective.", "pipeline_stage": "identified"},
    {"firm_name": "Jason Calacanis", "contact_name": "Jason Calacanis", "investor_type": "angel", "tier": 3,
     "why_fit": "LAUNCH fund and angel. Strong B2B SaaS network.", "pipeline_stage": "identified"},
    {"firm_name": "David Sacks", "contact_name": "David Sacks", "investor_type": "angel", "tier": 2,
     "why_fit": "Former PayPal/Yammer exec. Deep B2B enterprise and AI credibility.", "pipeline_stage": "identified"},
    {"firm_name": "Sheel Mohnot", "contact_name": "Sheel Mohnot", "investor_type": "angel", "tier": 3,
     "why_fit": "Better Tomorrow Ventures. Fintech and B2B tools focus.", "pipeline_stage": "identified"},
    {"firm_name": "Lenny Rachitsky", "contact_name": "Lenny Rachitsky", "investor_type": "angel", "tier": 3,
     "why_fit": "Product-focused angel with massive audience of B2B buyers.", "pipeline_stage": "identified"},
    {"firm_name": "SV Angel", "investor_type": "angel", "tier": 3,
     "why_fit": "Ron Conway's fund. Strong network effects and B2B credibility.", "pipeline_stage": "identified"},

    # --- ADDITIONAL EUROPEAN / SEED ---
    {"firm_name": "Headline", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "US/European hybrid. B2B SaaS focus with strong AI portfolio.", "pipeline_stage": "identified"},
    {"firm_name": "Atlantic Labs", "investor_type": "seed_vc", "tier": 3,
     "why_fit": "Berlin-based early-stage fund. DACH tech ecosystem depth.", "pipeline_stage": "identified"},
    {"firm_name": "Nauta Capital", "investor_type": "seed_vc", "tier": 3,
     "why_fit": "European B2B SaaS specialist. Spain/UK/Germany presence.", "pipeline_stage": "identified"},
    {"firm_name": "Partech", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "European-US tech VC. Strong AI and enterprise software track record.", "pipeline_stage": "identified"},
    {"firm_name": "Northzone", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "Nordic/European VC. Enterprise and consumer tech. Strong Nordics market reach.", "pipeline_stage": "identified"},
    {"firm_name": "Speedinvest", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "Vienna-based, strong in DACH and CEE. B2B SaaS and deep tech portfolio.", "pipeline_stage": "identified"},
    {"firm_name": "Accel (London)", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "Top global VC with strong European enterprise focus.", "pipeline_stage": "identified"},
    {"firm_name": "Index Ventures (London)", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "Premier European VC. Strong SaaS and enterprise software track record.", "pipeline_stage": "identified"},
    {"firm_name": "Atomico", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "Skype founders' fund. Deep European tech network.", "pipeline_stage": "identified"},
    {"firm_name": "Earlybird", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "Berlin-based, digital tech focus, strong DACH presence.", "pipeline_stage": "identified"},
    {"firm_name": "Global Founders Capital", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "Zalando founders' fund. European tech network and B2B portfolio.", "pipeline_stage": "identified"},
    {"firm_name": "Lakestar", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "European tech VC with strong enterprise software track record.", "pipeline_stage": "identified"},
    {"firm_name": "Bessemer Venture Partners (EU)", "investor_type": "series_a_vc", "tier": 3,
     "why_fit": "Global VC with strong B2B SaaS track record. AI-first investing.", "pipeline_stage": "identified"},
    {"firm_name": "Creandum", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "Nordic/European early-stage. Strong Nordics market access for hotel campaigns.", "pipeline_stage": "identified"},
    {"firm_name": "Stride.VC", "investor_type": "seed_vc", "tier": 2,
     "why_fit": "London B2B seed specialist. Deep enterprise software network.", "pipeline_stage": "identified"},
    {"firm_name": "Picus Capital", "investor_type": "seed_vc", "tier": 3,
     "why_fit": "Munich/Berlin based. Tech-enabled services and B2B SaaS focus.", "pipeline_stage": "identified"},
    {"firm_name": "Target Global", "investor_type": "seed_vc", "tier": 3,
     "why_fit": "Berlin-based. Strong Israeli-European tech bridge. B2B and enterprise portfolio.", "pipeline_stage": "identified"},
]


def main() -> None:
    # Load existing firm names to avoid duplicates
    existing = supabase.table("investor_targets").select("firm_name").execute().data or []
    known: set[str] = {r["firm_name"].lower() for r in existing if r.get("firm_name")}

    to_insert = [inv for inv in INVESTORS if inv["firm_name"].lower() not in known]
    skipped = len(INVESTORS) - len(to_insert)

    if not to_insert:
        print("All investors already in DB — nothing to insert.")
        return

    for i in range(0, len(to_insert), 50):
        batch = to_insert[i : i + 50]
        supabase.table("investor_targets").insert(batch).execute()

    print(f"Seeded {len(to_insert)} new investors. Skipped {skipped} already present.")


if __name__ == "__main__":
    main()
