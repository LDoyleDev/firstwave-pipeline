#!/usr/bin/env bash
# Email-sourcing Tier 3 — run INSIDE the 21:00-22:00 UTC vybe-trading LLM window.
#
# Sources the `pending_confirm` leads left by the earlier Tier 1+2 run (website
# scrape + Haiku opt-out-disclaimer confirm), then audits the result. Idempotent
# and resumable — safe to re-run. All output goes to data/phase2/tier3_run.log.
#
# Schedule it for tonight (23:03 Berlin = 21:03 UTC) with:
#   systemd-run --user --on-calendar='2026-05-21 23:03:00' \
#     --unit=fw-email-tier3 /bin/bash <path-to-this-script>
set -u
cd "$(cd "$(dirname "$0")" && pwd)/.." || exit 1

LOG=data/phase2/tier3_run.log
mkdir -p data/phase2
{
  echo "=== Tier 3 sourcing run — started $(date -u +%FT%TZ) ==="
  PYTHONPATH=. venv/bin/python3 scripts/source_emails.py
  echo
  echo "=== verify — $(date -u +%FT%TZ) ==="
  PYTHONPATH=. venv/bin/python3 scripts/verify_email_sourcing.py
  echo "=== finished $(date -u +%FT%TZ) ==="
} > "$LOG" 2>&1
