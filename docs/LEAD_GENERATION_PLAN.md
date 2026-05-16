# FirstWave AI — Hotel Business Lead Generation Plan

**Target**: 2000 verified, real hotel operators across EU and US
**Execution Window**: Weeks of 2026-05-15 through 2026-06-11
**Lead Model**: Independent, boutique, and franchise hotel operators with 5+ properties

---

## PHASE 1: PLANNING & DATA SOURCE VALIDATION

### Status: IN PROGRESS
Started: 2026-05-15
Timeline: 1 week

### Data Sources Identified

#### Primary Sources (verified, hotel-specific)
1. **European Companies Register (EU)**
   - Czech Republic: ARES (ares.gov.cz) — free, XML/JSON export
   - Poland: KRS (rejestracjehandlowy.pl) — free search
   - Germany: Bundesanzeiger + Handelsregister (dnb.de for D&B enrichment)
   - France: SIRENE/SIREN database (companies-house equivalent)
   - Spain: BORME + NRSC registries
   - Italy: Registro Imprese (cameredicommercio.it)
   - UK: Companies House (companieshouse.gov.uk) — free API
   - Benelux: KVK (Netherlands), KBE (Belgium), LBR (Luxembourg)

   **Cost**: Free or minimal (~£50/mo for UK Companies House bulk)
   **Quality**: Authoritative, legal registration data
   **Lead yield estimate**: 400-500 hotel businesses across 8 countries

2. **US Secretary of State Business Databases**
   - Texas: Secretary of State online search (bulk data available)
   - California: CA Secretary of State EDGAR
   - Florida, New York, Illinois: Similar free registries
   - All 50 states via OpenCorporates API (free tier)

   **Cost**: Free (state registries), $0-100/mo (OpenCorporates pro)
   **Quality**: Legal registration, direct contacts sometimes included
   **Lead yield estimate**: 300-400 hotels (focus: top 10 metro areas)

