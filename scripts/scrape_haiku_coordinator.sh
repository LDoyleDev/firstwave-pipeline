#!/bin/bash
# Parallel Haiku scraping coordinator
# Launches 5 shells, each processing a different source manifest

set -e

cd "$(dirname "$0")/.."
source venv/bin/activate

mkdir -p logs data/phase2
export FIRSTWAVE_LLM_ALWAYS_ALLOW=1

echo "=== Multi-Haiku Scraping Pipeline ==="
echo "Launching 5 parallel scraping shells..."
echo ""

SHELLS=(
  "shell_1_wiki_eu"
  "shell_2_wiki_uk_es_it"
  "shell_3_wiki_us_nl"
  "shell_4_directories"
  "shell_5_associations_tourism"
)

PIDS=()
for shell in "${SHELLS[@]}"; do
  source_file="scripts/sources/${shell}.json"
  output_file="data/phase2/haiku_${shell}.json"
  log_file="logs/haiku_${shell}.log"

  echo "  Launching: $shell"
  python scripts/scrape_with_haiku.py \
    --input "$source_file" \
    --output "$output_file" \
    --delay 1.5 \
    > "$log_file" 2>&1 &
  PIDS+=($!)
done

echo ""
echo "Waiting for all 5 shells to complete..."
echo "(Monitor: tail -f logs/haiku_*.log)"
echo ""

for pid in "${PIDS[@]}"; do
  wait "$pid" || echo "Shell $pid had errors (see logs)"
done

echo ""
echo "=== All shells complete ==="
echo ""

TOTAL=0
for shell in "${SHELLS[@]}"; do
  output_file="data/phase2/haiku_${shell}.json"
  if [ -f "$output_file" ]; then
    count=$(jq '.leads | length' "$output_file")
    echo "  $shell: $count leads"
    TOTAL=$((TOTAL + count))
  fi
done
echo "  ─────────────────────"
echo "  TOTAL RAW: $TOTAL leads"
echo ""

echo "[1] Combining batches..."
python scripts/combine_batches.py \
  --inputs "data/phase2/haiku_*.json" \
  --output data/phase2/haiku_combined.json

echo "[2] Deduplicating..."
python scripts/dedup_leads.py \
  --input data/phase2/haiku_combined.json \
  --output data/phase2/haiku_deduped.json

echo "[3] Screening..."
python scripts/screening_filter.py \
  --input data/phase2/haiku_deduped.json \
  --output data/phase2/haiku_candidates.json

echo ""
FINAL=$(jq '.leads | length' data/phase2/haiku_candidates.json)
echo "=== FINAL: $FINAL candidate leads in data/phase2/haiku_candidates.json ==="
