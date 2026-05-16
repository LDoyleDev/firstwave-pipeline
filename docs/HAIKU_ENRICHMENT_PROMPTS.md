# Haiku System Prompts for Lead Enrichment & Clarification

**Purpose**: Specifications for Haiku-based classification and enrichment in Phase 1-4 of lead generation
**Model**: Claude Haiku (cost-optimized for high-volume classification)
**Batch Size**: Max 5 leads per API call (per FIRSTWAVE_SYSTEM_CONTEXT.md § 8.2)

---

## PROMPT 1: Lead Clarification (Verify Hotel Operator)

**Task**: Determine if a business is a real, operational hotel with decision-maker contact potential.

**Input**:
```json
{
  "name": "string",
  "address": "string",
  "country": "string",
  "phone": "string",
  "website": "string (optional)"
}
```

**System Prompt**:
```
You are a hotel business verification specialist. Your job is to
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
- Business name includes "hotel", "inn", "resort", "lodge", "motel", "ryokan", "auberge", "posada"
- Address is in a major city, resort destination, or tourist area
- Phone number format matches country code expectations
- Website (if provided) shows guest-facing booking/information
- Company exists on public registries (can be verified via background knowledge)

Medium confidence signals:
- Name suggests accommodation but less explicit ("The Grand", "Riverside")
- Address is real but in suburban/non-tourist area
- Phone number valid but no web presence
- Business registration exists but cannot be independently verified

Reject (low confidence):
- OTA sites (Booking.com, Expedia, Hotels.com, Airbnb)
- Review/rating platforms (TripAdvisor, Google Hotels)
- Real estate/property platforms (Zillow, Rightmove)
- Non-operational properties (under construction, planned, closed)
- Travel agencies or tour operators (not hotel operators)
- Holding companies or real estate investment trusts without operational detail

Output confidence score guidance:
- 0.95+: Clear name (Hotel X, Inn Y), major city, phone + website confirmed
- 0.85-0.94: Clear name, valid address, phone but no web, or web no phone
- 0.75-0.84: Plausible name (The Grand), location valid, one contact method
- 0.65-0.74: Ambiguous name, weak address signals, but possibly real
- <0.65: Reject (output as "Unclear - needs manual review")
```

**Output**:
```json
{
  "classification": "Verified Hotel Operator" | "Not a Hotel" | "Unclear - needs manual review",
  "confidence": 0.85,
  "reasoning": "Hotel name clear, Munich city center address confirms major operation, phone format valid DE number"
}
```

**Handling**:
- If `confidence >= 0.85`: Mark as "Verified Hotel Operator" → proceed to enrichment
- If `0.75 <= confidence < 0.85`: Mark as "manual_review" → human approval queue
- If `confidence < 0.75`: Mark as "discarded" → skip enrichment

---

## PROMPT 2: Lead Enrichment (Extract Operator Type & Pain Points)

**Task**: Infer operator structure, team size, pain points, and best decision-maker contact role.

**Input**:
```json
{
  "name": "string",
  "address": "string",
  "country": "string",
  "phone": "string (optional)",
  "website": "string (optional)"
}
```

**System Prompt**:
```
You are a hospitality market analyst enriching hotel business lead data
for B2B sales outreach.

Given a hotel business name, address, country, and optional contact info,
infer the most likely:
1. Operator type (independent, boutique, franchise)
2. Estimated team size
3. Likely pain points in guest experience, revenue management, staffing
4. Most likely decision-maker role for sales outreach

Respond ONLY with valid JSON:
{
  "operator_type": "independent" | "boutique" | "franchise",
  "team_size_estimate": "<e.g. '10-25 staff' or '50-100 staff'>",
  "pain_points": ["<point1>", "<point2>", "<point3>"],
  "decision_maker_role": "Owner" | "General Manager" | "CMO" | "VP Revenue" | "Director of CX",
  "region": "<geographic/market segment>"
}

Inference rules:

OPERATOR TYPE:
- Independent: Single property, unique name (Hotel de Paris, The Old Mill), owner-operated signals
- Boutique: 5-50 properties, brand name (Rocco Forte, Aman, Angsana), multi-unit but curated
- Franchise: Part of larger network (Marriott, IHG, Best Western), standardized naming

TEAM SIZE ESTIMATES:
- <20 rooms: 5-15 staff
- 20-50 rooms: 10-30 staff
- 50-100 rooms: 20-60 staff
- 100-300 rooms: 50-150 staff
- 300+ rooms: 150-300+ staff

PAIN POINTS (Select top 3 from these):
1. "Unanswered inbound phone calls → lost bookings to OTA"
2. "High OTA commission burden (15-30% of bookings)"
3. "Staff retention and training costs (hospitality churn 40%+ annually)"
4. "Inconsistent guest experience across multi-unit properties"
5. "Lack of direct-to-guest marketing (over-reliant on OTAs)"
6. "Difficulty managing online reviews and reputation"
7. "Revenue management complexity (dynamic pricing, channel management)"
8. "Guest communication gaps (pre-arrival, during stay, post-stay)"
9. "Operational inefficiency (check-in/check-out, housekeeping coordination)"
10. "Adapting to post-pandemic consumer expectations (flexibility, safety)"

DECISION-MAKER BY OPERATOR TYPE:
- Independent: Owner (often hands-on), or General Manager (if scaled to 50+ rooms)
- Boutique: General Manager (property level) or VP Revenue (if multi-property)
- Franchise: General Manager (day-to-day, local pricing/marketing autonomy)

REGION INFERENCE (for outreach targeting):
- Major cities (Paris, London, Berlin): Multi-unit, brand-conscious, pain points #1-3, 5
- Suburban/secondary markets: Independent/boutique, pain points #3, 8-9
- Resort destinations (ski, beach, mountain): Seasonal staffing pain points, #2 (OTA reliance)
- Mid-size cities (100k-500k pop): Family-run boutique, all pain points relevant

CONFIDENCE CHECK:
If you are uncertain about operator type or decision-maker role, output your best inference
with reasoning in a separate "confidence_notes" field.
```

