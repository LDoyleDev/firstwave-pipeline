# FirstWave Pipeline — Work Log

---

## 2026-04-23 — Raspberry Pi Deployment + Auto-Deploy

### Built
- `start.sh` — wrapper script that sources `.env` and starts uvicorn on port 8002; bypasses systemd EnvironmentFile parsing quirks
- `/etc/systemd/system/firstwave-api.service` — systemd service using `start.sh` as ExecStart; runs as user `vybe`; Restart=always
- nginx config on Pi — port 3001 serving `frontend/dist/`, `/api/` proxied to FastAPI on 8002
- Cloudflare Tunnel config updated to route `firstwave.vybe-dev.com` to `localhost:3001`
- `.github/workflows/deploy.yml` — GitHub Actions workflow using self-hosted runner on Pi; triggers on push to main; pulls, rebuilds frontend, restarts API
- Self-hosted GitHub Actions runner installed on Pi (`~/actions-runner`), running as systemd service

### Key issues resolved
- Port conflict: APP_PORT=8000 in `.env` was overriding `--port 8002` arg (uvicorn reads env var); fixed by wrapper script using `exec` with explicit `--port 8002` on one line
- nginx 500: `www-data` couldn't traverse `/home/vybe/` — fixed with `chmod o+x` on home, project, frontend, and dist directories
- GitHub PAT missing `workflow` scope — regenerated token with `repo` + `workflow` scopes

### Validation
| Check | Result |
|-------|--------|
| `curl http://localhost:8002/health` (Pi) | `{"status":"ok"}` ✓ |
| `curl http://localhost:3001` (Pi) | 200 ✓ |
| GitHub Actions deploy | success ✓ |

---

## 2026-04-23 — Phase 7: Seed Data + Final Polish

### Built
- `scripts/update_investor_contacts.py` — populated all 50 investor_targets records with:
  - `contact_name`: specific partner names for all 50 firms (e.g. Reshma Sohoni / Seedcamp, Brendan Wallace / Fifth Wall, Charles Hudson / Precursor)
  - `check_size_range`: typical check size for each fund
  - `warm_path`: personalised warm-path notes for all Tier 1, Tier 5, and key Tier 6 angels (20 total) describing how Liam's Selina/A&O background + Berlin location connects to each fund's thesis
- `README.md` — full operator documentation:
  - How to start backend + frontend (single commands)
  - Daily workflow description (morning review → meeting window → discovery)
  - All voice commands with examples
  - How to add leads manually (API + discovery run)
  - How to approve outreach (browser + API + auto-mode at 20 approvals)
  - Pipeline status check commands
  - n8n workflow import table
  - Troubleshooting guide (5 common failure modes with fix commands)
  - Full environment variables reference
- Verified Tailscale access: http://100.113.88.92:5173 (frontend bound to 0.0.0.0 in vite.config.js)
- Verified FastAPI binds to 0.0.0.0 (pass `--host 0.0.0.0` to uvicorn)

### Validation
| Check | Result |
|-------|--------|
| `pytest backend/tests/ -v` | 46/46 passed ✓ |
| Backend imports | ✓ |
| DB connection | ✓ |
| Investor contacts populated | 50/50 ✓ |
| warm_path coverage | 20/50 (all Tier 1 + Tier 5 + key Tier 6) ✓ |
| Tailscale IP | 100.113.88.92 ✓ |
| Frontend build | ✓ clean (984KB) |

### All phases complete
- Phase 1: Foundation (schema, API, routers)
- Phase 2: AI Agents (enrichment, outreach, intent parser, followup, briefing)
- Phase 3: Integrations (Gmail, Calendar, Telegram, Groq, Cal.com, Apollo, PhantomBuster)
- Phase 4: Outreach Engine (discovery, review queue, sequence executor, reply detection, n8n)
- Phase 5: Scheduling + Meeting Flow (booking, briefings, post-meeting feedback loop)
- Phase 6: Frontend Dashboard (React, 7 pages, Kanban, dark theme)
- Phase 7: Seed Data + Polish (investor contacts, warm paths, README)

---

## 2026-04-23 — Phase 5: Scheduling + Meeting Flow

