# Batch Processing Guide — Lead Enrichment Phases

**Purpose**: Standard operating procedures for running 5-lead batches through clarification and enrichment pipeline
**Applies to**: Phase 2, Phase 3, Phase 4
**Owner**: Automated script (scripts/enrich_leads_haiku.py)

---

## BATCH STRUCTURE

### Input Batch Format
```json
{
  "leads": [
    {
      "name": "Hotel Name",
      "address": "Street Address, Postal Code City",
      "country": "Country Name",
      "phone": "+CountryCode Number",
      "website": "https://example.com (optional)"
    },
    ...
  ]
}
```

### Maximum Batch Size: 5 Leads
- Hard limit per FIRSTWAVE_SYSTEM_CONTEXT.md § 8.2
- Rationale: Haiku rate limits (~100 req/min), cost optimization, error isolation
- If received with >5 leads: Split into sub-batches automatically

### Batch Naming
- Format: `batch_NNNL` where NNN = batch sequence, L = phase letter
- Examples:
  - `batch_001P`: Phase 1 (pilot), batch 1
  - `batch_045E`: Phase 2 (bulk search), batch 45
  - `batch_032R`: Phase 3 (enrichment refine), batch 32

---

## PROCESSING PIPELINE

### Step 1: Pre-Batch Validation (No API Calls)
For each lead in batch:
```
1. Check: name is non-empty → pass
2. Check: address contains city OR address contains postal code → pass
3. Check: country is in approved list (EU-28 + US-50) → pass
4. Check: phone OR website present → pass
```

