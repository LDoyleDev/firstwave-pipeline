# FIRSTWAVE PIPELINE — BUILD PHASES
> Hand this document to Claude Code alongside FIRSTWAVE_SYSTEM_CONTEXT.md.
> It defines exactly what to build in each phase, in order.

---

## BEFORE YOU START — RULES FOR CLAUDE CODE

1. Always read `FIRSTWAVE_SYSTEM_CONTEXT.md` before generating any code in this project.
2. Use the exact system prompts defined in Section 6 of that document. Do not paraphrase or shorten them.
3. Use the exact Supabase schema from Section 5. Do not invent new table structures.
4. Every agent that calls the Anthropic API must use `claude-sonnet-4-20250514` for generation and `claude-haiku-4-5-20251001` for classification, as defined in Context Optimisation Rule 7.
5. All environment variables come from `.env`. Never hardcode credentials.
6. Write Python with type hints throughout.
7. Every FastAPI endpoint must have a docstring explaining its purpose.
8. After each phase, confirm that all tests pass before proceeding to the next phase.

---

## PHASE 1 — FOUNDATION
**Goal**: Project skeleton, database, and basic API running locally.
**Estimated time**: 1-2 days
**Start here**: `mkdir firstwave-pipeline && cd firstwave-pipeline`

### Tasks

**1.1 Project initialisation**
```
Create the full file structure as defined in FIRSTWAVE_SYSTEM_CONTEXT.md Section 10.
Create .env.example with all variables from Section 9 (empty values).
Create requirements.txt with:
  fastapi
  uvicorn[standard]
  python-dotenv
  supabase
  anthropic
  groq
  python-telegram-bot==20.7
  google-auth
  google-auth-oauthlib
  google-auth-httplib2
  google-api-python-client
  httpx
  pydantic
  python-multipart
Create backend/main.py as a FastAPI app with health check endpoint GET /health.
Create backend/prompts/system_prompts.py containing all 6 system prompts from 
FIRSTWAVE_SYSTEM_CONTEXT.md Section 6 as Python string constants.
```

**1.2 Supabase client**
```
Create backend/integrations/supabase_client.py.
Initialise Supabase client using SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from .env.
Export a single supabase client instance.
Include a test_connection() function that queries system_config and returns True/False.
```

**1.3 Database schema**
```
Create supabase/schema.sql with the complete schema from FIRSTWAVE_SYSTEM_CONTEXT.md Section 5.
Create supabase/seed_investors.sql that inserts all 50 investor targets from the 
investor target list in FIRSTWAVE_SYSTEM_CONTEXT.md Section 3 (Track B).
Include all fields: firm_name, investor_type, tier, why_fit, liam_leads (true for Tier 1, 5, 6).
```

**1.4 Basic routers**
```
Create backend/routers/leads.py with:
  GET /leads — list leads with optional filter by pipeline_stage
  GET /leads/{id} — get single lead
  POST /leads — create lead manually
  PATCH /leads/{id} — update lead (stage, score, notes)
  
Create backend/routers/investors.py with:
  GET /investors — list investors with optional filter by tier, stage
  GET /investors/{id} — get single investor
  PATCH /investors/{id} — update investor

Create backend/routers/meetings.py with:
  GET /meetings — list meetings, optional filter by date
  GET /meetings/today — today's three slots with lead/investor details
  POST /meetings — create meeting
  PATCH /meetings/{id} — update meeting (status, outcome, feedback)

Register all routers in main.py.
```

**1.5 Phase 1 validation**
```
Run: uvicorn backend.main:app --reload --port 8000
Test: curl http://localhost:8000/health → {"status": "ok"}
Test: GET /leads → empty array
Test: GET /investors → 50 rows (seeded)
Test: GET /meetings/today → three slot objects for next working day
```

---

## PHASE 2 — AI AGENTS
**Goal**: All six Claude-powered agents working as callable Python functions.
**Estimated time**: 2-3 days
**Prerequisite**: Phase 1 complete, ANTHROPIC_API_KEY in .env

### Tasks

