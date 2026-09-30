# Phase 2 Quick Start — Data Source Scraping

> **Note (repository made public, 2026-09-30):** the five regional Phase 2
> scraper scripts referenced below (`scrape_eu_west.py`, `scrape_eu_central.py`,
> `scrape_eu_south.py`, `scrape_us.py`, `scrape_booking_expedia.py`) were removed
> before publication — four were placeholder scaffolding, and the fifth scraped
> OTA sites whose terms prohibit it. The commands naming them no longer resolve.
> The lead sourcing that actually worked is `scrape_osm.py` plus the
> `website_fetch` / `provenance` pipeline. See the README.


**Scheduled**: Saturday 2026-05-25, 09:00–16:00 UTC
**Objective**: Scrape 1500–2000 raw hotel leads from 5 regions
**Duration**: 6–8 hours (all 5 shells parallel) + 1 hour (dedup serial)
**Output**: 1200–1400 verified candidate leads ready for Phase 3 enrichment

---

## Pre-Execution Checklist (Friday 2026-05-24)

```bash
# 1. Verify Ollama is running (optional for Phase 2, required for Phase 3)
curl http://100.113.88.92:11434/api/tags

# 2. Verify Supabase connectivity
PYTHONPATH=. python -c "from backend.integrations.supabase_client import test_connection; print('OK' if test_connection() else 'FAIL')"

# 3. Activate venv (verify Python + dependencies)
source venv/bin/activate
python -c "import json; print('OK')"

# 4. Create logs directory
mkdir -p logs data/phase2

# 5. Check disk space
df -h | grep /home
# Need: ~500 MB free for raw leads + working files
```

---

## OPTION 1: Automated Orchestration (Recommended)

Run the master orchestration script — handles all 5 scrapers + dedup pipeline:

```bash
cd /home/vybe/firstwave-pipeline
source venv/bin/activate

# Dry run (limit 50 leads per scraper, for testing)
./scripts/phase2_orchestrate.sh --parallel --test

# Full run (Saturday, parallel scrapers)
./scripts/phase2_orchestrate.sh --parallel

# Or sequential (one scraper at a time)
./scripts/phase2_orchestrate.sh --sequential
```

**Output**:
- Logs: `logs/shell_*.log` (one per scraper)
- Dedup logs: `logs/dedup_*.log`
- Final candidates: `data/phase2/candidates_final.json` (~1200–1400 leads)

---

## OPTION 2: Manual Multi-Shell Execution

For fine-grained control, open 5 terminal tabs and run separately:

### Terminal 1 — Shell A (EU-West: Germany + France)
```bash
cd /home/vybe/firstwave-pipeline && source venv/bin/activate
python scripts/scrape_eu_west.py --output data/phase2/batch_001_050.json 2>&1 | tee logs/shell_a.log
# Expected: ~150 leads in 10–20 minutes
```

### Terminal 2 — Shell B (EU-Central: UK + Spain)
```bash
cd /home/vybe/firstwave-pipeline && source venv/bin/activate
python scripts/scrape_eu_central.py --output data/phase2/batch_051_100.json 2>&1 | tee logs/shell_b.log
# Expected: ~150 leads in 10–20 minutes
```

### Terminal 3 — Shell C (EU-South: Italy + Netherlands + Belgium)
```bash
cd /home/vybe/firstwave-pipeline && source venv/bin/activate
python scripts/scrape_eu_south.py --output data/phase2/batch_101_150.json 2>&1 | tee logs/shell_c.log
# Expected: ~150 leads in 10–20 minutes
```

### Terminal 4 — Shell D (US: Top 10 metros)
```bash
cd /home/vybe/firstwave-pipeline && source venv/bin/activate
python scripts/scrape_us.py --output data/phase2/batch_151_250.json 2>&1 | tee logs/shell_d.log
# Expected: ~200 leads in 15–25 minutes
```

### Terminal 5 — Shell E (APIs: Booking.com + Expedia)
```bash
cd /home/vybe/firstwave-pipeline && source venv/bin/activate
python scripts/scrape_booking_expedia.py --output data/phase2/batch_251_290.json 2>&1 | tee logs/shell_e.log
# Expected: ~100 leads in 10–15 minutes
```

