# Hotel Business Lead Generation — Data Sources Reference

**Last updated**: 2026-05-15
**Purpose**: Sourcing 1000-2000 verified hotel businesses for FirstWave AI client acquisition pipeline

---

## PRIMARY SOURCES

### 1. European Company Registers (Free, High Fidelity)

**Coverage**: 8 EU countries
**Data Quality**: Legal registration records, 95%+ verified
**Timeline**: Query results within 24 hours

#### Germany
- **Bundesanzeiger** (www.bundesanzeiger.de)
  - Federal official gazette, all GmbH/AG registrations
  - Search: "Hotel" OR "Inn" OR "Resort" in business type
  - Cost: Free
  - Yield estimate: 15,000+ hotel businesses

- **Chamber of Commerce (IHK)** 
  - Regional registries: Berlin (IHK Berlin), Munich (IHK München), Hamburg (IHK Hamburg)
  - Contact: tourism boards for bulk exports
  - Cost: €50-200 per region
  - Yield estimate: 5,000+ hotel operators

#### France
- **SIRENE Database** (www.sirene.fr)
  - Official business registry, INSEE-maintained
  - Search API: SirenAPI (free tier: 100 req/day)
  - Code APE 5510Z (hotels) returns verified records
  - Cost: Free
  - Yield estimate: 20,000+ hotels

- **INSEE Open Data** (data.gouv.fr)
  - Bulk download: all hospitality businesses by region
  - Format: CSV + GeoJSON
  - Cost: Free
  - Yield estimate: 18,000+ hotels

#### Spain
- **BORME** (Boletín Oficial del Registro Mercantil)
  - www.borme.es — official business registry
  - Search by NACE code 5510 (accommodation)
  - Cost: Free search, €20/download
  - Yield estimate: 12,000+ hotels

- **NRSC** (National Registry of Sole Traders)
  - Spanish autonomous businesses
  - Web access + bulk export available
  - Cost: Free
  - Yield estimate: 5,000+ small hotel operators

#### Italy
- **Registro Imprese** (www.cameredicommercio.it)
  - Chamber of Commerce unified registry
  - Regional access: Camera di Commercio di Milano, Roma, Napoli, etc.
  - Cost: Free search, €10-50 per bulk export
  - Yield estimate: 8,000+ hotels

#### UK
- **Companies House** (www.beta.companieshouse.gov.uk)
  - API + bulk download available
  - Search: NAICS 721110 (hotels) or keyword "hotel"
  - Cost: Free API, £50/mo for bulk download
  - Yield estimate: 10,000+ hotels

#### Benelux
- **KVK** (Netherlands Kamer van Koophandel)
  - www.kvk.nl — API available
  - Search: SIC 5510 (accommodation)
  - Cost: Free API (100 req/mo) or €99/yr
  - Yield estimate: 3,500+ hotels

- **KBE** (Belgium Crossroads Bank)
  - Belgian business registry
  - Cost: Free via portal, €500/yr API
  - Yield estimate: 1,200+ hotels

- **LBR** (Luxembourg)
  - Grand Duchy registry
  - Cost: Free
  - Yield estimate: 200+ hotels

**Cost Summary**: €500-1500 for regional bulk exports (one-time), Free for search-based approach

---

### 2. US Secretary of State Business Registries (Free-Freemium)

**Coverage**: All 50 states
**Data Quality**: Legal registration records, 90%+ complete
**Timeline**: Query results in real-time

#### Key States (Top 10 Metro Areas)
- **Texas**: Secretary of State database (free search, bulk download €200/yr)
  - Yield: 5,000+ hotels
  
- **California**: EDGAR database (free, searchable)
  - Yield: 4,000+ hotels
  
- **Florida**: Department of State (free search)
  - Yield: 3,000+ hotels
  
- **New York**: Division of Corporations (free search)
  - Yield: 2,500+ hotels
  
- **Illinois**: Secretary of State (free search)
  - Yield: 1,500+ hotels

- **Massachusetts**: Secretary of State (free API)
  - Yield: 1,000+ hotels

- **Colorado**: Secretary of State (free)
  - Yield: 800+ hotels

- **Washington**: Secretary of State (free)
  - Yield: 1,000+ hotels

- **Arizona**: Corporation Commission (free)
  - Yield: 1,200+ hotels

