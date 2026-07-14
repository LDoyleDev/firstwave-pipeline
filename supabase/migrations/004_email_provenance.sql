-- Run this in the Supabase SQL editor. Idempotent — safe to re-run.
-- Email-sourcing provenance: the defensible audit trail behind every sourced
-- address. GDPR Art 14 (source disclosure) + legitimate-interest balancing, and
-- CASL / Spam-Act "conspicuous publication" implied consent all require showing
-- WHERE and WHEN an address was obtained and that the publication carried no
-- "no unsolicited email" statement. The compliance layer (migration 002) records
-- only the source CATEGORY; this adds the full evidence bundle.

BEGIN;

-- Append-only audit log — one row per sourcing event. Never updated in place;
-- a re-source of the same lead appends a new row, preserving history.
CREATE TABLE IF NOT EXISTS email_provenance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  email TEXT NOT NULL,
  email_source TEXT NOT NULL,             -- website_published | osm_tag | apollo | manual
  email_address_type TEXT,                -- generic_role | named_individual
  source_url TEXT,                        -- exact page URL / OSM element permalink
  source_page_title TEXT,
  context_snippet TEXT,                   -- text surrounding the address on that page
  robots_allowed BOOLEAN,                 -- robots.txt permitted the fetch
  optout_disclaimer_seen BOOLEAN DEFAULT FALSE,  -- a no-unsolicited-email statement was present
  disclaimer_check_method TEXT,           -- phrase_list | phrase_list+haiku | none
  html_sha256 TEXT,                       -- sha256 of the retained HTML snapshot
  snapshot_path TEXT,                     -- path to the gzipped HTML evidence file
  jurisdiction_route TEXT,                -- A | B | C at capture time
  captured_at TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_email_provenance_lead ON email_provenance (lead_id);

-- Backend-only table — RLS on, no policies (the service-role key bypasses RLS).
-- Same pattern as suppression_list in 002_compliance_layer.sql.
ALTER TABLE email_provenance ENABLE ROW LEVEL SECURITY;

-- Denormalised latest-provenance summary on the lead, for fast per-lead lookup
-- without joining the audit log. Mirrors the newest email_provenance row.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_provenance JSONB;

COMMIT;

-- Verify after running:
--   SELECT to_regclass('email_provenance');                    -- expect 'email_provenance'
--   SELECT relrowsecurity FROM pg_class WHERE relname = 'email_provenance';  -- expect true
--   SELECT column_name FROM information_schema.columns
--    WHERE table_name = 'leads' AND column_name = 'email_provenance';        -- expect 1 row
