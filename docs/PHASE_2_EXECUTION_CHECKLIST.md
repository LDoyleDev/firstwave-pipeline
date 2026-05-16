# Phase 2 Execution Checklist — Bulk Search & Initial Screening

**Phase**: 2 of 4 (Lead Generation)
**Timeline**: 2026-05-22 to 2026-06-05 (2 weeks)
**Objective**: Acquire 1200-1400 candidate leads from EU and US registries
**Owner**: Claude Code (with Liam's go-ahead)

---

## PRE-EXECUTION SIGN-OFF

- [ ] **Phase 1 pilot completed** — Spot-check 10 leads manually, confidence distribution analyzed
- [ ] **Liam approval** — Confirm geography (DACH, UK, Benelux, US metros) matches ICP
- [ ] **Supabase schema ready** — Test write 5 leads to `leads` table
- [ ] **Budget approved** — ~€50 EU bulk exports + €0 US + €0 free sources
- [ ] **Timeline realistic** — 2 weeks for bulk search + dedup + initial screening

**Sign-off date**: __________  
**Approver**: __________

---

## WEEK 1: EU BULK SEARCH (Batches 001-150)

### Batch 1-50: Germany + France (300 leads)

#### Germany
- [ ] **Step 1a**: Query Bundesanzeiger.de
  - Tool: Web scraper (or manual downloads for initial sample)
  - Search: `business_type ~ "Hotel" OR "Inn" OR "Resort" OR "Gasthof"`
  - Filters: `status = "Active"` only
  - Fields to extract: Name, address, postal code, phone, registration date
  - Estimated yield: 5,000-8,000 results (apply heuristics to narrow to top 500)
  
- [ ] **Step 1b**: Filter by major cities
  - Cities: Berlin, Munich, Frankfurt, Cologne, Hamburg, Düsseldorf
  - Size filter: ≥1 employee (excludes hobby operations)
  - Output: 200 leads → `data/phase2_batch_01_germany.json`

- [ ] **Step 1c**: German Chamber of Commerce (IHK)
  - Query: IHK Berlin, IHK München, IHK Hamburg (contact via email for bulk list)
  - Estimated yield: 500-1000 per region
  - Action: Email contact, request hotel operator list (mention business purpose)
  - Timeline: 3-5 days for response
  - Output: `data/phase2_germany_chamber.json` (when received)

#### France
- [ ] **Step 2a**: Query SIRENE database
  - API: inseedatasets.fr or insee.fr/en/accueil
  - Code APE: 5510Z (Hotels)
  - Filter: `sirene_status = "Active"`
  - Fields: SIREN, name, address, phone, manager name
  - Estimated yield: 18,000+ results → apply size + location filters

- [ ] **Step 2b**: Filter by major cities + region
  - Cities: Paris (IDF), Lyon, Marseille, Toulouse, Nice
  - Output: 100 leads → `data/phase2_batch_01_france.json`

- [ ] **Step 2c**: INSEE Open Data (bulk download)
  - Use data.gouv.fr CSV export
  - Filter: APE=5510Z, status=Active
  - Dedup with Step 2a
  - Output: 50 additional leads → `data/phase2_france_open_data.json`

**Completion criteria**: 300 leads acquired, saved to JSON, ready for dedup

---

### Batch 51-100: UK + Spain (300 leads)

#### UK
- [ ] **Step 3a**: Companies House API
  - Auth: Free API key (register at beta.companieshouse.gov.uk)
  - Search: `keywords ~ "hotel" AND status="Active"`
  - Filters: SIC code 5510, 5511, 5512 (accommodation categories)
  - Estimated yield: 10,000+ results → filter top 200 by incorporation date (recent = likely active)
  - Output: `data/phase2_batch_02_uk.json`

- [ ] **Step 3b**: VisitBritain hotel directory
  - Query: www.visitbritain.com/accommodation (if available as bulk export)
  - Fallback: Manual scrape of top regions (London, Manchester, Edinburgh, Bath)
  - Estimated yield: 100-200 leads
  - Output: `data/phase2_uk_tourism.json`

#### Spain
- [ ] **Step 4a**: BORME (Registro Mercantil)
  - Search: NACE code 5510 (accommodation)
  - Filter: Active registrations from last 5 years
  - Estimated yield: 8,000+ results → apply city filters
  - Output: 150 leads → `data/phase2_batch_02_spain_borme.json`

- [ ] **Step 4b**: Spanish Chamber of Commerce
  - Regional chambers: Madrid, Barcelona, Valencia, Seville
  - Request: Hotel operator member lists
  - Timeline: 5-7 days
  - Output: `data/phase2_spain_chamber.json` (when received)

**Completion criteria**: 300 leads acquired, dedup applied, ready for Haiku clarification

---

### Batch 101-150: Italy + Benelux (300 leads)

#### Italy
- [ ] **Step 5a**: Registro Imprese (Chamber of Commerce)
  - Regional registries: Milan (Lombardy), Rome (Lazio), Florence (Tuscany), Venice (Veneto)
  - Query: ATECO 55.10.1 (Hotels)
  - Estimated yield: 5,000+ results → city + size filters
  - Output: 150 leads → `data/phase2_batch_03_italy.json`

#### Benelux
- [ ] **Step 6a**: KVK (Netherlands)
  - API: kvk.nl (free tier, searchable)
  - Search: SIC 5510 + keywords="hotel"
  - Filter: Amsterdam, Rotterdam, The Hague (top markets)
  - Estimated yield: 1,500+ results → top 80 leads
  - Output: `data/phase2_batch_03_netherlands.json`

- [ ] **Step 6b**: KBE (Belgium) + LBR (Luxembourg)
  - Belgium: kbe.ov.be, query hotel operators
  - Luxembourg: Simple (small market), 200+ total hotels
  - Estimated yield: 50-100 leads combined
  - Output: `data/phase2_batch_03_benelux.json`

**Completion criteria**: 300 leads acquired, all deduplicated against batches 1-50

---

## DEDUPLICATION (Batches 001-150)

### Dedup Step 1: Data Normalization
```bash
for file in data/phase2_batch_*.json; do
  python3 scripts/normalize_leads.py --input "$file" --output "${file%.json}_normalized.json"
done
```

**Normalization rules**:
- Convert to lowercase
- Remove accents (Müller → Muller)
- Remove articles (The, Le, La, Il, Het)
- Remove common words (Hotel, Inn, Resort, etc. from address but keep in name)
- Strip punctuation and extra spaces
- Standardize postal codes

### Dedup Step 2: SHA1 Hash
```python
import hashlib
for lead in leads:
  key = f"{lead['name_normalized']}|{lead['address_normalized']}|{lead['city']}"
  lead['dedup_hash'] = hashlib.sha1(key.encode()).hexdigest()
```

### Dedup Step 3: Conflict Resolution
```
For each duplicate group (same hash):
  1. Keep: Most recent registration_date
  2. If tied: Most complete contact (phone > email > web)
  3. Flag: Multi-unit properties at same address (chain signals)
```

**Output**: `data/phase2_deduped_batches_001_150.json`

**Expected dedup rate**: 5-8% (removes duplicates from overlapping sources)

---

## WEEK 2: US BULK SEARCH (Batches 151-290)

### Batch 151-200: US Top 5 Metros (400 leads)

#### New York
- [ ] **Step 7a**: NY Division of Corporations
  - Search: business type = "Hotel" or "Lodging"
  - Filter: Active, last annual report < 2 years
  - Metro area: NYC + boroughs
  - Estimated yield: 2,000+ results → top 100 by size
  - Output: `data/phase2_batch_04_ny.json`

#### California
- [ ] **Step 7b**: CA Secretary of State EDGAR
  - Search: SIC 7011 (Hotels)
  - Metros: Los Angeles, San Francisco, San Diego
  - Estimated yield: 2,000+ results → top 100 by size
  - Output: `data/phase2_batch_04_ca.json`

#### Texas
- [ ] **Step 7c**: TX Secretary of State + OpenCorporates
  - Query: `state=TX AND (keywords~"hotel" OR sic=7011)`
  - Metros: Dallas, Houston, Austin
  - Estimated yield: 1,500+ → top 100
  - Output: `data/phase2_batch_04_tx.json`

#### Florida
- [ ] **Step 7d**: FL Department of State
  - Search: Hotels + Resorts
  - Metros: Miami, Tampa, Orlando
  - Estimated yield: 1,200+ → top 50
  - Output: `data/phase2_batch_04_fl.json`

#### Massachusetts
- [ ] **Step 7e**: MA Secretary of State
  - Metro: Boston
  - Estimated yield: 500+ → top 50
  - Output: `data/phase2_batch_04_ma.json`

**Completion criteria**: 400 leads from top 5 metros, deduplicated against EU leads

### Batch 201-250: US Secondary Metros (300 leads)

#### Multi-State Query
- [ ] **Step 8a**: OpenCorporates API (pro tier if budget allows)
  - Query: All 50 states, SIC 7011 (Hotels)
  - Filter: Active status, contact info present
  - Focus: Chicago, Denver, Seattle, Phoenix, Portland
  - Estimated yield: 2,000+ → filter to 300 leads
  - Cost: €50/mo (1-month subscription for bulk query)
  - Output: `data/phase2_batch_05_us_secondary.json`

**Completion criteria**: 300 leads, deduplicated against previous

### Batch 251-290: Booking Platform APIs (200 leads)

#### Booking.com Affiliate API
- [ ] **Step 9a**: Query via Partner API
  - Search: Hotel properties in US + EU cities
  - Extract: Property name, manager email, property address
  - Estimated yield: 500-700 properties → filter to 150 (avoid duplicates with registries)
  - Output: `data/phase2_batch_06_booking.json`

#### Expedia Partner Network
- [ ] **Step 9b**: Expedia API query
  - Property search: Hotel properties (US + major EU cities)
  - Extract: Name, manager contact, address
  - Estimated yield: 600-800 → filter to 50 (dedup against Booking)
  - Output: `data/phase2_batch_06_expedia.json`

**Completion criteria**: 200 leads from booking platforms, unique from registry leads

---

## INITIAL SCREENING (All Batches)

### Screening Step 1: Validation Filters (Non-LLM)
```
For each lead:
  1. name: NOT NULL AND length > 2
  2. address: Contains city OR contains postal code
  3. country: IN (approved countries)
  4. phone OR website: At least one present
  5. NOT matches patterns: (OTA, review site, real estate, tour operator)
```

**Output**: Leads that pass validation → `data/phase2_candidates_screening.json`
**Expected filter rate**: 90-95% pass (5-10% invalid/obviously not hotels)

### Screening Step 2: Keyword Exclusions
```
Reject if name or address contains:
  - "booking.com", "expedia", "hotels.com", "airbnb", "vrbo"
  - "tripadvisor", "google hotels", "kayak"
  - "real estate", "property management", "real estate investment"
  - "tour operator", "travel agency", "cruise"
  - Status words: "closed", "under construction", "planned"
```

**Output**: Clean candidate list → `data/phase2_candidates_final.json`
**Expected output**: 1200-1400 leads, ready for Haiku clarification

---

## SUPABASE IMPORT (Optional Checkpoint)

- [ ] Create table: `leads_candidates_phase2` (mirror of `leads`, with status="screening")
- [ ] Batch insert: `data/phase2_candidates_final.json` (in chunks of 100)
- [ ] Verify: SELECT COUNT(*) FROM leads_candidates_phase2 (should be 1200-1400)
- [ ] Backup: Export to CSV for reference

---

## PHASE 2 COMPLETION CHECKLIST

### Data Quality
- [ ] Total leads acquired: 1400+ ✓
- [ ] Dedup applied: Hash collisions resolved ✓
- [ ] Validation passed: 90%+ compliance ✓
- [ ] Country distribution: EU 60%, US 40% ✓
- [ ] Contact data: 85%+ have phone OR email ✓

### Documentation
- [ ] Source log: Which batches came from which sources ✓
- [ ] Dedup report: % removed per batch ✓
- [ ] Filtering report: % rejected per validation gate ✓
- [ ] Cost summary: Total spent on registries/APIs ✓

### Data Files
- [ ] `data/phase2_candidates_final.json` (1200-1400 leads) ✓
- [ ] `data/phase2_dedup_report.csv` (conflicts resolved) ✓
- [ ] `logs/phase2_screening_log.txt` (all filtering decisions) ✓

### Ready for Phase 3?
- [ ] Liam approval: Proceed to Haiku clarification on full dataset
- [ ] Cost on track: <€100 total spend
- [ ] Timeline on track: Completed by 2026-06-05
- [ ] No blockers: Registries accessible, dedup working, data quality good

---

## RISK MITIGATIONS

| Risk | Contingency |
|------|-------------|
| Registry API down | Use open data exports (CSV) or manual download |
| Response from chambers slow | Proceed without chamber data, add later |
| Dedup collision rate >10% | Expand hash key to include phone number |
| Phone number parsing fails | Mark as "phone_format_invalid", still include lead |
| Supabase quota exceeded | Chunk inserts into 100-lead batches |

---

## COST TRACKING

| Item | Cost | Qty | Total |
|------|------|-----|-------|
| EU registry bulk exports | €50-200 | 1 | €50-200 |
| US state registries | €0 | — | €0 |
| OpenCorporates pro (1 month) | €50 | 1 | €50 |
| Booking/Expedia APIs | €0 | — | €0 |
| **Phase 2 Total** | — | — | **€100-250** |

**Remaining budget**: €750K - €250 = €749,750 (still healthy for Phase 3-4 + full pipeline)