### Built
- `backend/routers/meetings.py` — added 3 new endpoints:
  - `GET /meetings/upcoming-briefings`: queries meetings within 35 min with briefing_sent=false; calls `generate_briefing()` for each, sends via Telegram, marks briefing_sent=true; called by n8n every 10 min
  - `GET /meetings/completed-pending-feedback`: finds meetings that ended 20+ min ago with no voice feedback; sends Telegram prompt, updates status to 'completed'; called by n8n every 5 min
  - `POST /meetings/{id}/confirm-followup`: sends stored follow_up_draft via Gmail, marks follow_up_sent=true, updates pipeline stage
  - Top-level `send_email` import added (was local import)
- `backend/agents/intent_parser.py` — upgraded 4 handlers from stubs to full implementations:
  - `_handle_book_meeting`: resolves date/slot from natural language, looks up attendee in DB, creates Cal.com booking + Google Calendar event + Supabase meeting record, sends Telegram confirmation
  - `_handle_pre_meeting_briefing`: queries next scheduled meeting and returns details
  - `_handle_post_meeting_feedback`: finds most recent completed meeting, calls `generate_followup()`, sends draft to Telegram with YES confirmation prompt
  - `_handle_send_followup`: finds most recent meeting with draft but follow_up_sent=false, sends via Gmail, updates stage
  - Module-level imports for calcom_client, calendar_client, gmail_client, telegram_bot
- `n8n-workflows/meeting_briefing.json` — filled stub with real workflow: cron every 10 min → GET /meetings/upcoming-briefings
- `n8n-workflows/post_meeting_prompt.json` — new workflow: cron every 5 min → GET /meetings/completed-pending-feedback
- `backend/tests/test_phase5.py` — 10 tests covering all new endpoints and intent handlers

### Validation
| Check | Result |
|-------|--------|
| `pytest backend/tests/ -v` | 46/46 passed ✓ (36 existing + 10 Phase 5) |
| Backend imports | ✓ |
| DB connection | ✓ |

### Known issues / notes
- `_handle_book_meeting` falls back gracefully when Cal.com / Google Calendar credentials are missing — meeting is still created in Supabase
- `_handle_post_meeting_feedback` auto-selects the most recent completed meeting — edge case if two meetings close together; operator can use `/meetings/{id}/feedback` directly if needed
- Python 3.12 deprecation warning for `asyncio.get_event_loop()` in intent handlers (no event loop in test context) — harmless, will resolve when running under ASGI

### Next
Phase 7 — Seed Data + Final Polish (investor seed data, Tailscale access confirmation, end-to-end smoke test, README)

---

## 2026-04-23 — Phase 4: Outreach Engine

