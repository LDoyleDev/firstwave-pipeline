# FIRSTWAVE PIPELINE — SYSTEM CONTEXT & FOUNDATION
> Hand this document to Claude Code at the start of every session.
> It defines the project purpose, architecture, data models, and context rules.
> For agent system prompts, load docs/FIRSTWAVE_PROMPTS.md separately (Phase 2+).

---

## 1. PROJECT OVERVIEW

**Product being sold**: First Wave AI — a human + AI omnichannel customer care and sales coaching platform, purpose-built for hospitality. Not a chatbot. A hybrid model: domain-trained AI paired with human quality assurance across phone, chat, email, SMS, and WhatsApp.

**Tagline**: *People + AI™ | Built for Hospitality. Never Miss a Guest. Never Lose a Lead.*

**Key proof points** (use in all outreach):
- 21% of hotel calls go unanswered today
- 16x cheaper than traditional live agents
- 4.6x faster guest resolution
- 5,817 staff minutes saved per pilot property
- $2,496 direct cost savings per month in pilot
- GM quote: *"First Wave AI acted as the first layer of interaction with our customers, handling calls around the clock, night and day."*

**Raise**: $750K seed at $6M pre-money valuation. 18-month runway to $500K ARR.

**This system's purpose**: Automate the discovery, enrichment, outreach, scheduling, and follow-up pipeline for two parallel sales tracks — client acquisition and investor fundraising — operated by Liam Doyle via voice commands through Telegram.

---

## 2. OPERATOR PROFILE

**Name**: Liam Doyle
**Role**: Advisor, Hospitality Strategy & Operations at First Wave AI
**Credibility**: Former COO at Selina and A&O Hotels & Hostels. Deep European hospitality operator network. Attended ITB Berlin 2026.
**Email**: liam@firstwaveai.com
**Meeting window**: 10:30–11:30 daily — three 20-minute slots at 10:30, 10:50, 11:10
**Location**: Berlin, Germany
**Voice interface**: Telegram bot (voice notes → Groq Whisper → Claude intent parser)
**Primary device**: Ubuntu 24.04 desktop + mobile via Tailscale

---

## 3. TWO PIPELINE TRACKS

### Track A — CLIENT PIPELINE

**Goal**: Book demo meetings with hospitality decision-makers at hotel groups, resort portfolios, and management companies.

