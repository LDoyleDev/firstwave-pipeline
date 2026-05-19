#!/bin/bash
# Launch 5 parallel enrichment shells RESPECTING the vybe-trading gate.
# Use at off-hours: Saturday all day, Sunday before 22:00 UTC, daily 21:00-22:00 UTC.
#
# Safe to fire from cron — anthropic_client.py defers calls when vybe-trading active.

set -e
cd "$(dirname "$0")/.."
source venv/bin/activate

mkdir -p logs

# DO NOT set FIRSTWAVE_LLM_ALWAYS_ALLOW=1 — we want the gate to apply.

echo "=== After-hours enrichment ==="
echo "Started: $(date)"
echo ""

# Verify chunks exist
for i in 1 2 3 4 5; do
  chunk="data/phase2/enrich_chunk_${i}.json"
  if [ ! -f "$chunk" ]; then
    echo "Missing $chunk - aborting"
    exit 1
  fi
  count=$(jq '.leads | length' "$chunk")
  echo "  Chunk $i: $count leads"
done

echo ""
echo "Launching 5 parallel enrichment shells..."
PIDS=()
for i in 1 2 3 4 5; do
  nohup python scripts/enrich_leads_haiku.py \
    --input "data/phase2/enrich_chunk_${i}.json" \
    --batch-size 5 \
    --save-supabase \
    > "logs/enrich_chunk_${i}.log" 2>&1 &
  PIDS+=($!)
  echo "  Chunk $i PID: $!"
done

echo ""
echo "Waiting for all 5 shells to complete..."
for pid in "${PIDS[@]}"; do
  wait "$pid" 2>/dev/null || echo "Shell $pid finished with errors"
done

echo ""
echo "=== Enrichment complete: $(date) ==="
echo ""

# Summary
TOTAL_SAVED=0
for i in 1 2 3 4 5; do
  saved=$(grep -c "Saved to Supabase" "logs/enrich_chunk_${i}.log" 2>/dev/null || echo 0)
  echo "  Chunk $i: $saved leads saved"
  TOTAL_SAVED=$((TOTAL_SAVED + saved))
done
echo "  ─────────────────────"
echo "  TOTAL SAVED: $TOTAL_SAVED leads"
echo ""

# Auto-run group consolidation
echo "Running group consolidation..."
python scripts/group_consolidate.py
