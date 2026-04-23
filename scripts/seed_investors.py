"""Seed the investor_targets table with all 50 pre-built targets."""
from dotenv import load_dotenv

load_dotenv()

from backend.integrations.supabase_client import supabase

INVESTORS = [
    # TIER 1 — Hospitality & Travel Tech VCs (liam_leads = True)
    {"firm_name": "Derive Ventures", "investor_type": "seed_vc", "tier": 1, "liam_leads": True,
     "why_fit": "Hospitality-focused VC with deep operator network. Liam opens with operator credibility and references their portfolio.",
     "pipeline_stage": "identified"},
    {"firm_name": "Thayer Ventures", "investor_type": "seed_vc", "tier": 1, "liam_leads": True,
     "why_fit": "Travel and hospitality technology specialist. Strong fit given First Wave AI's pilot proof in hotel operations.",
     "pipeline_stage": "identified"},
    {"firm_name": "Branded Hospitality Ventures", "investor_type": "seed_vc", "tier": 1, "liam_leads": True,
     "why_fit": "Operator-backed hospitality VC. Credibility match: Liam's A&O/Selina background speaks directly to their investment thesis.",
     "pipeline_stage": "identified"},
    {"firm_name": "Journey Ventures", "investor_type": "seed_vc", "tier": 1, "liam_leads": True,
     "why_fit": "Travel tech and hospitality investor. First Wave AI's unanswered-call proof point aligns with their guest experience focus.",
     "pipeline_stage": "identified"},
    {"firm_name": "Jaws Ventures", "investor_type": "seed_vc", "tier": 1, "liam_leads": True,
     "why_fit": "Hospitality and travel VC. Relevant portfolio in CX and operations tech for hotel groups.",
     "pipeline_stage": "identified"},
    {"firm_name": "JetBlue Technology Ventures", "investor_type": "cvc", "tier": 1, "liam_leads": True,
     "why_fit": "Travel-sector CVC investing in operational AI and CX. Guest experience angle is directly relevant.",
     "pipeline_stage": "identified"},
    {"firm_name": "MairDuMont Ventures", "investor_type": "seed_vc", "tier": 1, "liam_leads": True,
     "why_fit": "European travel and hospitality investor. Strong relevance for DACH market expansion strategy.",
     "pipeline_stage": "identified"},
    {"firm_name": "Fifth Wall", "investor_type": "seed_vc", "tier": 1, "liam_leads": True,
     "why_fit": "Real estate and hospitality tech investor with significant hotel operator relationships in their network.",
     "pipeline_stage": "identified"},
    {"firm_name": "Howzat Partners", "investor_type": "seed_vc", "tier": 1, "liam_leads": True,
     "why_fit": "Hospitality-focused fund with portfolio companies in hotel tech. Peer outreach from Liam makes sense.",
     "pipeline_stage": "identified"},
    {"firm_name": "Big Rock Ventures", "investor_type": "seed_vc", "tier": 1, "liam_leads": True,
     "why_fit": "Travel and hospitality VC. Operator credibility story resonates with their typical investment framework.",
     "pipeline_stage": "identified"},

    # TIER 2 — Vertical AI / B2B SaaS Pre-Seed (liam_leads = False)
    {"firm_name": "Outlander VC", "investor_type": "pre_seed", "tier": 2, "liam_leads": False,
     "why_fit": "Pre-seed B2B SaaS investor. Lead with market size and defensible hybrid moat vs. pure AI commoditisation.",
     "pipeline_stage": "identified"},
    {"firm_name": "Ascend VC", "investor_type": "pre_seed", "tier": 2, "liam_leads": False,
     "why_fit": "Vertical SaaS and AI pre-seed. Highlight pilot traction and unit economics vs. traditional outsourcing.",
     "pipeline_stage": "identified"},
    {"firm_name": "Pear VC", "investor_type": "pre_seed", "tier": 2, "liam_leads": False,
     "why_fit": "Pre-seed to seed B2B SaaS. Strong track record in vertical AI. Traction-led narrative fits their criteria.",
     "pipeline_stage": "identified"},
    {"firm_name": "Amplify Partners", "investor_type": "pre_seed", "tier": 2, "liam_leads": False,
     "why_fit": "Developer tools and infrastructure investor expanding into vertical AI. Technical differentiation angle.",
     "pipeline_stage": "identified"},
    {"firm_name": "Audacious VC", "investor_type": "pre_seed", "tier": 2, "liam_leads": False,
     "why_fit": "$750K ask with clear ARR path and pilot proof is within their sweet spot for pre-seed vertical AI.",
     "pipeline_stage": "identified"},
    {"firm_name": "2048 Ventures", "investor_type": "pre_seed", "tier": 2, "liam_leads": False,
     "why_fit": "Pre-seed B2B SaaS. They back contrarian theses — human+AI hybrid is the contrarian bet against pure automation.",
     "pipeline_stage": "identified"},
    {"firm_name": "Forum Ventures", "investor_type": "pre_seed", "tier": 2, "liam_leads": False,
     "why_fit": "B2B SaaS accelerator and pre-seed fund. Apply through intake form while pursuing warm intro simultaneously.",
     "pipeline_stage": "identified"},
    {"firm_name": "Precursor Ventures", "investor_type": "pre_seed", "tier": 2, "liam_leads": False,
     "why_fit": "Invests at the earliest stage in B2B SaaS. Founder-first philosophy; Philip's AWS background is compelling.",
     "pipeline_stage": "identified"},
    {"firm_name": "Founder Collective", "investor_type": "pre_seed", "tier": 2, "liam_leads": False,
     "why_fit": "Pre-seed B2B. Portfolio includes CX and vertical SaaS. Operator credentials plus pilot traction match their bar.",
     "pipeline_stage": "identified"},
    {"firm_name": "Beta Boom", "investor_type": "pre_seed", "tier": 2, "liam_leads": False,
     "why_fit": "Diversity-focused pre-seed fund investing in underserved markets. Strong mission fit with accessible hospitality AI.",
     "pipeline_stage": "identified"},

    # TIER 3 — Accelerators (liam_leads = False — Philip leads)
    {"firm_name": "Y Combinator", "investor_type": "accelerator", "tier": 3, "liam_leads": False,
     "why_fit": "Top global accelerator. Philip leads the application. Liam referenced for domain credibility and pilot proof.",
     "pipeline_stage": "identified"},
    {"firm_name": "Techstars", "investor_type": "accelerator", "tier": 3, "liam_leads": False,
     "why_fit": "Global accelerator with hospitality and travel verticals. Strong corporate sponsor network in hotel sector.",
     "pipeline_stage": "identified"},
    {"firm_name": "500 Global", "investor_type": "accelerator", "tier": 3, "liam_leads": False,
     "why_fit": "Global accelerator with strong EMEA presence. Relevant for European market expansion narrative.",
     "pipeline_stage": "identified"},
    {"firm_name": "a16z START", "investor_type": "accelerator", "tier": 3, "liam_leads": False,
     "why_fit": "Andreessen Horowitz accelerator program for early AI companies. High bar, high reward for category definition.",
     "pipeline_stage": "identified"},
    {"firm_name": "NFX", "investor_type": "accelerator", "tier": 3, "liam_leads": False,
     "why_fit": "Network-effects focused fund and accelerator. Guest experience platform has genuine network effects at scale.",
     "pipeline_stage": "identified"},

    # TIER 4 — Enterprise AI / CX (liam_leads = False)
    {"firm_name": "First Round Capital", "investor_type": "seed_vc", "tier": 4, "liam_leads": False,
     "why_fit": "Tier 1 seed fund with strong B2B SaaS portfolio. Higher bar but strong signal if they engage.",
     "pipeline_stage": "identified"},
    {"firm_name": "SaaStr Fund", "investor_type": "seed_vc", "tier": 4, "liam_leads": False,
     "why_fit": "Jason Lemkin's B2B SaaS seed fund. Revenue-focused; $80K ARR with clear path to $500K is the hook.",
     "pipeline_stage": "identified"},
    {"firm_name": "Salesforce Ventures", "investor_type": "cvc", "tier": 4, "liam_leads": False,
     "why_fit": "CRM and CX-adjacent CVC. First Wave AI's post-call workflow automation integrates naturally with CRM stack.",
     "pipeline_stage": "identified"},
    {"firm_name": "HubSpot Ventures", "investor_type": "cvc", "tier": 4, "liam_leads": False,
     "why_fit": "Inbound marketing and CX CVC. Guest communication and lead capture angle is directly relevant.",
     "pipeline_stage": "identified"},
    {"firm_name": "FirstMark Capital", "investor_type": "seed_vc", "tier": 4, "liam_leads": False,
     "why_fit": "NYC-based seed to Series A with SaaS focus. AI-native CX is a core thesis area.",
     "pipeline_stage": "identified"},
    {"firm_name": "Glasswing Ventures", "investor_type": "seed_vc", "tier": 4, "liam_leads": False,
     "why_fit": "Enterprise AI specialist. Technical differentiation (AWS infrastructure + human oversight) fits their thesis.",
     "pipeline_stage": "identified"},
    {"firm_name": "Lerer Hippeau", "investor_type": "seed_vc", "tier": 4, "liam_leads": False,
     "why_fit": "NYC seed fund with consumer and enterprise SaaS. Hospitality at intersection of consumer and B2B.",
     "pipeline_stage": "identified"},
    {"firm_name": "White Star Capital", "investor_type": "seed_vc", "tier": 4, "liam_leads": False,
     "why_fit": "Transatlantic fund with European presence. Strong fit for Berlin-based operation targeting EU hotel groups.",
     "pipeline_stage": "identified"},
    {"firm_name": "HOF Capital", "investor_type": "seed_vc", "tier": 4, "liam_leads": False,
     "why_fit": "NYC seed fund. B2B AI and SaaS focus. Pilot economics ($2,496/month savings) are a compelling headline.",
     "pipeline_stage": "identified"},
    {"firm_name": "Trinity Ventures", "investor_type": "seed_vc", "tier": 4, "liam_leads": False,
     "why_fit": "Enterprise SaaS seed fund. Operational AI with measurable ROI fits their investment criteria.",
     "pipeline_stage": "identified"},

    # TIER 5 — European VCs (liam_leads = True)
    {"firm_name": "Seedcamp", "investor_type": "seed_vc", "tier": 5, "liam_leads": True,
     "why_fit": "Pan-European pre-seed and seed. Liam's European operator network gives a credible warm intro path.",
     "pipeline_stage": "identified"},
    {"firm_name": "Heartcore Capital", "investor_type": "seed_vc", "tier": 5, "liam_leads": True,
     "why_fit": "Copenhagen-based consumer and B2B fund. Strong Nordics network aligns with Liam's Priority 1 geographies.",
     "pipeline_stage": "identified"},
    {"firm_name": "Playfair Capital", "investor_type": "seed_vc", "tier": 5, "liam_leads": True,
     "why_fit": "London-based pre-seed. B2B SaaS thesis. UK hospitality market is Priority 1 for client pipeline too.",
     "pipeline_stage": "identified"},
    {"firm_name": "Earlybird Ventures", "investor_type": "seed_vc", "tier": 5, "liam_leads": True,
     "why_fit": "Pan-European early-stage VC with DACH strength. Berlin-based operations match Liam's location advantage.",
     "pipeline_stage": "identified"},
    {"firm_name": "Partech", "investor_type": "seed_vc", "tier": 5, "liam_leads": True,
     "why_fit": "Franco-German VC with strong enterprise SaaS portfolio. European hospitality operator credibility is the angle.",
     "pipeline_stage": "identified"},
    {"firm_name": "Icebreaker.vc", "investor_type": "pre_seed", "tier": 5, "liam_leads": True,
     "why_fit": "Nordic pre-seed fund. Hospitality is a significant sector in the Nordics. Personal outreach from Liam.",
     "pipeline_stage": "identified"},
    {"firm_name": "TheVentureCity", "investor_type": "seed_vc", "tier": 5, "liam_leads": True,
     "why_fit": "European and LatAm early-stage fund. Globalisation of hospitality AI is a credible expansion story.",
     "pipeline_stage": "identified"},
    {"firm_name": "Stride.VC", "investor_type": "pre_seed", "tier": 5, "liam_leads": True,
     "why_fit": "London-based pre-seed. B2B SaaS and AI focus. UK hotel group pipeline makes this immediately relevant.",
     "pipeline_stage": "identified"},

    # TIER 6 — Angels (liam_leads = True)
    {"firm_name": "Ryan Hoover", "investor_type": "angel", "tier": 6, "liam_leads": True,
     "why_fit": "Product Hunt founder and angel investor. Consumer-facing AI and hospitality experience are adjacent interests.",
     "pipeline_stage": "identified"},
    {"firm_name": "Gokul Rajaram", "investor_type": "angel", "tier": 6, "liam_leads": True,
     "why_fit": "Ex-Google, Facebook, DoorDash. Operator angel with deep knowledge of unit economics and scaling CX.",
     "pipeline_stage": "identified"},
    {"firm_name": "AngelList Hospitality Syndicates", "investor_type": "angel", "tier": 6, "liam_leads": True,
     "why_fit": "Curated syndicates of hospitality-focused angels. Direct relevance; collective check size can be meaningful.",
     "pipeline_stage": "identified"},
    {"firm_name": "Alumni Ventures", "investor_type": "angel", "tier": 6, "liam_leads": True,
     "why_fit": "Alumni-network fund investing in early-stage companies. Broad network for warm intro sourcing.",
     "pipeline_stage": "identified"},
    {"firm_name": "Golden Seeds", "investor_type": "angel", "tier": 6, "liam_leads": True,
     "why_fit": "Women-led angel network investing in diverse founding teams. Respectful one-liner outreach from Liam.",
     "pipeline_stage": "identified"},
    {"firm_name": "Regional Angel Networks", "investor_type": "angel", "tier": 6, "liam_leads": True,
     "why_fit": "DACH and UK regional angel groups with hospitality operator members. Liam's network has natural overlap.",
     "pipeline_stage": "identified"},
    {"firm_name": "Launch Capital", "investor_type": "angel", "tier": 6, "liam_leads": True,
     "why_fit": "Jason Calacanis's early-stage fund. High volume dealflow; concise one-liner and pilot traction is the pitch.",
     "pipeline_stage": "identified"},
]


def seed() -> None:
    existing = supabase.table("investor_targets").select("firm_name").execute()
    existing_names = {r["firm_name"] for r in existing.data}

    to_insert = [i for i in INVESTORS if i["firm_name"] not in existing_names]
    if not to_insert:
        print("All 50 investors already seeded.")
        return

    result = supabase.table("investor_targets").insert(to_insert).execute()
    print(f"Seeded {len(result.data)} investor targets.")

    total = supabase.table("investor_targets").select("id", count="exact").execute()
    print(f"Total in DB: {total.count}")


if __name__ == "__main__":
    seed()
