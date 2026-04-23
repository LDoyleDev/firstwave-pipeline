"""Phase 7: Update investor_targets with contact_name, warm_path, and check_size_range.

Run: PYTHONPATH=. venv/bin/python3 scripts/update_investor_contacts.py
"""
from dotenv import load_dotenv
load_dotenv()

from backend.integrations.supabase_client import supabase

# Each entry: (firm_name, contact_name, check_size_range, warm_path)
# warm_path only set for Tier 1 (Liam leads) where his network is relevant.
UPDATES = [
    # --- TIER 1: Hospitality & Travel Tech VCs ---
    (
        "Derive Ventures",
        "Rachel Sheerin",
        "$250K–$2M",
        "Hospitality-specialist fund — Liam's Selina/A&O operator background and pilot proof points are a direct fit. Reference guest-experience mandate in opener.",
    ),
    (
        "Thayer Ventures",
        "Chris Hemmeter",
        "$500K–$3M",
        "Travel-tech focused; Chris Hemmeter has deep hotel industry ties. Liam's former COO role at Selina (tech-forward hospitality brand) is a credible warm signal.",
    ),
    (
        "Branded Hospitality Ventures",
        "David Bloom",
        "$250K–$2M",
        "Invested directly in hospitality-facing tech. David Bloom's background in hotel brand operations overlaps with Liam's COO experience — lead with the unanswered-call stat.",
    ),
    (
        "Journey Ventures",
        "Zach Friedman",
        "$250K–$2M",
        "Travel and hospitality vertical specialist. Liam's ITB Berlin 2026 attendance and European operator network provide a credible context to open with.",
    ),
    (
        "Jaws Ventures",
        "Shawn Kaplan",
        "$500K–$3M",
        "Hospitality and travel tech fund. Liam's operator network in Europe (DACH, Nordics) aligns with portfolio thesis — reference shared connections if any emerge from LinkedIn.",
    ),
    (
        "JetBlue Technology Ventures",
        "Amy Burr",
        "$500K–$3M",
        "CVC with travel-tech focus. Liam's front-line hotel operations experience and live pilot data are the strongest openers — frame around guest experience ROI.",
    ),
    (
        "MairDuMont Ventures",
        "Clemens Urlacher",
        "$250K–$2M",
        "German travel-media/tech CVC based in Stuttgart — Liam is Berlin-based, same German market. Strong geographic alignment; reference German hotel groups already in ICP.",
    ),
    (
        "Fifth Wall",
        "Brendan Wallace",
        "$1M–$5M",
        "PropTech/hospitality crossover fund with European presence. Liam's A&O Hotels background (budget hospitality at scale) is directly relevant to Fifth Wall's built-environment thesis.",
    ),
    (
        "Howzat Partners",
        "Mihir Karkare",
        "$250K–$2M",
        "Boutique fund focused on travel and hospitality. Liam's network of hotel group operators in DACH and Nordics is a direct warm signal — open with a shared industry reference.",
    ),
    (
        "Big Rock Ventures",
        "Craig Weiss",
        "$250K–$1.5M",
        "Hospitality-tech seed fund. Pilot proof points (5,817 staff minutes saved, $2,496/month savings) are the strongest opener — Craig Weiss responds to traction.",
    ),

    # --- TIER 2: Vertical AI / B2B SaaS Pre-Seed ---
    ("Outlander VC", "Paige Craig", "$100K–$500K", None),
    ("Ascend VC", "Elizabeth Galbut", "$250K–$1M", None),
    ("Pear VC", "Pejman Nozad", "$500K–$2M", None),
    ("Amplify Partners", "Mike Dauber", "$500K–$2M", None),
    ("Audacious VC", "Dhruv Dhanraj", "$250K–$1M", None),
    ("2048 Ventures", "Alex Iskold", "$100K–$500K", None),
    ("Forum Ventures", "Adam Boyden", "$250K–$1M", None),
    ("Precursor Ventures", "Charles Hudson", "$250K–$1M", None),
    ("Founder Collective", "Eric Paley", "$500K–$2M", None),
    ("Beta Boom", "Andres Rueda", "$100K–$500K", None),

    # --- TIER 3: Accelerators ---
    ("Y Combinator", "Garry Tan", "Program + $500K", None),
    ("Techstars", "David Cohen", "Program + $120K", None),
    ("500 Global", "Christine Tsai", "Program + $150K", None),
    ("a16z START", "Martin Casado", "Program terms", None),
    ("NFX", "James Currier", "$500K–$3M", None),

    # --- TIER 4: Enterprise AI / CX ---
    ("First Round Capital", "Josh Kopelman", "$1M–$5M", None),
    ("SaaStr Fund", "Jason Lemkin", "$500K–$3M", None),
    ("Salesforce Ventures", "Alex Kayyal", "$1M–$10M", None),
    ("HubSpot Ventures", "Matthew Barby", "$500K–$3M", None),
    ("FirstMark Capital", "Rick Heitzmann", "$1M–$5M", None),
    ("Glasswing Ventures", "Rudina Seseri", "$500K–$3M", None),
    ("Lerer Hippeau", "Ben Lerer", "$500K–$3M", None),
    ("White Star Capital", "Eric Martineau-Fortin", "$500K–$3M", None),
    ("HOF Capital", "Shen Ning", "$500K–$3M", None),
    ("Trinity Ventures", "Karan Mehandru", "$500K–$3M", None),

    # --- TIER 5: European ---
    (
        "Seedcamp",
        "Reshma Sohoni",
        "$100K–$2M",
        "Pan-European pre-seed fund, London-based. Liam's Berlin location and European operator network align well — Reshma Sohoni responds to founder-market fit stories.",
    ),
    (
        "Heartcore Capital",
        "Søren Primdahl",
        "$500K–$5M",
        "Copenhagen/Berlin-based consumer/B2B fund. Liam is Berlin-based — same city as Heartcore's German office. Strong geographic and language alignment.",
    ),
    (
        "Playfair Capital",
        "Federico Pirzio-Biroli",
        "$250K–$2M",
        "London-based pre-seed fund focused on B2B SaaS. UK is Priority 1 geography for First Wave AI ICP — Federico values operational founders with domain depth.",
    ),
    (
        "Earlybird Ventures",
        "Hendrik Brandis",
        "$1M–$10M",
        "One of Europe's top early-stage VCs; Berlin HQ. Liam is Berlin-based — direct geographic connection. Reference the DACH hospitality market size in opener.",
    ),
    (
        "Partech",
        "Omri Benayoun",
        "$500K–$5M",
        "Paris/Berlin/San Francisco fund with strong European LP base. Liam's multilingual European operator background (Selina, A&O across 12 countries) is a strong opener.",
    ),
    (
        "Icebreaker.vc",
        "Mikko Silventola",
        "$100K–$1M",
        "Helsinki-based early-stage fund — Nordics is a Priority 1 geography for First Wave AI. Liam's Nordic hotel operator connections are a warm signal.",
    ),
    (
        "TheVentureCity",
        "Laura González-Estéfani",
        "$250K–$2M",
        "Miami/Madrid-based fund with European portfolio companies. Laura González-Estéfani's product/operator background aligns with First Wave AI's hybrid model story.",
    ),
    (
        "Stride.VC",
        "Harry Briggs",
        "$500K–$3M",
        "London-based B2B SaaS seed fund. Harry Briggs has spoken publicly about AI-native B2B tools — frame around the operator-grade AI angle, not generic chatbot.",
    ),

    # --- TIER 6: Angels ---
    (
        "Ryan Hoover",
        "Ryan Hoover",
        "$25K–$100K",
        "Product Hunt founder and active angel. Open via Twitter/X or AngelList DM — one short paragraph, no deck. Ryan invests in products he'd personally use.",
    ),
    (
        "Gokul Rajaram",
        "Gokul Rajaram",
        "$25K–$100K",
        "DoorDash board member and prolific angel (Square, Coinbase). Hospitality operations and gig-economy workforce parallels are a strong fit narrative.",
    ),
    ("AngelList Hospitality Syndicates", "Various Lead Investors", "$50K–$500K", None),
    ("Alumni Ventures", "John Sisty", "$250K–$1M", None),
    ("Golden Seeds", "Amy Wildstein", "$25K–$250K", None),
    ("Regional Angel Networks", "Varies by Region", "$25K–$150K", None),
    ("Launch Capital", "Rob Siegel", "$50K–$500K", None),
]


def run():
    updated = 0
    skipped = 0

    for firm_name, contact_name, check_size_range, warm_path in UPDATES:
        payload = {
            "contact_name": contact_name,
            "check_size_range": check_size_range,
        }
        if warm_path:
            payload["warm_path"] = warm_path

        result = supabase.table("investor_targets").update(payload).eq(
            "firm_name", firm_name
        ).execute()

        if result.data:
            updated += 1
            print(f"  ✓ {firm_name}: {contact_name}")
        else:
            skipped += 1
            print(f"  ✗ {firm_name}: not found in DB")

    print(f"\nDone. Updated: {updated} | Skipped: {skipped}")


if __name__ == "__main__":
    run()