**2.1 Anthropic base client**
```
Create backend/utils/anthropic_client.py.
Two functions:
  generate(system_prompt: str, user_message: str, model: str = "claude-sonnet-4-20250514") -> str
  classify(system_prompt: str, user_message: str) -> str  # uses haiku model
Both functions handle API errors gracefully with retry (max 3 attempts, exponential backoff).
```

**2.2 Enrichment agent** (`backend/agents/enrichment.py`)
```
Function: enrich_lead(lead_data: dict) -> dict
- Takes: first_name, last_name, title, company, linkedin_url, company_website
- Calls Claude Sonnet with ENRICHMENT_SYSTEM_PROMPT
- Returns parsed JSON matching the enrichment output schema in system prompt
- Updates lead record in Supabase with enrichment_data, lead_score, warmth, pain_signals, personalisation_hooks
- Handles JSON parse errors gracefully

Function: enrich_batch(lead_ids: list[str]) -> list[dict]
- Enriches up to 5 leads in sequence (not parallel — rate limit protection)
- Returns list of enrichment results
```

**2.3 Outreach generation agent** (`backend/agents/outreach.py`)
```
Function: generate_client_outreach(lead_id: str) -> dict
- Fetches lead + enrichment data from Supabase
- Calls Claude Sonnet with CLIENT_OUTREACH_SYSTEM_PROMPT
- Generates email_1 subject, email_1 body, email_2 subject, email_2 body
- Stores drafts in lead record (outreach_email_1, outreach_email_2)
- Sets pipeline_stage to 'review_queue'
- Returns the draft object

Function: generate_investor_outreach(investor_id: str) -> dict
- Same pattern using INVESTOR_OUTREACH_SYSTEM_PROMPT
- Generates outreach_draft in investor_targets record
- Sets pipeline_stage to 'ready_to_contact' after stage 'research_needed'

Function: regenerate_with_feedback(entity_id: str, track: str, feedback: str) -> dict
- Takes existing draft + human feedback
- Regenerates the outreach incorporating the feedback
- Updates the record
```

**2.4 Intent parser agent** (`backend/agents/intent_parser.py`)
```
Function: parse_voice_intent(transcript: str) -> dict
- Calls Claude Haiku with INTENT_PARSER_SYSTEM_PROMPT
- Returns parsed JSON intent object
- Always returns valid JSON even if confidence is low
- Logs to voice_commands table in Supabase

Function: route_intent(intent: dict) -> dict
- Takes parsed intent and routes to the correct action
- Returns action result + confirmation message for Telegram
```

**2.5 Follow-up agent** (`backend/agents/followup.py`)
```
Function: generate_followup(meeting_id: str, feedback_text: str) -> dict
- Fetches meeting + lead/investor data from Supabase
- Calls Claude Sonnet with FOLLOWUP_SYSTEM_PROMPT
- Returns: outcome classification, next_action, next_action_at, follow_up_draft
- Updates meeting record with all fields
- Schedules follow-up in email_sequences table
```

**2.6 Pre-meeting briefing agent** (`backend/agents/briefing.py`)
```
Function: generate_briefing(meeting_id: str) -> str
- Fetches meeting + lead/investor full profile from Supabase
- Calls Claude Sonnet with BRIEFING_SYSTEM_PROMPT
- Returns formatted briefing text (Telegram-formatted, under 300 words)
- Stores in meeting.briefing_content
- Marks meeting.briefing_sent = true after delivery
```

**2.7 Phase 2 validation**
```
Create backend/tests/test_agents.py with:
  test_enrichment_agent() — mock lead data → valid enrichment JSON returned
  test_client_outreach() — lead with enrichment → email draft generated
  test_investor_outreach() — investor target → outreach draft generated
  test_intent_parser() — 5 sample voice transcripts → correct intents returned
  test_followup() — meeting feedback → outcome + draft generated
Run: python -m pytest backend/tests/test_agents.py -v
```

---

## PHASE 3 — INTEGRATIONS
**Goal**: Gmail, Google Calendar, Groq Whisper, Cal.com, and Telegram bot all connected.
**Estimated time**: 3-4 days
**Prerequisites**: All API credentials in .env

### Tasks