3. **Hospitality Industry Directories**
   - STR (Smith Travel Research) — requires subscription but has free sample lists
   - Lodging Magazine's industry database
   - HotelTechReport (vendor ecosystem = who's buying CX software)
   - HospitalityNet community (business profiles with contact info)
   - American Hotel & Lodging Association directory

   **Cost**: Freemium or $300-1000/mo
   **Quality**: High intent (actively talking about tech/CX)
   **Lead yield estimate**: 200-300 high-signal leads

4. **Booking.com / Expedia Partner Data**
   - Free APIs provide property listings for franchises
   - Booking Affiliate API (free tier) returns property manager names
   - Expedia Partner Network (public directory by property)
   - Data accuracy: property owner/manager contact info is 60-70% complete

   **Cost**: Free
   **Quality**: Active operators (live bookings prove operation)
   **Lead yield estimate**: 500-700 leads (high dedup risk)

5. **LinkedIn + PhantomBuster**
   - Search: "Hotel General Manager" + "Marketing Director" + "VP Revenue" in each country
   - PhantomBuster free tier: 100 leads/mo, $50/mo pro
   - Campaign: Collect 200-300 decision-makers, reverse-lookup company

   **Cost**: $50/mo (already budgeted as per CLAUDE.md)
   **Quality**: Real people (profile verification), direct contact
   **Lead yield estimate**: 200-300 high-intent leads

6. **Chamber of Commerce & Tourism Board Listings**
   - Spanish Chamber of Commerce (Cámara de Comercio) — 30,000+ registered hotels
   - German IHK (Industrie- und Handelskammern) — hotel directories
   - French CCIP (Chambre de Commerce et d'Industrie Paris-IDF)
   - Tourism boards: VisitBritain, TourismBoard.it, etc. — often publish hotel operator directories

   **Cost**: Free (public listings)
   **Quality**: Mid-high (officially registered)
   **Lead yield estimate**: 200-300 leads

### Target Countries Confirmed

**Primary (Tier 1 — Liam's network): 6 countries**
- 🇩🇪 Germany (Berlin, Munich, Frankfurt, Cologne)
- 🇫🇷 France (Paris, Lyon, Marseille)
- 🇬🇧 UK (London, Manchester, Birmingham)
- 🇪🇸 Spain (Madrid, Barcelona, Valencia)
- 🇮🇹 Italy (Rome, Milan, Florence)
- 🇳🇱 Netherlands (Amsterdam, Rotterdam)

**Secondary (Tier 2 — high volume, English-speaking): 4 countries**
- 🇺🇸 USA (top 15 metros: NYC, LA, Chicago, Dallas, Houston, Phoenix, Philadelphia, San Antonio, San Diego, Austin, Boston, Seattle, Miami, Denver, Portland)
- 🇫🇮 Finland (Helsinki, Tampere)
- 🇸🇪 Sweden (Stockholm, Gothenburg, Malmö)
- 🇮🇸 Iceland (Reykjavik)

### Verification Gates (Non-Negotiable)

Every lead must pass these filters before entering Supabase:

1. **Company Registration**
   - ✅ Business registration number present (or confirmed via web lookup)
   - ✅ Business type = hospitality/accommodation (not OTA, not real estate)
   - ✅ Active status (not dissolved, under-construction, or planned)

2. **Contact Information**
   - ✅ Phone number or email present
   - ✅ Address verified (postal code + street confirms operation location)
   - ✅ Decision-maker title identifiable (Owner, GM, CMO, VP Revenue, Hospitality Manager)

3. **Hotel Operator Classification**
   - ✅ Independent (full autonomy on pricing, marketing)
   - ✅ Boutique (5-50 properties, brand control important)
   - ✅ Franchise (adheres to brand standards but local autonomy on non-core)
   - ❌ Reject: OTA-only listings, real estate investment trusts, non-operational properties

4. **Business Size (Soft Gate)**
   - ✅ Preferred: 5-500 properties
   - ✅ Acceptable: 1-5 properties (if ICP-aligned decision-maker visible)
   - ⚠️ Review queue: >500 properties (may be enterprise, may not answer cold email)

### Haiku Pilot: 50-Lead Sample Validation

**Objective**: Test clarification + enrichment prompts before scaling to 2000.

**Setup**:
1. Source 50 hotel leads from mixed sources (10 per country pair: DE/FR/UK/ES/IT)
2. Manually verify all 50 are real, active hotels
3. Run Haiku clarification + enrichment on small batches (5 leads per batch, 10 batches total)
4. Manually spot-check 10 outputs (20% sample)
5. Measure:
   - Clarification accuracy: % of "Verified Hotel Operator" that human confirms as accurate
   - Enrichment quality: Are extracted pain points + operator type realistic?
   - Haiku confidence scores: Do high-confidence (≥0.85) outputs match human judgment?
   - Token cost: Establish baseline for 2000-lead run

**Output**:
- 50 "Verified Hotel Operator" records in Supabase with enrichment data
- Confidence distribution chart (will inform filtering thresholds)
- Validated system prompt for Phase 3 (clarification pass on full 2000)

**Timeline**: Complete by 2026-05-22 (1 week)

---

## PHASE 2: BULK SEARCH & INITIAL SCREENING

### Status: PENDING
**Planned Start**: 2026-05-22
**Timeline**: 2 weeks

### Batch Strategy

| Batch | Countries | Sources | Target Count | Status |
|-------|-----------|---------|--------------|--------|
| 1 | DE + FR | Company registers + Chamber of Commerce | 300 | — |
| 2 | UK + ES | Companies House + BORME | 300 | — |
| 3 | IT + NL | Registro Imprese + KVK | 300 | — |
| 4 | US Top 10 metros | Secretary of State + Booking API | 400 | — |
| 5 | US Secondary + Overflow | Expedia API + HotelsHR | 400 | — |

**Dedup strategy**: SQLite SHA1(name + address + city). Keep: most recent registration, most complete contact.

**Output**: 1200-1400 "Candidate" records with status="screening"

---

## PHASE 3: CLARIFICATION & ENRICHMENT

### Status: PENDING
**Planned Start**: 2026-06-05
**Timeline**: 3 weeks

### Haiku-Driven Workflow

**Clarification Pass**:
- Input: {business_name, address, phone, website_snippet, registration_data}
- Classifier: "Is this a real hotel operator?"
- Output: classification + confidence_score (0.0-1.0)
- Gates: Keep ≥0.85, review 0.75-0.85, discard <0.75

**Enrichment Pass**:
- Input: verified {business_name, address, phone}
- Generator: Extract operator type, team size, pain points
- Classifier: Identify decision-maker role
- Batch constraint: Max 5 leads per API call (FIRSTWAVE_SYSTEM_CONTEXT.md rule 2)

**Trading-Hours Compliance**: All Haiku calls scheduled weekends + Mon-Fri 21:00-22:00 UTC only.

---

## PHASE 4: SCALING TO 2000

### Status: PENDING
**Planned Start**: 2026-06-26
**Timeline**: 2 weeks

**Secondary sources + manual engagement**:
- Franchise directories: +500-600 new leads
- Tourism boards: +200-300 new leads
- LinkedIn manual research: +100-150 converted from "Unclear" queue
- Combined verified total: 2000+

---

## Success Criteria

- [ ] 2000+ lead records in Supabase (verified_hotel OR manual_review status)
- [ ] ≥1500 with confidence_score ≥0.75
- [ ] ≥1200 with confidence_score ≥0.85 (ready for outreach)
- [ ] All with: name, address, phone/email, decision_maker_name, decision_maker_role
- [ ] 0 GDPR gaps for EU leads
- [ ] Dedup rate <5%
- [ ] Random verification: ≥95% of spot-checked leads are real + operational

---

## Known Constraints & Risk Mitigations

| Constraint | Impact | Mitigation |
|---|---|---|
| Haiku rate limit (~100 req/min) | Batch processing time | Spread batches across weekends + evenings; queue if needed |
| GDPR compliance (EU data) | 6/10 leads are EU-based | Store "privacy_basis" field; no email until GDPR basis confirmed |
| Trading-hours gates | LLM calls only off-peak | Schedule Haiku runs weekends + 21:00-22:00 UTC only |
| Data dedup & conflict resolution | Data quality risk | SHA1 hash on (name + address); keep most recent + complete |
| Decision-maker identification | Cold outreach effectiveness | Haiku enrichment + LinkedIn manual lookup for "Unclear" |
| Cost tracking | Budget overrun | Haiku cost ~$15 for 4000 calls; monitor spend per batch |