### Built
- `backend/agents/sequence_executor.py` — `schedule_sequence(entity_id, track)`: creates 3 email steps (Day 0, 7, 14) + 1 LinkedIn touch (Day 3) as Telegram notification; `process_due_sequences()`: queries pending sequences due now, sends via Gmail, updates records, marks replied entities as skipped; `check_all_replies()`: checks Gmail for replies, flips stage to 'replied', pauses remaining steps, sends Telegram alert
- `backend/routers/sequences.py` (full implementation) — `GET /review-queue`: split client/investor, ordered by lead_score/tier; `POST /review-queue/{id}/approve`: sets outreach_approved, increments system_config counter, flips to auto mode at 20 approvals, schedules sequence; `POST /review-queue/{id}/reject`: closes as closed_lost/pass; `POST /review-queue/{id}/edit`: inline draft edit without approving; `POST /sequences/process`: runs process_due_sequences(); `POST /sequences/check-replies`: runs check_all_replies(); `GET /sequences`: list with filters
- `backend/routers/discovery.py` — `POST /discovery/run`: supports apollo/phantombuster/manual sources, deduplicates by linkedin_url+email, creates leads, triggers enrichment+outreach, sends Telegram notification; `POST /discovery/phantombuster-launch`: launches daily PhantomBuster scraper (called by n8n at 06:00)
- `backend/main.py` — registered discovery router; sequences router now uses no prefix (owns /review-queue/* and /sequences/*)
- `n8n-workflows/sequence_scheduler.json` — full n8n workflow: cron at 08:00 daily → POST /sequences/process
- `n8n-workflows/reply_checker.json` — full n8n workflow: cron every 2h → POST /sequences/check-replies
- `n8n-workflows/phantombuster_launcher.json` — full n8n workflow: cron at 06:00 daily → POST /discovery/phantombuster-launch
- `backend/tests/test_phase4.py` — 10 tests covering review queue CRUD, sequence processing, discovery endpoint, sequence_executor unit tests

### Validation
| Check | Result |
|-------|--------|
| `pytest backend/tests/ -v` | 36/36 passed ✓ (26 existing + 10 Phase 4) |
| Backend imports | ✓ |
| DB connection | ✓ |

### Known issues / notes
- `PHANTOMBUSTER_DEFAULT_SEARCH_URL` must be set in `.env` before `POST /discovery/phantombuster-launch` will work
- Gmail send in `process_due_sequences()` requires valid Google OAuth credentials in `.env` (GOOGLE_REFRESH_TOKEN etc.)
- Investor discovery only supports 'manual' source — investor list is pre-seeded; Apollo/PhantomBuster reserved for client track
- n8n workflows use `localhost:8000` — ensure FastAPI is running before activating workflows

### Next
Phase 5 — Scheduling + Meeting Flow (meeting booking via voice, pre-meeting briefing trigger, post-meeting feedback loop)

---

## 2026-04-23 — Phase 3: Integrations

### Built
- `backend/integrations/groq_client.py` — `transcribe_audio(audio_bytes, filename)`: Groq Whisper large-v3; supports OGG/WAV/MP3/M4A/WEBM; handles both object and string response formats
- `backend/integrations/telegram_bot.py` — `Application` with 6 handlers (`/start`, `/pipeline`, `/review`, `/next`, voice, text); `process_webhook_update(data)` for FastAPI webhook; `send_operator_message()` for outbound notifications; operator-only guard on all handlers
- `backend/integrations/gmail_client.py` — `send_email(to, subject, body, reply_to_message_id)` → gmail_message_id; `check_replies(sequence_ids)` → list of {replied: bool, reply_snippet}; OAuth2 via GOOGLE_REFRESH_TOKEN; plain-text only
- `backend/integrations/calendar_client.py` — `create_event()` → google_event_id; `cancel_event()` → bool; `get_todays_events()` → events in 10:30–11:30 block; same OAuth2 credentials as Gmail
- `backend/integrations/calcom_client.py` — `get_available_slots(date)`, `create_booking(slot_time, name, email, notes)`, `cancel_booking(cal_event_id)`; parses CALCOM_EVENT_TYPE_ID URL to extract username+slug; lazy-fetches numeric event type ID and caches it
- `backend/integrations/apollo_client.py` — `find_person_email(first, last, domain)` → email|None; `search_leads(titles, industry, geography, limit)` → list; 2s rate-limit delay between requests
- `backend/integrations/phantombuster_client.py` — `launch_linkedin_search_scraper(url, limit)` → container_id; `get_scraper_results(container_id)` → list; polls every 10s up to 2min; parses both JSON and CSV output formats
- `backend/routers/voice.py` — `POST /webhook/telegram` (Telegram webhook, always 200); `POST /voice/feedback` (multipart: meeting_id + audio → transcript + follow-up draft)
- `backend/main.py` — Removed `/webhook` prefix from voice router; paths now defined in router directly
- `backend/tests/test_integrations.py` — 14 tests covering all 7 integrations + webhook endpoint (all mocked)
- `requirements.txt` — Pinned `httpx>=0.27.0,<0.28.0` to resolve python-telegram-bot 20.7 / httpx 0.28 incompatibility (proxies kwarg removed in 0.28)

### Validation
| Check | Result |
|-------|--------|
| `pytest backend/tests/ -v` | 26/26 passed ✓ (12 agent + 14 integration) |
| Backend imports | ✓ |
| DB connection | ✓ |

### Known issues / notes
- `LINKEDIN_SESSION_COOKIE` not yet in `.env` — required for PhantomBuster to authenticate LinkedIn; set before first scraper launch
- Cal.com event type numeric ID is resolved lazily on first booking; if API shape differs, set `CALCOM_EVENT_TYPE_NUMERIC_ID` manually
- Telegram webhook URL must be registered with Telegram: `POST https://api.telegram.org/bot{TOKEN}/setWebhook?url=https://{your-domain}/webhook/telegram`
- Google credentials use refresh token flow — no interactive OAuth needed

### Next
Phase 4 — Outreach Engine (discovery, review queue, sequence executor, reply detection, n8n workflows)

---

## 2026-04-23 — Phase 2: AI Agents

### Built
- `backend/utils/anthropic_client.py` — `generate()` (Sonnet) + `classify()` (Haiku), exponential backoff retry (max 3 attempts), handles RateLimitError / APIConnectionError / APIError
- `backend/agents/enrichment.py` — `enrich_lead(lead_data)` + `enrich_batch(lead_ids, max=5)`: calls Sonnet with ENRICHMENT_SYSTEM_PROMPT, parses JSON, updates lead record in Supabase (enrichment_data, lead_score, warmth, pain_signals, personalisation_hooks, stage → 'enriched')
- `backend/agents/outreach.py` — `generate_client_outreach(lead_id)`, `generate_investor_outreach(investor_id)`, `regenerate_with_feedback(entity_id, track, feedback)`: stores drafts, sets pipeline_stage to 'review_queue' / 'ready_to_contact'
- `backend/agents/intent_parser.py` — `parse_voice_intent(transcript)` (Haiku), `route_intent(intent)` with 15 intent handlers; logs all commands to voice_commands table; always returns valid JSON (fallback to check_pipeline on parse error)
- `backend/agents/followup.py` — `generate_followup(meeting_id, feedback_text)`: outcome classification (hot/warm/cold/dead), next_action with auto-calculated timing, follow_up_draft; updates meeting record + schedules step 3 email sequence
- `backend/agents/briefing.py` — `generate_briefing(meeting_id)`: fetches lead/investor profile, generates Telegram-formatted briefing (<300 words), stores in meeting.briefing_content, marks briefing_sent=True
- `backend/routers/leads.py` — Added `POST /leads/{id}/enrich` + `POST /leads/enrich-batch`
- `backend/routers/meetings.py` — Added `POST /meetings/{id}/briefing` + `POST /meetings/{id}/feedback`
- `backend/tests/test_agents.py` — 12 tests covering all 6 agents (mocked Anthropic + Supabase)

### Validation
| Check | Result |
|-------|--------|
| `pytest backend/tests/test_agents.py -v` | 12/12 passed ✓ |
| Backend imports | ✓ |

### Known issues / notes
- Agents require ANTHROPIC_API_KEY in .env (now set)
- `pytest` added to venv (`pip install pytest`)
- Intent router's complex actions (book_meeting, enrich_lead by name) return guidance messages directing to the correct REST endpoint — full automation wires in Phase 3/4/5

### Next
Phase 3 — Integrations (Groq Whisper, Telegram bot, Gmail, Google Calendar, Cal.com, Apollo, PhantomBuster)

---

## 2026-04-23 — Phase 6: Frontend Dashboard

### Built
- Full React + Vite frontend with 7 pages: Dashboard, Clients (Kanban), Investors (Table), Review Queue, Meetings (Week view), Analytics (Charts), Voice Log
- Tailwind CSS v3 dark theme: navy (#0f1117) / charcoal (#1a1d2e) / electric blue (#2563eb) palette matching Bloomberg Terminal spec
- shadcn-style UI primitives: Card, Badge, Button, Input, Sheet (slide-over), Dialog, Skeleton
- Data layer: Supabase JS client for reads (works everywhere); FastAPI calls for writes (dev only)
- Real-time updates via Supabase Realtime subscriptions (auto-invalidates React Query cache)
- `PasswordGate.jsx` — password protects entire app; auto-bypasses on localhost and Tailscale IPs
- `AppShell` with persistent sidebar (active state, review queue badge count), live Berlin clock in topbar
- `MeetingSlotsPanel` — hero component showing today's 3 slots (booked/available/past + outcome badges)
- KPI cards: Review Queue, Active in Sequence, Replies This Week, Meetings This Week
- `PipelineHealthBar` — clickable stage-count bars for both tracks
- `ActivityFeed` — last 10 events merged from leads/investors/meetings, 30s refresh
- `KanbanBoard` — full @dnd-kit drag-and-drop across 11 client stages; PATCH on drop
- `LeadDetailSheet` / `InvestorDetailSheet` — slide-over profile panels
- `InvestorTable` — grouped by tier with TierGroup collapsible sections, liam_leads indicator
- `ReviewCard` — inline approve/reject/edit (read-only mode warning in production)
- `WeekView` — 7-column calendar grid for the 10:30–11:30 meeting block
- 4 Recharts charts: ConversionFunnel, ReplyRateChart (weekly trend), InvestorTierCoverage (stacked bars), MeetingOutcomesChart (donut)
- `frontend/vercel.json` — ready for Vercel deployment (SPA rewrites configured)
- `frontend/.env` — Supabase anon key pre-filled; access password `firstwave2026`

### Validation
| Check | Result |
|-------|--------|
| `npm run build` | ✓ clean (984KB bundle) |
| All 7 routes HTTP 200 | ✓ |
| Backend imports | ✓ |
| DB connection | ✓ |

### Known issues / notes
- inotify watcher limit on this machine — use `CHOKIDAR_USEPOLLING=1 npm run dev` (documented in CLAUDE.md)
- Bundle is 984KB (Recharts adds ~400KB) — not an issue for a private operator tool; could code-split later
- Supabase RLS policies for anon read access must be applied before Vercel deployment (SQL in plan file)
- `frontend/.env` is gitignored — copy values to Vercel environment variables before deploying

### Next
Phase 2 — AI Agents (enrichment, outreach generation, intent parser, follow-up, briefing)

---

## 2026-04-23 — Phase 1: Foundation

### Built
- Full directory scaffold matching FIRSTWAVE_SYSTEM_CONTEXT.md Section 10
- `requirements.txt` with all Phase 1–3 dependencies; pinned `supabase>=2.28.3` (required for new `sb_secret_` key format)
- `.env.example` with all variables; appended missing defaults to `.env` (GMAIL_SENDER_EMAIL, APP_ENV, APP_PORT, FRONTEND_PORT, OPERATOR_TIMEZONE)
- `backend/main.py` — FastAPI app with CORS middleware, `/health` endpoint, all routers registered
- `backend/integrations/supabase_client.py` — initialised with SUPABASE_SERVICE_ROLE_KEY, exports `supabase` singleton and `test_connection()`
- `backend/prompts/system_prompts.py` — all 6 agent system prompts as Python string constants (Enrichment, Client Outreach, Investor Outreach, Intent Parser, Follow-Up, Briefing)
- `backend/routers/leads.py` — GET list (filter by stage), GET single, POST create, PATCH update
- `backend/routers/investors.py` — GET list (filter by tier + stage), GET single, PATCH update
- `backend/routers/meetings.py` — GET list (filter by date), GET /today (3-slot structure), POST create (slot enforcement), PATCH update
- `supabase/schema.sql` — complete schema (companies, leads, investor_targets, meetings, email_sequences, voice_commands, system_config)
- `supabase/seed_investors.sql` — SQL version of all 50 investor targets
- `scripts/seed_investors.py` — Python seed script (idempotent); run successfully, 50 rows live in Supabase
- Stub files for all Phase 2/3 agents, integrations, frontend components, and n8n workflows
- `frontend/vite.config.js` — binds to `0.0.0.0` for Tailscale access

### Validation results
| Endpoint | Result |
|----------|--------|
| GET /health | `{"status": "ok"}` ✓ |
| GET /leads | `[]` ✓ |
| GET /investors | 50 rows ✓ |
| GET /meetings/today | 3 slots (10:30, 10:50, 11:10) ✓ |

### Known issues / notes
- `ANTHROPIC_API_KEY` is blank in `.env` — must be filled in before starting Phase 2
- `python-telegram-bot==20.7` has an httpx version conflict with supabase 2.28.x — no impact until Phase 3 (Telegram integration); resolve then by pinning compatible httpx

### Next
Phase 2 — AI Agents (enrichment, outreach, intent parser, follow-up, briefing agents)