**3.1 Groq transcription** (`backend/integrations/groq_client.py`)
```
Function: transcribe_audio(audio_bytes: bytes, filename: str) -> str
- Calls Groq Whisper API (model: whisper-large-v3)
- Returns transcript text
- Handles file format conversion if needed (OGG from Telegram → WAV)
Install: pip install pydub (for audio conversion)
```

**3.2 Telegram bot** (`backend/integrations/telegram_bot.py`)
```
Set up python-telegram-bot with webhook mode (not polling — webhook is more reliable).
Webhook URL: POST /webhook/telegram registered in FastAPI

Handlers:
  /start — send welcome message with command list
  /pipeline — trigger check_pipeline intent
  /review — show review queue
  /next — show next meeting briefing
  voice_message_handler — receive voice note, transcribe via Groq, parse intent, execute action, reply with result

All responses to operator only (check TELEGRAM_OPERATOR_CHAT_ID).
Format all outgoing messages for mobile (short lines, clear sections, emoji sparingly).
```

**3.3 Gmail client** (`backend/integrations/gmail_client.py`)
```
OAuth2 setup for liam@firstwaveai.com using GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN.

Functions:
  send_email(to: str, subject: str, body: str, reply_to_message_id: str = None) -> str
    Returns gmail_message_id
  check_replies(sequence_ids: list[str]) -> list[dict]
    Checks if any emails in active sequences have received replies
    Returns list of {sequence_id, replied: bool, reply_snippet}

Notes:
  - Always send as liam@firstwaveai.com
  - Store gmail_message_id in email_sequences table after send
  - Plain text emails only (no HTML) — keeps deliverability high
```

**3.4 Google Calendar client** (`backend/integrations/calendar_client.py`)
```
OAuth2 using same Google credentials.

Functions:
  create_event(title: str, start_time: datetime, duration_minutes: int, 
               attendee_email: str, description: str) -> str
    Returns google_event_id
  cancel_event(google_event_id: str) -> bool
  get_todays_events() -> list[dict]
    Returns events in the 10:30-11:30 block for today
```

**3.5 Cal.com client** (`backend/integrations/calcom_client.py`)
```
REST API client using CALCOM_API_KEY.

Functions:
  get_available_slots(date: str) -> list[dict]
    Returns available slots for the given date (should only return 10:30, 10:50, 11:10)
  create_booking(slot_time: str, attendee_name: str, attendee_email: str, 
                 notes: str) -> dict
    Returns booking details including cal_event_id
  cancel_booking(cal_event_id: str) -> bool

Configure Cal.com availability to ONLY allow slots at 10:30, 10:50, 11:10 
in Europe/Berlin timezone. Maximum 3 bookings per day.
```

**3.6 Apollo client** (`backend/integrations/apollo_client.py`)
```
Functions:
  find_person_email(first_name: str, last_name: str, company_domain: str) -> str | None
    Returns email if found, None if not (free tier, respects rate limits)
  search_leads(job_titles: list[str], industry: str, min_employees: int, 
               geography: list[str], limit: int = 20) -> list[dict]
    Returns list of prospect objects
Rate limit: add 2-second delay between requests. Cache results in Supabase.
```

**3.7 PhantomBuster client** (`backend/integrations/phantombuster_client.py`)
```
Functions:
  launch_linkedin_search_scraper(search_url: str, limit: int = 25) -> str
    Launches a PhantomBuster agent, returns launch_id
  get_scraper_results(launch_id: str) -> list[dict]
    Polls for results, returns leads list
  Note: PhantomBuster free tier = 10 minutes/day execution. 
  Schedule phantom launches for 06:00 daily via n8n to preserve the quota.
```

**3.8 Voice router** (`backend/routers/voice.py`)
```
POST /webhook/telegram — receives Telegram updates
- Verifies request is from Telegram
- Extracts voice note or text command
- Calls transcribe_audio() if voice
- Calls parse_voice_intent()
- Calls route_intent()
- Sends result back to operator via Telegram

POST /voice/feedback — receives post-meeting voice feedback
- Takes meeting_id + audio bytes
- Transcribes + generates follow-up
- Returns follow-up draft for approval
```