### Terminal 6 — Monitor Progress
```bash
watch -n 5 'echo "=== Batch Files ===" && ls -lh data/phase2/batch_*.json && echo "=== Log Tails ===" && tail -3 logs/shell_*.log'
```

### When All 5 Shells Complete (check Terminal 6):
Once all 5 batch files exist and logs show ✓ completion:

```bash
# Verify all files created
for f in data/phase2/batch_*.json; do
  echo "$f: $(jq '.leads | length' "$f") leads"
done
# Expected: 5 files, 1500-2000 total leads
```

---

## Dedup Pipeline (After All Scrapers Done)

**Run in a single shell** (serial, ~30 minutes total):

```bash
cd /home/vybe/firstwave-pipeline && source venv/bin/activate

# Step 1: Combine all 5 batch files
echo "Combining batches..."
python scripts/combine_batches.py \
  --inputs "data/phase2/batch_*.json" \
  --output data/phase2/combined.json

# Step 2: Deduplicate (SHA1 hash on name+address)
echo "Deduplicating..."
python scripts/dedup_leads.py \
  --input data/phase2/combined.json \
  --output data/phase2/deduped.json

# Step 3: Screen & validate leads (non-LLM filters)
echo "Screening..."
python scripts/screening_filter.py \
  --input data/phase2/deduped.json \
  --output data/phase2/candidates_final.json

# Verify final output
echo "Final count:"
jq '.leads | length' data/phase2/candidates_final.json
# Expected: 1200–1400 leads
```

---

## What the Scrapers Do (Placeholder Implementations)

⚠️ **Important**: The current scripts are **templates with sample data**. For production, you'll need to:

1. **Bundesanzeiger (Germany)**
   - Replace sample data with actual API/bulk export query
   - Filter: business_type = "Hotel" OR "Inn" OR "Resort"
   - Extract: name, address, phone, website

2. **SIRENE (France)**
   - Replace with actual inseedatasets.fr API calls
   - Filter: APE code 5510Z (Hotels)

3. **Companies House (UK)**
   - Use beta.companieshouse.gov.uk API
   - Filter: SIC 5510, 5511, 5512

4. **BORME (Spain)**
   - Query borme.es registry
   - Filter: NACE 5510 (accommodation)

5. **Booking.com + Expedia APIs**
   - Authenticate with partner APIs
   - Query: Active hotel properties in target cities

---

## Expected Results

### Before Dedup
- Total leads: 1500–2000
- Geographic distribution: EU 60%, US 40%

### After Dedup
- Deduplicated: 1200–1400 leads
- Dedup rate: 5–10% (removes cross-registry duplicates)

### After Screening
- Passed validation: 1200–1400 leads (90%+ pass rate)
- Fields: name, address, country, phone/website, decision_maker_role (if scraped)

### Ready for Phase 3
- Status: `candidates` (waiting for Haiku clarification)
- File: `data/phase2/candidates_final.json`
- Next: Phase 3 enrichment scheduled for Saturday 2026-06-05

---

## Troubleshooting

### Error: "No such file or directory" (data/phase2/...)
```bash
mkdir -p data/phase2 logs
# Re-run scraper
```

### Error: "JSON decode error" (dedup step)
- Check batch files are valid JSON: `jq . data/phase2/batch_*.json`
- If invalid, delete broken file and re-scrape

### Error: "Screening filter rejects all leads"
- Check APPROVED_COUNTRIES list in screening_filter.py
- Verify scrapers are setting `country` field correctly

### Scraper hangs or times out
- Check network connectivity: `curl -I https://google.com`
- Check Ollama (if used): `curl http://100.113.88.92:11434/api/tags`
- Manually interrupt (Ctrl+C) and re-run with `--limit 50` for testing

---

## Post-Phase 2 Checklist

- [ ] Final output file: `data/phase2/candidates_final.json`
- [ ] Lead count: 1200–1400
- [ ] All leads have: name, address, country, phone/website
- [ ] Dedup rate logged
- [ ] Pass rate logged
- [ ] Ready for Phase 3? (Confirm with Liam)

**Next step**: Phase 3 enrichment on Saturday 2026-06-05
**See**: `docs/PIPELINE_COORDINATION.md` (Phase 3 Enrichment section)

