#!/bin/bash
# Post-enrichment chain: group consolidation → priority scoring → email drafts.
# Waits for all 5 enrichment chunks + Max test to finish, then runs the chain.
#
# Fires automatically when current enrichment work completes.

set -e
cd "$(dirname "$0")/.."
source venv/bin/activate
export FIRSTWAVE_LLM_ALWAYS_ALLOW=1

mkdir -p logs

echo "=== Post-enrichment chain started: $(date) ==="
echo ""

# 1. Wait for enrichment to fully complete
echo "[Waiting for enrichment processes to finish...]"
while pgrep -f "enrich_leads_haiku|enrich_max_test" > /dev/null; do
  sleep 60
done

echo "[All enrichment finished: $(date)]"
echo ""

# 2. Group consolidation
echo "=== Step 1/3: Group consolidation ==="
date
python scripts/group_consolidate.py 2>&1 | tee logs/group_consolidate.log
echo ""

# 3. Priority scoring
echo "=== Step 2/3: Priority scoring ==="
date
python scripts/outreach_score.py 2>&1 | tee logs/priority_score.log
echo ""

# 4. Cold email drafts
echo "=== Step 3/3: Cold email drafts (top 200) ==="
date
python scripts/draft_outreach_emails.py --top-n 200 2>&1 | tee logs/email_drafts.log
echo ""

echo "=== Post-enrichment chain complete: $(date) ==="

# Final summary
echo ""
echo "=== FINAL PIPELINE STATUS ==="
python3 -c "
import json, sys
sys.path.insert(0, '.')
from backend.integrations.supabase_client import supabase

r = supabase.table('leads').select('id, lead_score, enrichment_data, outreach_email_1, outreach_approved').in_('source', ['haiku_pilot', 'haiku_max_test']).execute()
leads = r.data or []
verified = [l for l in leads if (l.get('enrichment_data') or {}).get('verification_status') == 'verified_hotel']
primary = [l for l in verified if (l.get('enrichment_data') or {}).get('is_primary_contact')]
with_draft = [l for l in verified if l.get('outreach_email_1')]
approved = [l for l in leads if l.get('outreach_approved')]

print(f'Total leads ingested:    {len(leads)}')
print(f'Verified hotel operators: {len(verified)}')
print(f'Primary contacts (post-group): {len(primary)}')
print(f'With outreach email draft: {len(with_draft)}')
print(f'outreach_approved=TRUE:  {len(approved)}')
"