**3.9 Phase 3 validation**
```
Test Telegram: Send voice note "What's my pipeline status?" → receive formatted reply
Test Gmail: Send test email to a test address → confirm delivery
Test Calendar: Create test event → confirm in Google Calendar
Test Cal.com: Check available slots → only 10:30, 10:50, 11:10 returned
Test Groq: Send sample audio file → receive accurate transcript
```

---

## PHASE 4 — OUTREACH ENGINE + SEQUENCE MANAGEMENT
**Goal**: Full outreach pipeline from lead → enrichment → review → send → sequence execution.
**Estimated time**: 2-3 days

### Tasks

**4.1 Discovery workflow endpoint**
```
POST /discovery/run
- Accepts: track ('client'|'investor'), source ('apollo'|'phantombuster'|'manual'), 
           filters (title, geography, company_size)
- For client track: calls Apollo or PhantomBuster to fetch leads
- Deduplicates against existing Supabase records (check linkedin_url and email)
- Creates lead records in 'discovered' stage
- Triggers enrichment for each new lead
- Triggers outreach generation after enrichment
- Sends Telegram notification: "Found X new leads, Y added to review queue"
- Returns summary
```

**4.2 Review queue endpoints**
```
GET /review-queue — returns all leads/investors with outreach_approved = false, 
                    ordered by lead_score desc, split by track

POST /review-queue/{id}/approve
- Sets outreach_approved = true
- Increments system_config count (client_outreach_approved_count or investor)
- If count reaches 20: set review_mode to 'auto' for that track
- Schedules email sequence step 1 for immediate send
- Sends Telegram confirmation

POST /review-queue/{id}/reject
- Sets pipeline_stage = 'closed_lost', notes = 'rejected in review'
- Sends Telegram confirmation

POST /review-queue/{id}/edit
- Takes new_subject, new_body
- Updates outreach_email_1 in record
- Does NOT auto-approve — still requires explicit approval
```

**4.3 Sequence executor**
```
Create backend/agents/sequence_executor.py

Function: process_due_sequences() -> dict
- Queries email_sequences where status='pending' AND scheduled_for <= NOW()
- For each due sequence:
  - Checks lead/investor record: if reply received, skip and mark sequence complete
  - Sends email via Gmail client
  - Updates sequence record: sent_at, status='sent', gmail_message_id
  - Schedules next sequence step
- Returns count of sequences processed

Function: schedule_sequence(entity_id: str, track: str) -> None
- Creates email_sequences records for steps 1, 2, 3 with correct timing:
  Client: Day 0 (email 1), Day 7 (email 2), Day 14 (final touch)
  Investor: Day 0 (email 1), Day 7 (email 2), Day 14 (final touch)
- Day 3 LinkedIn reminder created as a Telegram notification (not an email)
```

**4.4 Reply detection**
```
Function: check_all_replies() -> None
- Runs every 2 hours (triggered by n8n)
- For all active sequences: calls gmail_client.check_replies()
- If reply detected:
  - Updates lead/investor pipeline_stage to 'replied'
  - Pauses remaining sequence steps
  - Sends Telegram notification: "Reply from [Name] at [Company] — check your inbox"
```

**4.5 n8n workflows**
```
Create n8n-workflows/sequence_scheduler.json:
  Trigger: Cron, every day at 08:00
  Action: POST http://localhost:8000/sequences/process
  
Create n8n-workflows/reply_checker.json:
  Trigger: Cron, every 2 hours
  Action: POST http://localhost:8000/sequences/check-replies

Create n8n-workflows/phantombuster_launcher.json:
  Trigger: Cron, daily at 06:00
  Action: POST http://localhost:8000/discovery/phantombuster-launch
  (Launches LinkedIn scraper using PhantomBuster free quota before the day begins)

All n8n workflows call the local FastAPI server at localhost:8000.
```

**4.6 Phase 4 validation**
```
Full end-to-end test:
1. POST /discovery/run with track='client', source='manual', 1 test lead
2. Check review queue: outreach draft present
3. POST /review-queue/{id}/approve
4. Check email_sequences: step 1 scheduled for now
5. POST /sequences/process
6. Confirm email sent (check Gmail sent folder)
7. Confirm Telegram notification received
```

---

## PHASE 5 — SCHEDULING + MEETING FLOW
**Goal**: Meeting booking, pre-meeting briefing, post-meeting feedback loop.
**Estimated time**: 2 days