If any lead fails:
- Log warning: "Invalid lead data: [name] - missing [field]"
- Skip to next lead (don't call API)
- Increment "validation_errors" counter in batch result

### Step 2: Clarification Pass (Haiku Classifier)
For each validated lead:
```
1. Call classify() with CLARIFICATION_PROMPT
2. Parse JSON response
3. Extract: classification, confidence, reasoning
4. If JSON parse error: Log, set classification="Unclear", confidence=0.0
5. If API error (timeout, rate limit): Queue batch for retry after 60s
6. If trading-hours gate (VybeTradingWindowError): Defer entire batch, alert operator
```

**Classification Outcomes**:
| Classification | Confidence | Action |
|---|---|---|
| Verified Hotel Operator | ≥0.85 | Proceed to enrichment |
| Verified Hotel Operator | 0.75-0.84 | Proceed to enrichment (tag for manual review) |
| Unclear - needs manual review | Any | Skip enrichment, queue for manual |
| Not a Hotel | Any | Skip enrichment, mark discard |

### Step 3: Enrichment Pass (Haiku Generator)
For leads with "Verified Hotel Operator" and confidence ≥0.75:
```
1. Call generate() with ENRICHMENT_PROMPT
2. Parse JSON response
3. Extract: operator_type, team_size_estimate, pain_points, decision_maker_role, region
4. If JSON parse error: Log, return None (skip enrichment)
5. If API error: Retry up to 2 times, then skip enrichment
```

**Enrichment Output Validation**:
- `operator_type` must be one of: "independent", "boutique", "franchise"
- `pain_points` must be an array of 2-5 strings (not empty, not >10)
- `decision_maker_role` must be one of: "Owner", "General Manager", "CMO", "VP Revenue", "Director of CX"

### Step 4: Supabase Write (Optional)
If `--save-supabase` flag set:
```
1. For each enriched lead:
   a. Build record: {first_name, last_name, phone, location, enrichment_data, pain_signals, ...}
   b. Set status based on clarification outcome:
      - confidence ≥0.85: status="verified_hotel"
      - 0.75 ≤ confidence < 0.85: status="manual_review"
      - confidence < 0.75: discard (don't write)
   c. Call supabase.table("leads").insert(record).execute()
   d. On success: Increment "saved" counter, log record ID
   e. On error: Log error, increment "save_errors" counter (don't retry)
```

### Step 5: Batch Result Summary
Return JSON structure:
```json
{
  "batch_id": "batch_001P",
  "timestamp": "2026-05-15T23:15:00Z",
  "input_count": 5,
  "validation_errors": 0,
  "clarification_results": {
    "verified_high_confidence": 4,    // ≥0.85
    "verified_low_confidence": 1,      // 0.75-0.84
    "unclear": 0,
    "rejected": 0
  },
  "enrichment_results": {
    "enriched": 5,
    "skipped": 0,
    "parse_errors": 0
  },
  "supabase_writes": {
    "attempted": 5,
    "saved": 5,
    "errors": 0
  },
  "confidence_distribution": {
    "0.95+": 2,
    "0.85-0.94": 2,
    "0.75-0.84": 1,
    "< 0.75": 0
  },
  "sample_results": [
    {
      "name": "Hotel Zur Post",
      "classification": "Verified Hotel Operator",
      "confidence": 0.92,
      "enrichment": {
        "operator_type": "boutique",
        "decision_maker_role": "General Manager",
        "pain_points": [...]
      }
    }
  ]
}
```

---

## RATE LIMITING & BACKOFF

### Haiku Rate Limits
- **Estimated**: 100+ requests per minute (Haiku is low-cost)
- **Per Anthropic SLA**: Requests are queued; no explicit rate limit published
- **Per Ollama**: 1000+ requests per second (local, unlimited on desktop)

### Backoff Strategy (If Hitting Limits)
```
Attempt 1: Immediate
Attempt 2: Wait 1s, retry
Attempt 3: Wait 2s, retry
Attempt 4: Wait 4s, retry
Attempt 5: Wait 8s, retry
After 5 attempts: Fail batch, log, alert operator
```

### Inter-Batch Delay
- **Between batches**: 1-2 seconds (prevents request collision)
- **During trading-hours deferral**: Check cooloff key every 30s, process when window opens

---

## ERROR HANDLING

### Recoverable Errors (Retry)
- API timeout (subprocess timeout, httpx timeout)
- Rate limit (HTTP 429)
- Network connection error
- JSON parse error (incomplete response)

**Retry logic**: Exponential backoff, max 3-5 attempts, then fail gracefully

### Unrecoverable Errors (Fail Batch)
- Invalid API credentials
- Malformed system prompt
- VybeTradingWindowError (trading-hours gate)
- Supabase connection error (if --save-supabase set)

**Handling**: Log error, alert operator via Telegram (if available), output batch result with error field

### Operator Alerts (Telegram)
Send alert if:
1. Batch size >5 (auto-split)
2. >1 validation error (bad input data)
3. >20% enrichment failures (possible API issue)
4. Trading-hours gate triggered (batch deferred)
5. Supabase write errors (if --save-supabase set)

---

## COST TRACKING

### Per-Batch Cost Calculation
```
Clarification calls: 5 leads × 1 call = 5 Haiku calls
Enrichment calls: 4 leads × 1 call = 4 Haiku calls (assuming 1 filtered out)
Total per batch: 9 Haiku calls

Cost per call: ~€0.0005 (Haiku at ~€1.50 per million tokens, ~200 tokens per call)
Total per batch: 9 × €0.0005 = €0.0045

For 2000 leads: (2000 / 5 batches) × €0.0045 = €1.80 (clarification + enrichment)
```

### Tracking in Redis
- Log each batch result to `llm:calls` sorted set (shared with vybe-trading)
- Include: source="firstwave", caller="batch_enrich", batch_id
- Used for real-time cost dashboard and quota management

---

## QUALITY ASSURANCE CHECKPOINTS

### During Batch Processing
- [ ] First batch: Log raw responses (first 3 leads) for spot-check
- [ ] Every 10 batches: Manual verify 5 leads (confidence, pain_points, DM role)
- [ ] Log confidence distribution after each phase

### Post-Phase Validation
After Phase 3 (full enrichment pass):
- [ ] Plot confidence distribution (histogram)
- [ ] Identify outliers (leads with very high or low confidence)
- [ ] Spot-check >0.75 confidence leads manually (>90% should match human judgment)
- [ ] Calculate false positive / false negative rates

---

## OPERATIONAL RUNBOOK

### Phase 1: Pilot (50 leads, batches 001-010)
```bash
source venv/bin/activate
python scripts/enrich_leads_haiku.py \
  --input scripts/sample_leads.json \
  --batch-size 5 \
  --force-allow \
  --save-supabase
# Expected: 10 batches, ~2 minutes, €0.04 cost
```

### Phase 2: Bulk Search (1200-1400 leads, batches 011-290)
```bash
# Generate bulk lead input from EU/US registries (manual, 3-5 days)
# Then:
python scripts/enrich_leads_haiku.py \
  --input data/bulk_leads_phase2.json \
  --batch-size 5 \
  # No --force-allow (respect trading-hours gate)
  # No --save-supabase (review manually first)
# Expected: 280 batches, ~4-6 hours off-peak, €1.26 cost
```

### Phase 3: Clarification + Enrichment (1200+ leads, batches 291-540)
```bash
# Run same script, enable --save-supabase
python scripts/enrich_leads_haiku.py \
  --input data/bulk_leads_phase3.json \
  --batch-size 5 \
  --save-supabase
# Expected: 250 batches, ~4-5 hours off-peak, €1.13 cost
```

---

## MONITORING & LOGGING

### Log Levels
- **INFO**: Batch start, lead processing, batch complete, Supabase writes
- **WARNING**: Validation errors, confidence < 0.75, retry attempts, trading-hours defer
- **ERROR**: API failures, JSON parse errors, Supabase connection errors

### Log Output
- Console: Real-time progress (human-readable)
- File: `logs/enrich_YYYYMMDD_HHMMSS.log` (structured, searchable)
- Redis: `llm:calls` sorted set (cost tracking)

### Sample Log Lines
```
2026-05-15 23:13:17 [INFO] Loaded 57 leads from scripts/sample_leads.json
2026-05-15 23:13:17 [INFO] Processing batch_001P (5 leads)...
2026-05-15 23:13:18 [INFO] [batch_001P] Processing lead 1/5: Hotel Zur Post
2026-05-15 23:13:18 [INFO] HTTP Request: POST http://<desktop-tailscale-ip>:11434/api/generate "HTTP/1.1 200 OK"
2026-05-15 23:13:18 [INFO]   Classification: Verified Hotel Operator (confidence: 0.92)
2026-05-15 23:13:19 [INFO]   Enriched: boutique | DM: General Manager
```