- **Pennsylvania**: Department of State (free)
  - Yield: 900+ hotels

#### All-States Solution
- **OpenCorporates API** (www.opencorporates.com)
  - Aggregated business registry data for all 50 states
  - Free tier: 10 req/day
  - Pro: €50/mo (unlimited)
  - Yield estimate: 20,000+ US hotels (deduplicated)

**Cost Summary**: Free (state registries) or €50/mo (OpenCorporates pro for faster queries)

---

### 3. Hospitality Industry Directories (Freemium-Paid)

**Coverage**: Decision-makers, industry signals
**Data Quality**: Mid-high (self-reported, intent-forward)
**Timeline**: 1-7 days for bulk access

#### STR (Smith Travel Research)
- www.str.com
- Industry data on US + international hotels
- Free sample lists (50-100 properties)
- Paid: €500/mo for segment-based lists
- **API**: Yes, limited free tier
- Yield estimate: 500-1000 high-signal leads (resort chains, multi-property groups)

#### HotelTechReport
- www.hoteltechreport.com
- CMS software buyer registry (high purchase intent)
- Free directory
- Paid: €200/mo for filtered lists (hotel size, budget status)
- Yield estimate: 200-300 tech-forward hotels

#### HospitalityNet
- www.hospitalitynet.org
- Community profiles + company pages
- Free search
- Cost: Free
- Yield estimate: 100-150 manually verified leads

#### Lodging Magazine
- www.lodgingmagazine.com
- Industry news + company profiles
- Free search (limited)
- Paid: €99/yr for industry database
- Yield estimate: 50-100 news-sourced leads

#### American Hotel & Lodging Association (AHLA)
- www.ahlonline.org
- Member directory (public)
- Cost: Free
- Yield estimate: 3,000+ members (mix of operators + suppliers)

**Cost Summary**: €200-800/mo if pursuing all premium feeds, €0-300 for freemium approach

---

### 4. Booking Platform APIs (Free)

**Coverage**: Active hotel operators
**Data Quality**: High (real bookings confirm operation)
**Timeline**: Real-time

#### Booking.com Affiliate API
- Partner Network → Property search
- Returns: Property name, manager contact, review data
- Cost: Free (affiliate commission structure)
- Rate limit: 100 req/min
- Yield estimate: 1,000-1,500 properties (EU/US sample)

#### Expedia Partner Network
- Developer API → Available properties
- Returns: Property ID, manager info, contact
- Cost: Free (affiliate structure)
- Rate limit: 50 req/sec
- Yield estimate: 1,500-2,000 properties

#### Airbnb API
- Public API (limited; full data requires partnership)
- Returns: Property type, host name, location
- Cost: Free public, paid for property manager details
- Yield estimate: 500-800 boutique hotels

**Cost Summary**: Free (affiliate structure)

---

### 5. LinkedIn + PhantomBuster (Freemium)

**Coverage**: Decision-makers (GMs, CMOs, Revenue Directors)
**Data Quality**: High (verified profiles)
**Timeline**: 1-3 days per campaign

#### LinkedIn Search
- Advanced search: "Hotel General Manager" + country filter
- Connection reverse-lookup: company discovery
- Cost: €39/mo (LinkedIn Sales Navigator)
- Yield estimate: 200-300 decision-makers per country

#### PhantomBuster LinkedIn Scraper
- www.phantombuster.com
- Campaign: Scrape hotel owner profiles
- Free tier: 100 profiles/mo
- Paid: €50/mo (1000 profiles/mo)
- Yield estimate: 300-500 decision-makers (with reverse company lookup)

**Cost Summary**: €50/mo (PhantomBuster already budgeted per CLAUDE.md)

---

### 6. Chamber of Commerce & Tourism Boards (Free)

**Coverage**: Official, tourist-facing operator directories
**Data Quality**: Mid (publicly listed, sometimes outdated)
**Timeline**: Manual scrape: 3-5 days per country

#### EU Tourism Boards
- **VisitBritain**: www.visitbritain.com/en/plan-your-trip (hotel listings)
  - Yield: 2,000+ UK hotels

- **Atout France**: www.france-tourisme.net
  - Regional tourism partnerships
  - Yield: 5,000+ French hotels

- **Spain Tourism**: www.spain.info
  - Regional listings + chamber partnerships
  - Yield: 3,000+ Spanish hotels