### Tasks

**5.1 Meeting booking via voice**
```
When intent_parser returns intent='book_meeting':
  - Get available Cal.com slots for requested date
  - If attendee known (lead/investor in DB): use their email
  - Create Cal.com booking
  - Create Google Calendar event
  - Create Supabase meeting record
  - Send confirmation via Telegram: "Meeting booked: [Name] at 10:30 on [Date]"
  - Schedule briefing trigger 30 minutes before meeting
```

**5.2 Pre-meeting briefing trigger**
```
n8n workflow: meeting_briefing.json
  Trigger: Cron, every 10 minutes
  Action: GET http://localhost:8000/meetings/upcoming-briefings
  
GET /meetings/upcoming-briefings:
  - Returns meetings where scheduled_at is within 35 minutes from now
  - AND briefing_sent = false
  
For each: 
  - generate_briefing(meeting_id)
  - Send via Telegram
  - Mark briefing_sent = true
```

**5.3 Post-meeting feedback via Telegram voice**
```
After a meeting slot time passes:
  n8n detects completed meeting (scheduled_at + 20 minutes has passed)
  Sends Telegram prompt: "How did the meeting with [Name] go? Send a voice note."
  
When operator sends voice reply:
  Intent parser detects 'post_meeting_feedback'
  Calls generate_followup(meeting_id, feedback_text)
  Sends Telegram: "Got it. Here's your follow-up draft: [draft]. Send it? Reply YES to confirm."
  
On YES confirmation:
  Sends follow-up email via Gmail
  Updates meeting record: follow_up_sent = true
  Updates lead/investor pipeline_stage based on outcome
```

**5.4 Dashboard meeting view endpoint**
```
GET /meetings/today:
  Returns:
  {
    "date": "2026-04-22",
    "slots": [
      {"slot": 1, "time": "10:30", "meeting": {...} | null},
      {"slot": 2, "time": "10:50", "meeting": {...} | null},
      {"slot": 3, "time": "11:10", "meeting": {...} | null}
    ],
    "available_slots": 2
  }
```

---

## PHASE 6 — FRONTEND DASHBOARD
**Goal**: React webapp accessible via Tailscale for pipeline visibility.
**Estimated time**: 3-4 days
**Note**: Claude Code should read /mnt/skills/public/frontend-design/SKILL.md before building the frontend.

### Design Direction
```
Aesthetic: Refined dark dashboard — think Bloomberg Terminal meets modern SaaS.
Dark navy/charcoal base (#0f1117, #1a1d2e), electric blue accents (#2563eb), 
white text hierarchy. Monospace font for data, clean sans-serif for labels.
No gradients, no purple. Sharp, high-information density. Operator tool, not marketing site.
```

### Pages to build

**6.1 Dashboard (/)** 
```
Today's 3 meeting slots (prominent, top of page) — empty slots vs booked
Pipeline health summary: 
  Client: X leads in review / Y in sequence / Z replied
  Investor: A targets in review / B in sequence / C replied
Recent activity feed (last 10 actions)
Quick action buttons: "Run Discovery", "Open Review Queue", "Check Pipeline"
```

**6.2 Review Queue (/review)**
```
Split view: Client queue (left) | Investor queue (right)
Each card shows: Name, Title, Company, Lead Score badge, Pain Signals tags
Expand to see: Full enrichment data, Email 1 draft, Email 2 draft
Actions per card: Approve (green), Reject (red), Edit (pencil → inline editor)
Keyboard shortcuts: A = approve, R = reject, E = edit, → next card
Show count: "12 pending approvals (8 client, 4 investor)"
```

**6.3 Client Pipeline (/clients)**
```
Kanban board: discovered → enriched → review → approved → contacted → replied → meeting_booked → met → follow_up → won/lost
Each card: Name, Company, Lead Score, Days in stage
Click card: full profile sidebar (enrichment data, sequence status, all emails sent)
Filter by: Stage, Score, Geography, Source
```

**6.4 Investor Pipeline (/investors)**
```
Table view (not kanban — investors are fewer, more data per row):
Columns: Tier, Firm, Type, Contact, Stage, Why Fit, Liam Leads (Y/N), Last Action, Next Action
Click row: full profile with outreach draft, warm path notes
Filter by: Tier, Stage, Liam Leads
Group by: Tier (default)
```

