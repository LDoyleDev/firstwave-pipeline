# Pipeline Coordination — Multi-Shell Parallel Execution

**Purpose**: Coordinate 4+ concurrent shells during Phase 2–4 without conflicts
**Strategy**: Geographic/regional separation, serialized dedup, parallel enrichment
**Timeline**: 2026-05-22 to 2026-07-10 (Phases 2–4)

---

## SHELL ASSIGNMENT MATRIX

### Phase 2: Data Source Scraping (Week 1: 2026-05-22 to 2026-05-28)

| Shell | Region | Sources | Output File | Lead Target | Owner | Status |
|-------|--------|---------|-------------|-------------|-------|--------|
| A | EU-West (DE, FR) | Bundesanzeiger, SIRENE, Chambers | `data/phase2_batch_001_050.json` | 300 | — | pending |
| B | EU-Central (UK, ES) | Companies House, BORME, Chambers | `data/phase2_batch_051_100.json` | 300 | — | pending |
| C | EU-South (IT, NL, BE) | Registro Imprese, KVK, KBE | `data/phase2_batch_101_150.json` | 300 | — | pending |
| D | US (Top 10 metros) | SoS databases, OpenCorporates | `data/phase2_batch_151_250.json` | 400 | — | pending |
| E | APIs (Booking, Expedia) | Partner APIs | `data/phase2_batch_251_290.json` | 200 | — | pending |

**Completion criteria per shell**:
- JSON file created with 300–400 leads
- All required fields: name, address, country, phone, website (optional)
- No duplicates within shell's output (dedup across shells happens later)

---

### Phase 2: Deduplication (Serialized: 2026-05-28, Single Shell)

| Step | Script | Input | Output | Duration | Owner |
|------|--------|-------|--------|----------|-------|
| 1 | `scripts/combine_batches.py` | All 5 batch JSONs | `data/phase2_combined.json` | 5 min | — |
| 2 | `scripts/normalize_leads.py` | combined.json | `data/phase2_normalized.json` | 10 min | — |
| 3 | `scripts/dedup_leads.py` | normalized.json | `data/phase2_deduped.json` | 15 min | — |
| 4 | `scripts/screening_filter.py` | deduped.json | `data/phase2_candidates_final.json` | 5 min | — |

**Output**: 1200–1400 candidate leads ready for Haiku clarification

---

### Phase 3: Haiku Enrichment (Week 2–3: 2026-06-05 to 2026-06-26)

| Shell | Batch Range | Leads | Input File | Output (Supabase) | Duration | Owner | Status |
|-------|-------------|-------|------------|-------------------|----------|-------|--------|
| A | 001–050 | 250 | `phase2_candidates_final.json[0:250]` | leads table, status=verified_hotel | 45 min | — | pending |
| B | 051–100 | 250 | `phase2_candidates_final.json[250:500]` | leads table, status=verified_hotel | 45 min | — | pending |
| C | 101–150 | 250 | `phase2_candidates_final.json[500:750]` | leads table, status=verified_hotel | 45 min | — | pending |
| D | 151–200 | 250 | `phase2_candidates_final.json[750:1000]` | leads table, status=verified_hotel | 45 min | — | pending |
| E | 201–240 | ~200 | `phase2_candidates_final.json[1000:1200]` | leads table, status=verified_hotel | 35 min | — | pending |

**Parallel execution**: All 5 shells run simultaneously on Saturday or Sunday
**Completion**: All 1200+ leads have enrichment_data, pain_signals, decision_maker_role in Supabase

---

### Phase 4: Secondary Sources + Manual Review (Week 4: 2026-06-26 to 2026-07-10)

| Shell | Task | Source | Lead Target | Output | Owner | Status |
|-------|------|--------|-------------|--------|-------|--------|
| A | Franchise directory scraping | Marriott, IHG, Hilton | 200 | `data/phase4_franchises.json` | — | pending |
| B | Tourism board scraping | National/regional boards | 200 | `data/phase4_tourism.json` | — | pending |
| C | Manual review (unclear queue) | Supabase manual_review status | 100–150 | Enrichment updates | — | pending |
| D | LinkedIn reverse lookup | PhantomBuster campaign | 100–150 | `data/phase4_linkedin.json` | — | pending |
| E | QA + spot verification | Random sample validation | 50 | Report | — | pending |

---

## SAFETY RULES

### Rule 1: Shell Isolation (No Cross-Shell Conflicts)
✅ **OK**:
- Shell A scrapes `data/phase2_batch_001_050.json`
- Shell B scrapes `data/phase2_batch_051_100.json` (different file, no conflict)

