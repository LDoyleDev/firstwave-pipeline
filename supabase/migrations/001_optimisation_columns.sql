-- Run this in the Supabase SQL editor before deploying the optimisation build.

-- leads.company: denormalised text field used throughout (schema only had company_id FK)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS company TEXT;

-- leads.chatbot_detected: flagged during enrichment via website scrape
ALTER TABLE leads ADD COLUMN IF NOT EXISTS chatbot_detected BOOLEAN DEFAULT FALSE;

-- F1: store reply snippet on the sequence record
ALTER TABLE email_sequences ADD COLUMN IF NOT EXISTS reply_snippet TEXT;

-- G3: pending reply draft on the lead (Telegram YES/EDIT flow)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS pending_reply_draft TEXT;

-- K2: warm intro check flag on investor
ALTER TABLE investor_targets ADD COLUMN IF NOT EXISTS pending_intro_check BOOLEAN DEFAULT FALSE;

-- K3: investor-specific meeting outcome
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS investor_outcome TEXT;

-- L1: subject line pattern tag on sequence records
ALTER TABLE email_sequences ADD COLUMN IF NOT EXISTS subject_pattern TEXT;

-- J1: re-engagement tracking
ALTER TABLE leads ADD COLUMN IF NOT EXISTS reengagement_sent_at TIMESTAMPTZ;

-- I3 / D1: weekly meeting target
INSERT INTO system_config (key, value)
VALUES ('meeting_target_weekly', '8')
ON CONFLICT (key) DO NOTHING;

-- C2: daily send limit (default 20 for warmup week 1-2)
INSERT INTO system_config (key, value)
VALUES ('daily_send_limit', '20')
ON CONFLICT (key) DO NOTHING;

-- A2: raise discovery limit
UPDATE system_config SET value = '500' WHERE key = 'daily_discovery_limit';
