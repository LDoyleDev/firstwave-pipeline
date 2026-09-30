#!/bin/bash
# Phase 2 dedup / screening pipeline.
#
# NOTE: this script originally also ran five regional "scraper template" scripts
# that were removed before this repository was made public — they targeted
# company registries and OTA sites, and their hardcoded target lists were
# placeholder scaffolding that never produced usable output. See README.
#
# It now operates on whatever batch files already exist in data/phase2/, and
# runs the parts that did real work: combine -> dedup -> screen.
#
# Usage: ./phase2_orchestrate.sh

set -e

PHASE2_DIR="data/phase2"
LOG_DIR="logs"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

mkdir -p "$PHASE2_DIR" "$LOG_DIR"
source venv/bin/activate

echo -e "${BLUE}=== Phase 2: dedup / screening ===${NC}"
echo ""

# Count whatever input batches are present
echo -e "${YELLOW}--- INPUT BATCHES ---${NC}"
total_leads=0
shopt -s nullglob
batches=("$PHASE2_DIR"/batch_*.json)
if [ ${#batches[@]} -eq 0 ]; then
  echo -e "${RED}No batch files in $PHASE2_DIR — nothing to process.${NC}"
  exit 1
fi
for file in "${batches[@]}"; do
  count=$(jq '.leads | length' "$file")
  echo "  $(basename "$file"): $count leads"
  total_leads=$((total_leads + count))
done
echo "  TOTAL: $total_leads leads"

# Dedup pipeline (serial, single shell)
echo ""
echo -e "${YELLOW}--- DEDUP PIPELINE (Serial) ---${NC}"

echo -e "${BLUE}[1] Combining batches...${NC}"
python scripts/combine_batches.py \
  --inputs "$PHASE2_DIR/batch_*.json" \
  --output "$PHASE2_DIR/combined.json" 2>&1 | tee "$LOG_DIR/dedup_combine.log"

echo -e "${BLUE}[2] Deduplicating...${NC}"
python scripts/dedup_leads.py \
  --input "$PHASE2_DIR/combined.json" \
  --output "$PHASE2_DIR/deduped.json" 2>&1 | tee "$LOG_DIR/dedup_hash.log"

echo -e "${BLUE}[3] Screening/filtering...${NC}"
python scripts/screening_filter.py \
  --input "$PHASE2_DIR/deduped.json" \
  --output "$PHASE2_DIR/candidates_final.json" 2>&1 | tee "$LOG_DIR/dedup_screen.log"

# Final summary
echo ""
echo -e "${YELLOW}--- PHASE 2 FINAL SUMMARY ---${NC}"

if [ -f "$PHASE2_DIR/candidates_final.json" ]; then
  final_count=$(jq '.leads | length' "$PHASE2_DIR/candidates_final.json")
  echo -e "${GREEN}✓ Final candidates: $final_count leads${NC}"
  echo "  File: $PHASE2_DIR/candidates_final.json"
  echo "  Ready for Phase 3 enrichment"
else
  echo -e "${RED}✗ Error: Final output file not created${NC}"
  exit 1
fi

echo ""
echo -e "${GREEN}=== Phase 2 Complete ===${NC}"
echo "Next: Phase 3 enrichment (scheduled for 2026-06-05)"
echo "See docs/PIPELINE_COORDINATION.md for Phase 3 execution"