❌ **NOT OK**:
```bash
# Shell A and B both trying to write to same file
Shell-A: python enrich_leads_haiku.py --input batch_001.json --save-supabase
Shell-B: python enrich_leads_haiku.py --input batch_001.json --save-supabase  # DUPLICATE WRITES!
```

### Rule 2: Sequential Gates (Dedup Must Be Serial)
✅ **Correct sequence**:
1. All shells (A–E) finish scraping → 5 independent JSON files
2. **Wait** for all shells to report completion
3. **Single shell** runs `combine_batches.py` + `dedup_leads.py`
4. Output: `data/phase2_candidates_final.json` (deduplicated)
5. All shells proceed to enrichment using this single file

❌ **Wrong**:
- Running dedup while scrapers are still writing (file corruption, missed leads)

### Rule 3: Supabase Concurrent Writes (Safe, But Don't Duplicate)
✅ **Safe**: Multiple shells insert non-overlapping ranges
```python
# Shell A inserts leads 0–250
# Shell B inserts leads 251–500
# Shell C inserts leads 501–750
# PostgreSQL handles concurrent inserts gracefully
```

❌ **Unsafe**: Two shells both insert the same lead (duplicate primary key error)

### Rule 4: Claude Max Quota Monitoring
- All shells combined should not exceed user's daily Max limit
- **Estimate**: Phase 3 enrichment = 4000 Haiku calls (distributed across 5 shells)
  - If 80% Ollama success: ~800 Claude Max fallbacks
  - At ~Haiku cost: Negligible
- **Check** `llm:calls` Redis key after each shell completes (for cost tracking)

### Rule 5: Trading-Hours Coordination
- **All Phase 2–3 work happens Saturday only** (safest, zero vybe-trading conflict)
- If extending to Sunday: 00:00–22:00 UTC only (before futures resume)
- If running Mon–Fri: Only 21:00–22:00 UTC windows (limit to small batches)

---

## EXECUTION CHECKLIST