- **Italian Hoteliers Association**: www.federalberghi.it
  - Member directory
  - Yield: 2,500+ Italian hotels

- **NBTC** (Dutch Tourism): www.holland.com
  - Hotel directory by region
  - Yield: 1,000+ Dutch hotels

#### US State Tourism Boards
- Visit each state's official tourism site (e.g., VisitCalifornia.com, VisitNewYork.com)
- Hotel directories typically public-facing
- Yield estimate: 3,000-5,000 state-listed hotels (varies by state)

**Cost Summary**: Free (public web scrape)

---

## SECONDARY SOURCES (Phase 4)

### Franchise Directories
- **Marriott**: www.marriott.com/partners (franchise partner list)
- **IHG**: www.ihg.com/en-gb/hotel-owners (property owner contact form)
- **Hilton**: www.hiltonhospitality.com/franchising
- **Wyndham**: www.wyndhamhotels.com/franchising
- **Choice Hotels**: www.choicehotels.com/franchising

Yield estimate: 500-700 franchise operators (US + EU mixed)

### Real Estate Platforms
- **CBRE Hotels**: www.cbrehotels.com (hotel sales/listings)
- **Colliers International**: Hotels vertical
- Cost: Free listings (contact info for brokers, not operators)
- Yield: 200-300 high-value properties (for follow-up with brokers)

---

## DEDUPLICATION STRATEGY

### Primary Key (Hard Dedup)
```
SHA1(normalize(name) + normalize(address) + city)
```

Where `normalize()` removes:
- Accents (Hotel Münchën → Hotel Munchen)
- Articles (The Ritz → Ritz)
- Abbreviations (St. → Saint)
- Multiple spaces

### Soft Dedup (Conflict Resolution)
When multiple records match the same SHA1:
1. Keep: Most recent registration date
2. If tied: Most complete contact info (phone > email > web)
3. Flag: Multi-unit properties at same address (chain/franchise signals)

---

## VERIFICATION GATES (Applied to All Sources)

| Gate | Rule | Reject If |
|------|------|-----------|
| Business Type | Accommodation (SIC 5510 / NACE 5510Z) | OTA, real estate, review site |
| Registration Status | Active | Dissolved, liquidating, planned |
| Contact Data | Phone OR email OR address | None provided |
| Location | City-level address identifiable | "Europe" or vague |
| Decision-Maker | Title identifiable (Owner, GM, CMO) OR inferable | CEO of holding company only |
| Size (soft) | 1-500 properties preferred | Enterprise (>1000 properties) held for review |

---

## PHASE 1 EXECUTION PLAN

### Week 1 (2026-05-15 to 2026-05-22)
- [ ] Build 50-lead sample from each source (8-10 per source)
- [ ] Run Haiku pilot on clarification + enrichment
- [ ] Document confidence distribution and token costs
- [ ] Validate system prompts for Phase 3

### Phase 2 (2026-05-22 to 2026-06-05)
- [ ] Execute bulk searches: EU registers (batches 1-3)
- [ ] US Secretary of State queries (batches 4-5)
- [ ] Dedup + conflict resolution
- [ ] Output: 1200-1400 "Candidate" records

### Phase 3 (2026-06-05 to 2026-06-26)
- [ ] Clarification pass (Haiku): 1200+ leads in batches of 5
- [ ] Enrichment pass (Haiku): ~80% verify as hotel operators
- [ ] Output: ~1000-1100 verified operators

### Phase 4 (2026-06-26 to 2026-07-10)
- [ ] Secondary sources: +500-600 new leads
- [ ] Manual review of "Unclear" queue
- [ ] Final 2000-lead compilation

---

## COST PROJECTIONS

| Component | Unit Cost | Qty | Total |
|-----------|-----------|-----|-------|
| EU bulk exports (one-time) | €50-300 | 5 countries | €500 |
| US state APIs (annual) | Free | — | €0 |
| Haiku calls (2000 leads × 2) | €0.005 per call | 4000 | €20 |
| PhantomBuster (annual) | €50/mo | 12 | €600 |
| LinkedIn Sales Nav (annual) | €39/mo | 12 | €468 |
| STR sample lists | €100 | 1 | €100 |
| **TOTAL (Annual)** | — | — | **€1,688** |

*Note: Ollama + Claude fallback already budgeted in cross-project infra.*