**Output**:
```json
{
  "operator_type": "boutique",
  "team_size_estimate": "30-50 staff",
  "pain_points": [
    "Unanswered inbound calls (hotel size, complex check-in process)",
    "OTA commission dependency (boutique market saturated with booking platforms)",
    "Staff retention (seasonal, hospitality churn)"
  ],
  "decision_maker_role": "General Manager",
  "region": "Central Europe, high-tourism city center (Munich)"
}
```

**Handling**:
- Save to leads table: `enrichment_data` JSONB field
- Extract `pain_points` array into separate `pain_signals` TEXT[] field
- Use `decision_maker_role` for personalization hooks in outreach

---

## BATCH PROCESSING CONSTRAINTS

### Rate Limiting
- **Max batch size**: 5 leads per API call
- **Min delay between batches**: 1-2 seconds (Haiku is fast)
- **Call cost**: ~€0.005 per call (Haiku is cheap)
- **Total cost for 2000 leads**: ~€20 (2 passes × 2000 leads / 5 batch size)

### Trading-Hours Gate
- **Allowed windows** (UTC):
  - All day Saturday
  - Sunday before 22:00 UTC
  - Daily 21:00–22:00 UTC (CME futures break)
- **Disallowed**: Mon-Fri 22:00 UTC to 21:00 UTC (vybe-trading active)
- **Override**: `FIRSTWAVE_LLM_ALWAYS_ALLOW=1` (testing only)

### Error Handling
- **JSON parse error**: Log, output "Unclear - needs manual review", confidence 0.0
- **API timeout**: Retry up to 3 times with exponential backoff (1s, 2s, 4s)
- **Rate limit**: Queue batch, retry after 60s
- **Network error**: Mark batch as deferred, alert operator via Telegram

---

## QUALITY ASSURANCE

### Spot-Check Protocol (Phase 1 Pilot)
- [ ] For every 50 leads enriched, manually verify 10 (20% sample)
- [ ] Verify classification matches human judgment (>80% accuracy target)
- [ ] Verify pain_points are realistic for operator type
- [ ] Verify decision_maker_role is appropriate for outreach

### Confidence Distribution (Log After Phase 1)
- [ ] % of leads at each confidence tier (0.95+, 0.85-0.94, 0.75-0.84, <0.75)
- [ ] Manual review queue size (0.75-0.84 tier)
- [ ] Discard rate (<0.75 tier)

### Token Cost Tracking
- [ ] Haiku calls per phase
- [ ] Average tokens per call (should be 200-400)
- [ ] Cost per lead (should be <€0.01)

---

## EXAMPLE: FULL ENRICHMENT CYCLE (1 Lead)

**Raw Input**:
```
Hotel Zur Post, Karlstrasse 12, 80333 Munich, Germany
+49 89 123 4567, www.hotelzurpost.de
```

**Clarification Output**:
```json
{
  "classification": "Verified Hotel Operator",
  "confidence": 0.92,
  "reasoning": "Clear hotel name, Munich city center major tourism market, German phone format valid, website confirms guest-facing operation"
}
```

**Enrichment Output**:
```json
{
  "operator_type": "boutique",
  "team_size_estimate": "20-35 staff",
  "pain_points": [
    "Unanswered calls during peak tourism season",
    "OTA commission management (competing with Booking.com, Expedia)",
    "Staff coordination across multiple departments (front, housekeeping, F&B)"
  ],
  "decision_maker_role": "General Manager",
  "region": "Bavaria, city-center boutique (high-tourism)"
}
```

**Supabase Storage**:
```json
{
  "name": "Hotel Zur Post",
  "phone": "+49 89 123 4567",
  "location": "Karlstrasse 12, 80333 Munich, Germany",
  "title": "General Manager",
  "status": "verified_hotel",
  "lead_score": 92,
  "enrichment_data": {
    "classification": "Verified Hotel Operator",
    "confidence": 0.92,
    "enrichment": {...}
  },
  "pain_signals": ["Unanswered calls", "OTA commissions", "Staff coordination"]
}
```

---

## ITERATION & REFINEMENT

After Phase 1 Pilot (50 leads + spot-check), update prompts if:
- Classification accuracy <80%
- Pain points are generic/non-actionable (>20% of outputs)
- Decision-maker role inference misses the mark (>15% of outputs)

Expected refinements:
- Add country-specific pain point patterns (e.g., GDPR compliance for EU)
- Add size-based decision-maker mapping (e.g., <20 rooms → Owner, >100 rooms → GM)
- Add seasonal/region-specific hints (resort vs. city, mountain vs. coastal)

