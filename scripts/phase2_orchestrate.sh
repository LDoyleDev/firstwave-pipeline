#!/bin/bash
# Phase 2 Master Orchestration Script
# Runs all 5 regional scrapers, then dedup/screening pipeline
# Usage: ./phase2_orchestrate.sh [--parallel|--sequential] [--test]

set -e

PHASE2_DIR="data/phase2"
LOG_DIR="logs"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
PARALLEL=true
TEST_MODE=false

for arg in "$@"; do
  case $arg in
    --sequential)
      PARALLEL=false
      shift
      ;;
    --parallel)
      PARALLEL=true
      shift
      ;;
    --test)
      TEST_MODE=true
      shift
      ;;
    *)
      echo "Unknown option: $arg"
      exit 1
      ;;
  esac
done

# Setup
mkdir -p "$PHASE2_DIR" "$LOG_DIR"
source venv/bin/activate

echo -e "${BLUE}=== Phase 2 Master Orchestration ===${NC}"
echo "Mode: $([ "$PARALLEL" = true ] && echo 'PARALLEL' || echo 'SEQUENTIAL')"
echo "Test mode: $([ "$TEST_MODE" = true ] && echo 'ON (--limit 50)' || echo 'OFF')"
echo ""

# Common arguments
LIMIT_ARG=""
[ "$TEST_MODE" = true ] && LIMIT_ARG="--limit 50"

# Run scrapers
run_scraper() {
  local name=$1
  local script=$2
  local output=$3

  echo -e "${BLUE}[Shell] Starting: $name${NC}"
  if [ "$PARALLEL" = true ]; then
    python "$script" --output "$output" $LIMIT_ARG 2>&1 | tee "$LOG_DIR/shell_${name}.log" &
    echo "  (running in background)"
  else
    python "$script" --output "$output" $LIMIT_ARG 2>&1 | tee "$LOG_DIR/shell_${name}.log"
    echo "  (completed)"
  fi
}

echo -e "${YELLOW}--- SCRAPING PHASE (5 shells) ---${NC}"
run_scraper "a_eu_west" "scripts/scrape_eu_west.py" "$PHASE2_DIR/batch_001_050.json"
run_scraper "b_eu_central" "scripts/scrape_eu_central.py" "$PHASE2_DIR/batch_051_100.json"
run_scraper "c_eu_south" "scripts/scrape_eu_south.py" "$PHASE2_DIR/batch_101_150.json"
run_scraper "d_us" "scripts/scrape_us.py" "$PHASE2_DIR/batch_151_250.json"
run_scraper "e_apis" "scripts/scrape_booking_expedia.py" "$PHASE2_DIR/batch_251_290.json"

# If parallel, wait for all scrapers
if [ "$PARALLEL" = true ]; then
  echo -e "${YELLOW}Waiting for all 5 scrapers to complete...${NC}"
  wait
  echo -e "${GREEN}✓ All scrapers completed${NC}"
fi

# Count leads
echo ""
echo -e "${YELLOW}--- SCRAPING SUMMARY ---${NC}"
total_leads=0
for file in "$PHASE2_DIR"/batch_*.json; do
  if [ -f "$file" ]; then
    count=$(jq '.leads | length' "$file")
    echo "  $(basename "$file"): $count leads"
    total_leads=$((total_leads + count))
  fi
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
