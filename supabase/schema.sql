-- COMPANIES
CREATE TABLE companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  domain TEXT,
  industry TEXT DEFAULT 'hospitality',
  size_estimate TEXT, -- '5-20 properties', '20-100 properties', etc.
  hq_country TEXT,
  linkedin_url TEXT,
  website TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- LEADS (CLIENT TRACK)
CREATE TABLE leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID REFERENCES companies(id),
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  title TEXT,
  email TEXT,
  linkedin_url TEXT,
  phone TEXT,
  location TEXT,
  -- Pipeline state
  pipeline_stage TEXT DEFAULT 'discovered',
  -- discovered | enriched | review_queue | approved | contacted | replied | meeting_booked | met | follow_up | closed_won | closed_lost
  lead_score INTEGER DEFAULT 0, -- 0-100
  warmth TEXT DEFAULT 'cold', -- cold | warm | hot
  -- Research
  enrichment_data JSONB, -- raw enrichment from Claude
  personalisation_hooks TEXT[], -- specific hooks for outreach
  pain_signals TEXT[], -- observed pain signals
  -- Outreach
  outreach_email_1 TEXT, -- generated draft
  outreach_email_2 TEXT,
  outreach_approved BOOLEAN DEFAULT FALSE,
  -- Sequence tracking
  sequence_step INTEGER DEFAULT 0,
  last_contacted_at TIMESTAMPTZ,
  next_action_at TIMESTAMPTZ,
  -- Meta
  source TEXT, -- 'phantombuster_linkedin' | 'apollo' | 'manual' | 'itb_list'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- INVESTOR TARGETS (PRE-SEEDED FROM 50-TARGET LIST)
CREATE TABLE investor_targets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  firm_name TEXT NOT NULL,
  investor_type TEXT, -- 'seed_vc' | 'pre_seed' | 'accelerator' | 'cvc' | 'angel'
  tier INTEGER, -- 1-6 from the outreach playbook
  contact_name TEXT, -- specific partner to approach
  contact_email TEXT,
  contact_linkedin TEXT,
  why_fit TEXT, -- from the investor target document
  check_size_range TEXT,
  intake_form_url TEXT,
  -- Pipeline state
  pipeline_stage TEXT DEFAULT 'identified',
  -- identified | research_needed | ready_to_contact | contacted | replied | meeting_booked | met | term_sheet | closed | pass
  liam_leads BOOLEAN DEFAULT FALSE, -- true if Liam should lead outreach (Tier 1, 5, some 6)
  warm_path TEXT, -- description of warm intro path if exists
  -- Outreach
  outreach_draft TEXT,
  outreach_approved BOOLEAN DEFAULT FALSE,
  sequence_step INTEGER DEFAULT 0,
  last_contacted_at TIMESTAMPTZ,
  next_action_at TIMESTAMPTZ,
  -- Meta
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- MEETINGS
CREATE TABLE meetings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  investor_id UUID REFERENCES investor_targets(id),
  track TEXT NOT NULL, -- 'client' | 'investor'
  scheduled_at TIMESTAMPTZ,
  duration_minutes INTEGER DEFAULT 20,
  slot_number INTEGER, -- 1, 2, or 3 (10:30, 10:50, 11:10)
  cal_event_id TEXT, -- from Cal.com
  google_event_id TEXT,
  status TEXT DEFAULT 'scheduled', -- scheduled | completed | cancelled | no_show
  -- Pre-meeting
  briefing_sent BOOLEAN DEFAULT FALSE,
  briefing_content TEXT,
  -- Post-meeting
  voice_feedback_raw TEXT, -- transcribed Telegram voice note
  feedback_summary TEXT, -- Claude-processed summary
  outcome TEXT, -- 'hot' | 'warm' | 'cold' | 'dead' | 'won'
  next_action TEXT,
  next_action_at TIMESTAMPTZ,
  follow_up_draft TEXT,
  follow_up_sent BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- EMAIL SEQUENCES
CREATE TABLE email_sequences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  investor_id UUID REFERENCES investor_targets(id),
  track TEXT NOT NULL,
  step_number INTEGER NOT NULL, -- 1, 2, 3
  step_type TEXT, -- 'email' | 'linkedin_touch' | 'follow_up'
  subject TEXT,
  body TEXT,
  scheduled_for TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  status TEXT DEFAULT 'pending', -- pending | sent | replied | bounced | skipped
  gmail_message_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- VOICE COMMANDS LOG
CREATE TABLE voice_commands (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_message_id TEXT,
  raw_transcript TEXT,
  parsed_intent TEXT, -- JSON string of parsed intent
  action_taken TEXT,
  status TEXT DEFAULT 'processed', -- processed | failed | pending_confirmation
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- SYSTEM CONFIG
CREATE TABLE system_config (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default config
INSERT INTO system_config (key, value) VALUES
  ('meeting_slot_1', '10:30'),
  ('meeting_slot_2', '10:50'),
  ('meeting_slot_3', '11:10'),
  ('operator_email', 'liam@firstwaveai.com'),
  ('operator_timezone', 'Europe/Berlin'),
  ('review_mode_client', 'manual'),
  ('review_mode_investor', 'manual'),
  ('client_outreach_approved_count', '0'),
  ('investor_outreach_approved_count', '0'),
  ('daily_discovery_limit', '20');