### Pre-Execution (2026-05-22)
- [ ] **Stop vybe-trading** (or confirm it's idle until Saturday evening)
- [ ] **Check Redis cooloff key**: `redis-cli get llm:claude:cooloff_until` (should be None)
- [ ] **Verify Ollama is running**: `curl http://100.113.88.92:11434/api/tags`
- [ ] **Test Supabase connectivity**: `PYTHONPATH=. python -c "from backend.integrations.supabase_client import test_connection; print(test_connection())"`
- [ ] **Create data/ directory**: `mkdir -p data/`

### Phase 2 Scraping (Saturday 2026-05-25, 09:00–16:00 UTC)

```bash
# Terminal 1 (Shell A — DE + FR)
cd /home/vybe/firstwave-pipeline
source venv/bin/activate
python scripts/scrape_eu_west.py --output data/phase2_batch_001_050.json 2>&1 | tee logs/shell_a.log

# Terminal 2 (Shell B — UK + ES)
cd /home/vybe/firstwave-pipeline
source venv/bin/activate
python scripts/scrape_eu_central.py --output data/phase2_batch_051_100.json 2>&1 | tee logs/shell_b.log

# Terminal 3 (Shell C — IT + NL + BE)
cd /home/vybe/firstwave-pipeline
source venv/bin/activate
python scripts/scrape_eu_south.py --output data/phase2_batch_101_150.json 2>&1 | tee logs/shell_c.log

# Terminal 4 (Shell D — US)
cd /home/vybe/firstwave-pipeline
source venv/bin/activate
python scripts/scrape_us.py --output data/phase2_batch_151_250.json 2>&1 | tee logs/shell_d.log

# Terminal 5 (Shell E — APIs)
cd /home/vybe/firstwave-pipeline
source venv/bin/activate
python scripts/scrape_booking_expedia.py --output data/phase2_batch_251_290.json 2>&1 | tee logs/shell_e.log

# Monitor: Check for all 5 files created
watch 'ls -lh data/phase2_batch_*.json'
```

**Completion check**:
```bash
for file in data/phase2_batch_*.json; do
  count=$(jq '.leads | length' "$file")
  echo "$file: $count leads"
done
# Expected: 5 files, 300–400 leads each = 1500–2000 total
```

### Phase 2 Dedup (Sequential, Sunday 2026-05-26, 10:00–11:00 UTC)

```bash
# Single shell: Combine, normalize, dedup, screen
cd /home/vybe/firstwave-pipeline
source venv/bin/activate

python scripts/combine_batches.py \
  --inputs data/phase2_batch_*.json \
  --output data/phase2_combined.json && echo "✓ Combined"

python scripts/normalize_leads.py \
  --input data/phase2_combined.json \
  --output data/phase2_normalized.json && echo "✓ Normalized"

python scripts/dedup_leads.py \
  --input data/phase2_normalized.json \
  --output data/phase2_deduped.json && echo "✓ Deduplicated"

python scripts/screening_filter.py \
  --input data/phase2_deduped.json \
  --output data/phase2_candidates_final.json && echo "✓ Screened"

# Final count
jq '.leads | length' data/phase2_candidates_final.json
# Expected: 1200–1400 leads
```

### Phase 3 Enrichment (Parallel, Saturday 2026-06-05, 09:00–11:00 UTC)

```bash
# Terminal 1 (Shell A — Leads 0–250)
source venv/bin/activate
python scripts/batch_split.py \
  --input data/phase2_candidates_final.json \
  --range 0:250 \
  --output data/phase3_chunk_a.json
python scripts/enrich_leads_haiku.py \
  --input data/phase3_chunk_a.json \
  --save-supabase 2>&1 | tee logs/enrich_a.log

# Terminal 2 (Shell B — Leads 250–500)
source venv/bin/activate
python scripts/batch_split.py \
  --input data/phase2_candidates_final.json \
  --range 250:500 \
  --output data/phase3_chunk_b.json
python scripts/enrich_leads_haiku.py \
  --input data/phase3_chunk_b.json \
  --save-supabase 2>&1 | tee logs/enrich_b.log

# ... repeat for C, D, E ...

# Monitor enrichment progress
watch 'grep -h "Enriched\|verified\|rejected" logs/enrich_*.log | tail -20'
```

### Phase 4 Secondary Sources (Parallel, 2026-06-26 onwards)

```bash
# Terminal 1 (Shell A — Franchises)
python scripts/scrape_franchises.py --output data/phase4_franchises.json

# Terminal 2 (Shell B — Tourism boards)
python scripts/scrape_tourism_boards.py --output data/phase4_tourism.json

# Terminal 3 (Shell C — Manual review)
python scripts/manual_review_enrich.py --supabase-table leads --status manual_review

# Terminal 4 (Shell D — LinkedIn)
python scripts/linkedin_reverse_lookup.py --output data/phase4_linkedin.json

# Terminal 5 (Shell E — QA verification)
python scripts/spot_check_verification.py --sample-size 50
```

---

## MONITORING & LOGGING

Each shell logs to `logs/shell_[A-E].log`:
```bash
tail -f logs/shell_a.log  # Terminal 6: Monitor Shell A
tail -f logs/shell_b.log  # Terminal 7: Monitor Shell B
```

**Summary command** (run in separate window):
```bash
watch -n 5 'echo "=== Files ===" && ls -lh data/phase2_batch_*.json && \
             echo "=== Logs ===" && tail -5 logs/shell_*.log'
```

---

## ROLLBACK / ERROR RECOVERY

If Shell A fails mid-scrape:
```bash
# Shell A crashed on lead 150/300
# Restart from checkpoint
python scripts/scrape_eu_west.py \
  --output data/phase2_batch_001_050.json \
  --resume-from-lead 150  # Implement checkpoint logic
```

If dedup fails:
```bash
# Restore from combined.json and re-run
python scripts/dedup_leads.py \
  --input data/phase2_combined.json \
  --output data/phase2_deduped_v2.json \
  --verbose  # Debug mode
```

If Supabase write fails during enrichment:
```bash
# Shell B crashed after enriching 180/250
# Re-run enrichment (idempotent, will overwrite existing records)
python scripts/enrich_leads_haiku.py \
  --input data/phase3_chunk_b.json \
  --save-supabase \
  --verbose
```

---

## SUCCESS METRICS

### Phase 2 Complete (2026-05-28)
- [ ] 5 batch JSON files created (001–290)
- [ ] Total leads: 1500–2000 before dedup
- [ ] After dedup: 1200–1400 candidates
- [ ] All have: name, address, country, phone/website

### Phase 3 Complete (2026-06-26)
- [ ] All 1200+ leads enriched in Supabase
- [ ] Clarification confidence: ≥0.75
- [ ] Enrichment fields: operator_type, pain_points, decision_maker_role
- [ ] Cost: ~€4–5 (Haiku)
- [ ] Manual review queue: ~100–200 (0.75–0.84 confidence tier)

### Phase 4 Complete (2026-07-10)
- [ ] 2000+ total leads (1200 verified + ~300 secondary sources + ~500 manual + LinkedIn)
- [ ] All have: enrichment_data, pain_signals, decision_maker_role
- [ ] GDPR compliance: EU leads marked with privacy_basis
- [ ] Cost: ~€6–8 total (all phases)

