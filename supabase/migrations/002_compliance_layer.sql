-- Run this in the Supabase SQL editor before deploying the email-compliance build.
-- Idempotent — safe to re-run.

-- Suppression list — global, case-insensitive, keyed on EMAIL (not lead_id):
-- the same address can appear on multiple leads and an unsubscribe must be global.
CREATE TABLE IF NOT EXISTS suppression_list (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  reason TEXT NOT NULL,            -- unsubscribe | bounce | complaint | manual
  source_campaign TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
-- Case-insensitive uniqueness: 'Liam@x.com' and 'liam@x.com' are one entry.
CREATE UNIQUE INDEX IF NOT EXISTS idx_suppression_email ON suppression_list (lower(email));

-- Compliance columns on leads.
-- country: normalised ISO 3166-1 alpha-2 (was only buried in free-text `location`).
ALTER TABLE leads ADD COLUMN IF NOT EXISTS country TEXT;
-- email_source: how the address was obtained — website_published | osm_tag | apollo | manual
ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_source TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_sourced_at TIMESTAMPTZ;
-- email_address_type: generic_role (info@, reservations@) | named_individual
ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_address_type TEXT;
-- unsubscribe_token: per-lead opaque token for the one-click unsubscribe link.
-- The DEFAULT backfills every existing row with a distinct UUID on ADD COLUMN.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS unsubscribe_token UUID DEFAULT gen_random_uuid();
-- jurisdiction_route: A | B | C | do_not_send — cached from config/jurisdiction_policy.py.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS jurisdiction_route TEXT;
-- consent_basis: GDPR Art 6 basis. legitimate_interest for cold B2B; consent once obtained.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS consent_basis TEXT DEFAULT 'legitimate_interest';
-- suppressed_at: denormalised convenience flag mirroring suppression_list membership.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS suppressed_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_unsub_token ON leads (unsubscribe_token);

-- Verify after running:
--   SELECT count(*) FROM leads WHERE unsubscribe_token IS NULL;   -- expect 0
--   SELECT to_regclass('suppression_list');                       -- expect 'suppression_list'