**Ideal Customer Profile (ICP)**:
- Title: CEO, CMO, Chief Sales Officer, VP Revenue, VP Guest Experience, Director of CX, General Manager (multi-property groups)
- Company: Hotel groups with 5+ properties, resort portfolios, hospitality management companies, boutique hotel chains
- Geography: Priority 1 — DACH, UK, Benelux, Nordics (Liam's network); Priority 2 — US, rest of Europe
- Size: 5–500 properties (enterprise handled separately)
- Signals: Recent job postings for CX roles, OTA dependency mentions, expansion news, complaints about staff turnover

**Pain points to target**:
1. 1 in 5 inbound calls goes unanswered → lost bookings to OTA or competitor
2. OTA commission bleed (15–30% per booking)
3. Staff turnover destroying training investment
4. Inconsistent guest experience across properties

**Sales methodology**: Challenger Sale — lead with a specific insight about their pain, not product features. Never pitch in email 1. Goal of email 1 is a 20-minute call, nothing more.

---

### Track B — INVESTOR PIPELINE

**Goal**: Secure meetings with VCs, seed funds, and angel investors to close $750K seed round.

**50 pre-built target list** (stored in Supabase `investor_targets` table, pre-seeded):
- Tier 1: Hospitality & Travel Tech VCs (Derive Ventures, Thayer Ventures, Branded Hospitality, Journey Ventures, Jaws Ventures, JetBlue Technology Ventures, MairDuMont Ventures, Fifth Wall, Howzat Partners, Big Rock Ventures)
- Tier 2: Vertical AI / B2B SaaS Pre-Seed (Outlander VC, Ascend VC, Pear VC, Amplify Partners, Audacious VC, 2048 Ventures, Forum Ventures, Precursor Ventures, Founder Collective, Beta Boom)
- Tier 3: Accelerators (Y Combinator, Techstars, 500 Global, a16z START, NFX)
- Tier 4: Enterprise AI / CX (First Round Capital, SaaStr Fund, Salesforce Ventures, HubSpot Ventures, FirstMark Capital, Glasswing Ventures, Lerer Hippeau, White Star Capital, HOF Capital, Trinity Ventures)
- Tier 5: European (Seedcamp, Heartcore Capital, Playfair Capital, Earlybird Ventures, Partech, Icebreaker.vc, TheVentureCity, Stride.VC)
- Tier 6: Angels (Ryan Hoover, Gokul Rajaram, AngelList Hospitality Syndicates, Alumni Ventures, Golden Seeds, Regional Angel Networks, Launch Capital)

**Pitch arc** (embed in all investor outreach):
1. Pain: Hotels haemorrhage revenue on unanswered calls and OTA commissions
2. Why now: AI is finally capable enough — but only with human domain oversight
3. Why us: AWS infrastructure expertise (Philip) + hospitality operator credibility (Liam) + live pilot proof
4. Why this beats alternatives: Generic chatbots destroy brand voice; outsourcing destroys culture; we're the only hybrid model purpose-built for hospitality
5. Ask: $750K to reach $500K ARR in 18 months. $6M pre-money.

**Outreach approach by tier**:
- Tier 1 (Hospitality VCs): Liam leads. Open with operator credibility. Reference their portfolio. Curiosity framing, not pitch.
- Tier 2 (Vertical AI): Lead with market insight + traction numbers. Apply through intake forms AND warm intro simultaneously.
- Tier 3 (Accelerators): Philip leads applications. Liam referenced as domain credibility.
- Tier 5 (European): Liam leads person-to-person. Not via formal pitch process.
- Tier 6 (Angels): Direct, respectful one-liner. Twitter/X or LinkedIn.

**Golden rule**: First message aims for a 20-minute call. Never attach a deck to cold email 1.

---

## 4. TECHNOLOGY STACK

```
Frontend:     React + Vite (dev: vybe-desktop:5173 · prod: Vercel)
Backend:      Python 3.12 + FastAPI (port 8001 on vybe-pi, uvicorn --host ::)
Database:     Supabase (PostgreSQL, free tier)
AI:           Claude Max OAuth token — Sonnet for generation, Haiku for classification
              (token read from ~/.claude/.credentials.json — no API key; Claude Code must be installed + authed on Pi)
Transcription: Groq Whisper API
Voice:        Telegram Bot (python-telegram-bot) → Groq → Claude intent parser
Email:        Gmail API via OAuth2 (liam@firstwaveai.com — Google Workspace)
Calendar:     Google Calendar API via OAuth2
Scheduling:   Cal.com free tier (API access included, custom availability slots)
Lead data:    Apollo.io free tier (email enrichment) + PhantomBuster free tier (LinkedIn scraping)
Automation:   n8n on vybe-pi (port 5678, n8n.service) — workflows target http://localhost:8001
Hosting:      vybe-pi (always-on, Cloudflare Tunnel → firstwave.vybe-dev.com); vybe-desktop for dev
              Tailscale IPs: desktop 100.113.88.92, Pi 100.108.149.115
              CI/CD: GitHub Actions runner on Pi, auto-restarts firstwave-backend on push to main
```

---

## 5. SUPABASE SCHEMA

```sql
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
  ('review_mode_client', 'manual'), -- manual until first 20 approved, then auto
  ('review_mode_investor', 'manual'),
  ('client_outreach_approved_count', '0'),
  ('investor_outreach_approved_count', '0'),
  ('daily_discovery_limit', '20');
```

---

## 6. SYSTEM PROMPTS

All six system prompts are in a separate file to keep this document lean:
**→ docs/FIRSTWAVE_PROMPTS.md**

Load that file only when working on agent tasks (Phase 2 onwards).
Prompts covered: Enrichment Agent, Client Outreach, Investor Outreach,
Telegram Intent Parser, Follow-Up Agent, Pre-Meeting Briefing Agent.

---

## 7. SEQUENCE CADENCE

### Client Sequence
```
Day 0:  Email 1 (Challenger Sale opener) — sent after approval
Day 3:  LinkedIn connection request (manual reminder sent via Telegram)
Day 7:  Email 2 (follow-up with new data point) — auto-sent if no reply
Day 14: Final touch — short "closing the loop" email, or archive
```

### Investor Sequence
```
Day 0:  Email 1 (curiosity/insight opener) — sent after approval
Day 3:  LinkedIn connection request (manual reminder via Telegram)
Day 7:  Email 2 (traction update or new proof point)
Day 14: Final touch — "closing the round" urgency note, or archive
```

---

## 8. CONTEXT OPTIMISATION RULES

These rules govern how Claude Code should approach building this system:

1. **Every API call to Claude should include the relevant system prompt from docs/FIRSTWAVE_PROMPTS.md** — never call the API without context.

2. **Lead enrichment runs in batches of 5** — do not enrich more than 5 leads per API call to manage costs and rate limits.

3. **Outreach generation is per-lead** — never generate batch outreach. Each email must use the specific enrichment data for that lead.

4. **Review queue is blocking** — no outreach email is ever sent without explicit approval. The `outreach_approved` flag must be TRUE in Supabase before the Gmail send is triggered.

5. **Voice commands confirm before executing destructive actions** — sending emails, cancelling meetings. Informational actions (check pipeline, get briefing) execute immediately.

6. **Supabase is the single source of truth** — n8n workflows and the FastAPI backend must always write state to Supabase. Never rely on in-memory state for pipeline data.

7. **Haiku for classification, Sonnet for generation** — use `claude-haiku-4-5-20251001` for intent parsing and lead scoring. Use `claude-sonnet-4-20250514` for enrichment, outreach generation, and briefings.

8. **Groq Whisper for all transcription** — do not use any other transcription service. Groq is already configured on the operator's machine.

9. **Meeting slots are sacred** — 10:30, 10:50, and 11:10 are the only bookable slots. The system must enforce this. No other times should be offered.

10. **Two-track separation** — client and investor pipelines share the database and voice interface but have completely separate outreach logic, system prompts, and approval flows. Never mix messaging between tracks.

---

## 9. ENVIRONMENT VARIABLES

The following must be present in `.env`:

```
# Anthropic
ANTHROPIC_API_KEY=

# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Groq
GROQ_API_KEY=

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_OPERATOR_CHAT_ID=  # Liam's personal chat ID for the bot

# Gmail / Google
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=  # for liam@firstwaveai.com
GMAIL_SENDER_EMAIL=liam@firstwaveai.com

# Cal.com
CALCOM_API_KEY=
CALCOM_EVENT_TYPE_ID=  # the 20-minute meeting event type

# Apollo.io
APOLLO_API_KEY=

# PhantomBuster
PHANTOMBUSTER_API_KEY=

# App
APP_ENV=development
APP_PORT=8000
FRONTEND_PORT=5173
OPERATOR_TIMEZONE=Europe/Berlin
```

---

## 10. FILE STRUCTURE

```
firstwave-pipeline/
├── .env
├── .env.example
├── README.md
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── requirements.txt
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── enrichment.py          # Lead enrichment agent
│   │   ├── outreach.py            # Outreach generation (client + investor)
│   │   ├── followup.py            # Post-meeting follow-up agent
│   │   ├── briefing.py            # Pre-meeting briefing agent
│   │   └── intent_parser.py       # Telegram voice command parser
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── supabase_client.py
│   │   ├── gmail_client.py        # Gmail API wrapper
│   │   ├── calendar_client.py     # Google Calendar API wrapper
│   │   ├── telegram_bot.py        # Telegram bot handler
│   │   ├── groq_client.py         # Whisper transcription
│   │   ├── calcom_client.py       # Cal.com scheduling API
│   │   ├── apollo_client.py       # Apollo.io enrichment
│   │   └── phantombuster_client.py
│   ├── prompts/
│   │   └── system_prompts.py      # All system prompts from docs/FIRSTWAVE_PROMPTS.md
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── leads.py               # Lead CRUD + pipeline actions
│   │   ├── investors.py           # Investor CRUD + pipeline actions
│   │   ├── meetings.py            # Meeting management
│   │   ├── sequences.py           # Email sequence management
│   │   └── voice.py               # Telegram webhook endpoint
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── index.css
│       ├── components/
│       │   ├── PipelineBoard.jsx  # Kanban pipeline view
│       │   ├── LeadCard.jsx
│       │   ├── ReviewQueue.jsx    # Outreach approval UI
│       │   ├── MeetingSlots.jsx   # Today's 3 meeting slots
│       │   └── VoiceLog.jsx       # Recent voice commands log
│       └── pages/
│           ├── Dashboard.jsx      # Overview: pipeline health, today's meetings
│           ├── Clients.jsx        # Client pipeline kanban
│           ├── Investors.jsx      # Investor pipeline kanban
│           ├── Meetings.jsx       # Calendar view + briefings
│           └── Settings.jsx       # Config management
├── supabase/
│   ├── schema.sql                 # Full schema from Section 5
│   └── seed_investors.sql         # Pre-seed 50-target list
├── n8n-workflows/
│   ├── sequence_scheduler.json    # Daily sequence execution
│   ├── meeting_briefing.json      # 30-min pre-meeting briefing trigger
│   └── follow_up_executor.json    # Post-meeting follow-up execution
└── docs/
    ├── FIRSTWAVE_SYSTEM_CONTEXT.md  # Architecture, schema, rules (this file)
    ├── FIRSTWAVE_PROMPTS.md         # All 6 Claude agent system prompts
    ├── FIRSTWAVE_BUILD_PHASES.md    # Phased build plan
    └── FIRSTWAVE_SETUP_GUIDE.md     # Account setup instructions
```