**6.5 Meetings (/meetings)**
```
Week view: shows the 10:30-11:30 block for each day
Today highlighted
Each slot shows: booked (with name/company) or "Available"
Click booked slot: shows briefing content + outcome (if past)
Click available slot: "Book manually" form
Past meetings: show outcome badge (hot/warm/cold/dead), follow-up status
```

**6.6 Voice Log (/voice)**
```
Recent voice commands: timestamp, transcript, parsed intent, action taken, status
Useful for debugging and reviewing what the system understood
```

**6.7 Frontend API connection**
```
Create frontend/src/api.js — all API calls to http://localhost:8000
Use React Query for data fetching and caching
WebSocket or polling (every 30s) for live updates to review queue and pipeline counts
```

---

## PHASE 7 — INVESTOR SEED DATA + FINAL POLISH
**Goal**: All 50 investor targets loaded, system tested end-to-end, Tailscale access confirmed.
**Estimated time**: 1 day

### Tasks

**7.1 Investor seed data**
```
Populate supabase/seed_investors.sql with all 50 targets from 
FIRSTWAVE_SYSTEM_CONTEXT.md Section 3 (Track B) with:
  - All fields populated
  - liam_leads = TRUE for: all Tier 1, all Tier 5, all Tier 6
  - contact_name populated where known (research and fill in specific partner names)
  - warm_path notes for Tier 1 where Liam's network applies
Run seed against Supabase.
```

**7.2 Tailscale access**
```
Ensure frontend Vite dev server binds to 0.0.0.0 not just localhost:
  In vite.config.js: server: { host: '0.0.0.0', port: 5173 }
Ensure FastAPI binds to 0.0.0.0:
  uvicorn backend.main:app --host 0.0.0.0 --port 8000
Access from mobile: http://[tailscale-ip]:5173
```

**7.3 End-to-end smoke test**
```
1. Voice command: "Find me 5 hotel group CMOs in Germany" 
   → Discovery runs → Leads created → Enriched → Added to review queue → Telegram notification
2. Open /review in browser → Approve 3 leads
3. Sequences scheduled → Run sequence processor → Emails sent
4. Voice command: "Book a client meeting tomorrow in slot 1"
   → Cal.com booking created → Google Calendar event created → Briefing scheduled
5. At 30 min before meeting: briefing arrives via Telegram
6. After meeting: Telegram prompt → Voice feedback → Follow-up drafted → Approved → Sent
```

**7.4 Process documentation**
```
Create README.md with:
  - How to start the system (single command)
  - Daily workflow description
  - All voice commands with examples
  - How to add new leads manually
  - How to check pipeline status
  - Troubleshooting common issues
```

---

## PHASE ORDER SUMMARY

```
Phase 1 (1-2 days):  Foundation — skeleton, DB schema, basic API
Phase 2 (2-3 days):  AI Agents — all 6 Claude-powered agents
Phase 3 (3-4 days):  Integrations — Gmail, Calendar, Telegram, Groq, Cal.com
Phase 4 (2-3 days):  Outreach Engine — discovery → review → sequence → send
Phase 5 (2 days):    Scheduling + Meeting Flow — booking, briefing, feedback loop
Phase 6 (3-4 days):  Frontend Dashboard — React webapp
Phase 7 (1 day):     Seed Data + Polish + End-to-end test

Total estimate: 14-19 days of Claude Code sessions
```

---

## OPENING PROMPT FOR EACH CLAUDE CODE SESSION

Start every new Claude Code session with this prompt:

```
We are building the First Wave AI Pipeline system — a voice-controlled B2B sales 
automation tool for two tracks: client acquisition and investor fundraising for 
a hospitality AI startup.

Read these two files before doing anything:
1. docs/FIRSTWAVE_SYSTEM_CONTEXT.md — project overview, schema, system prompts, rules
2. docs/FIRSTWAVE_BUILD_PHASES.md — what to build in each phase

We are currently on Phase [X]. 
Today's task: [specific task from the phase].

Ask me to clarify anything before writing code.
```
