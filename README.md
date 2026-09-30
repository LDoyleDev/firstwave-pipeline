# FirstWave Pipeline

> **Status: retired.** This system ran in production from April to September 2026
> and has been decommissioned. Nothing here is running, and the hosted database
> that held its records has been deleted. The code is published as a record of
> the work.

A B2B sales-automation pipeline for a hospitality-focused AI product: sourcing
hotel-operator leads, enriching them with an LLM, drafting outreach for human
approval, and driving the whole thing from a Telegram voice interface. Two
parallel tracks — client acquisition and investor fundraising.

Built solo. Deployed on a Raspberry Pi 5 behind a Cloudflare Tunnel, with a
React dashboard on Vercel and Supabase (PostgreSQL) as the single source of
truth. Python 3.12 / FastAPI backend, n8n for scheduled automation.

## What's worth looking at

- **Compliance-first email sourcing** — `scripts/source_emails.py`,
  `backend/integrations/provenance.py`, `website_fetch.py`. A tiered,
  near-zero-token pipeline that honours `robots.txt`, writes an append-only
  provenance record for every address it finds (source URL, page title, context
  snippet, retained HTML-snapshot SHA-256, jurisdiction route, captured-at), and
  suppresses any address discovered on a page that restricts unsolicited email.
- **Schema-wide row-level security** — `supabase/migrations/003_schema_wide_rls.sql`.
  Per-role policies across every table, replacing a client-side password gate
  with real Supabase Auth; browser writes blocked by default-deny.
- **Send-path suppression and unsubscribe** — `002_compliance_layer.sql`,
  `backend/routers/compliance.py`. Jurisdiction gates, `List-Unsubscribe`
  headers, bounce detection, an append-only suppression list.
- **Local-first LLM routing** — Ollama first, cloud models only as fallback,
  with a Redis circuit breaker coordinating a shared account across projects.
- **Deterministic pipeline glue** — SHA1 dedup on name+address+city, non-LLM
  screening gates, and research runs that are resumable and parallel-sliceable
  (`scripts/research_decision_makers.py`).

## What was removed before publication

Stated plainly, so it's clear what you won't find:

- **Five "Phase 2 regional scrapers."** Four were scaffolding whose hardcoded
  target lists were placeholder domains — they never produced usable output. The
  fifth scraped two OTA sites whose terms prohibit it. Removed from the full
  commit history, not only from the current tree.
- **A draft Legitimate Interest Assessment.** It carried an explicit
  "must be reviewed by qualified data-protection counsel before it is relied on"
  status and was never relied on — no outreach was ever sent from this pipeline.
  An unreviewed legal self-assessment is not something worth publishing.
- **Live infrastructure identifiers** — tunnel UUID, internal network addresses,
  and the public hostnames of unrelated services on the same host.

The historical `docs/WORK_LOG.md` entries describing this work are annotated
rather than deleted, so the record of what was built stays honest.

## Data protection

No personal data is in this repository or its history:

- Scraped lead records lived in `data/` and in the hosted database. Neither was
  ever tracked by git — verified across all commits.
- The hosted Supabase project holding the lead records has been deleted.
- `scripts/sample_leads.json` is a fully synthetic fixture: names use the local
  word for "example", telephone numbers use the fictional `555-01xx` range and
  are not dialable, and websites use `example.com`, which IANA reserves for
  documentation.
- Secret scanning (`gitleaks`) across the complete history reports no findings,
  and `.env` was never committed.

## Repository layout

| Path | What's in it |
|---|---|
| `backend/` | FastAPI app — routers, agents, integrations, prompts |
| `frontend/` | React + Vite operator dashboard |
| `scripts/` | Sourcing, enrichment, dedup and screening pipeline |
| `supabase/` | Schema and numbered migrations |
| `n8n-workflows/` | Scheduled automation definitions |
| `docs/` | Architecture, build phases, work log, runbooks |

Start with `docs/FIRSTWAVE_SYSTEM_CONTEXT.md` for architecture and schema, and
`docs/WORK_LOG.md` for the session-by-session development record.

## Running it

You can't run this as-is: it depended on a Supabase project, a Telegram bot, an
Ollama host and an n8n instance, none of which exist any more. `.env.example`
lists every variable it expected. The individual pipeline scripts under
`scripts/` are the most legible starting point if you want to read rather than
run.

---

# Operating manual (as it ran in production)

Everything below documents the system as it operated while live. It is kept for
reference and no longer describes anything running.

## Starting the system

The backend runs as a systemd service on **vybe-pi** — you do not start it manually.

**Frontend (dev — vybe-desktop only):**
```bash
cd frontend && CHOKIDAR_USEPOLLING=1 npm run dev
```

**Access:**
| Surface | URL |
|---|---|
| Frontend (dev) | http://localhost:5173 |
| Frontend (Tailscale) | http://<desktop-tailscale-ip>:5173 |
| Backend API (Tailscale) | http://<pi-tailscale-ip>:8001 |
| Backend API (public) | https://firstwave.example.com |
| API docs | https://firstwave.example.com/docs |
| n8n (Tailscale) | http://<pi-tailscale-ip>:5678 |
| Sign-in | shared Supabase Auth operator account (`VITE_AUTH_EMAIL`) |

**Restart backend (if needed — SSH to Pi first):**
```bash
sudo systemctl restart firstwave-backend
```

**Register Telegram webhook** (run once):
```
POST https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url=https://firstwave.example.com/webhook/telegram
```

---

## Daily workflow

**Morning (before 10:30)**
1. Telegram bot sends a pipeline summary automatically (via n8n cron)
2. Open `/review` in browser — approve or reject outreach drafts
3. Approved emails queue for the 08:00 daily send (n8n sequence scheduler)

**During meeting window (10:30–11:30)**
1. Briefing arrives via Telegram 30 minutes before each booked meeting
2. After each meeting slot, Telegram asks "How did it go? Send a voice note."
3. Send a voice note → follow-up draft generated → reply YES to send

**Ongoing discovery**
- Apollo or PhantomBuster runs via n8n at 06:00 daily
- New leads auto-enriched and queued for review
- Reply detection runs every 2 hours → Telegram alert if someone replies

---

## Voice commands

Send any of these as a voice note or text message to the Telegram bot.

| What you say | What happens |
|---|---|
| "What's my pipeline status?" | Summary of all stages across both tracks |
| "Show me the review queue" | Count of pending approvals |
| "Book a client meeting tomorrow in slot one" | Creates Cal.com + Google Calendar booking |
| "Book an investor meeting with Earlybird on Friday in slot two" | Same, but looks up Earlybird contact |
| "That meeting went well, Marcus wants to see a deck" | Generates follow-up draft, asks for YES confirmation |
| "Yes, send it" | Sends the pending follow-up email via Gmail |
| "Find me five hotel CMOs in Germany" | Queues a discovery run via Apollo |
| "Who is Seedcamp?" | Looks up investor in DB, returns contact + why_fit |
| "Pause sequence for Anna Schmidt" | Marks sequence as paused |

**Rule:** Voice commands that send emails always require YES confirmation first.  
Informational queries (pipeline status, review queue, next meeting) execute immediately.

---

## Adding leads manually

**Via API:**
```bash
curl -X POST https://firstwave.example.com/leads \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Anna",
    "last_name": "Schmidt",
    "email": "anna@example.com",
    "title": "CMO",
    "company": "Grand Hotel Group",
    "linkedin_url": "https://linkedin.com/in/annaschmidt",
    "source": "manual"
  }'
```

Then trigger enrichment + outreach:
```bash
curl -X POST https://firstwave.example.com/leads/{id}/enrich
```
The lead moves to `review_queue` after enrichment + outreach generation.

**Via discovery run (bulk):**
```bash
curl -X POST https://firstwave.example.com/discovery/run \
  -H "Content-Type: application/json" \
  -d '{
    "track": "client",
    "source": "apollo",
    "filters": {
      "titles": ["CMO", "VP Revenue", "Chief Sales Officer"],
      "geography": ["Germany", "Austria", "Switzerland"],
      "industry": "hospitality",
      "limit": 20
    }
  }'
```

---

## Approving outreach

**Via browser:** Open http://localhost:5173/review → click Approve / Reject / Edit on each card.

**Via API:**
```bash
# Approve
curl -X POST https://firstwave.example.com/review-queue/{id}/approve \
  -d '{"track": "client"}'

# Reject
curl -X POST https://firstwave.example.com/review-queue/{id}/reject \
  -d '{"track": "client"}'

# Edit then approve
curl -X POST https://firstwave.example.com/review-queue/{id}/edit \
  -d '{"track": "client", "new_subject": "...", "new_body": "...", "email_number": 1}'
```

After 20 approvals on a track, the system flips to `auto` mode and no longer requires manual approval.

---

## Checking pipeline status

```bash
# All leads by stage
curl https://firstwave.example.com/leads

# Today's 3 meeting slots
curl https://firstwave.example.com/meetings/today

# Review queue (split by track)
curl https://firstwave.example.com/review-queue

# Investor pipeline
curl https://firstwave.example.com/investors?tier=1

# Active email sequences
curl https://firstwave.example.com/sequences?status=pending
```

---

## n8n workflows (import via n8n UI)

All workflows are in `n8n-workflows/`. Import each via the n8n UI at http://localhost:5678.

| File | Schedule | Action |
|---|---|---|
| `sequence_scheduler.json` | Daily 08:00 | Sends due email sequences |
| `reply_checker.json` | Every 2 hours | Detects replies, alerts via Telegram |
| `phantombuster_launcher.json` | Daily 06:00 | Launches LinkedIn scraper |
| `meeting_briefing.json` | Every 10 min | Sends pre-meeting briefings |
| `post_meeting_prompt.json` | Every 5 min | Asks for post-meeting feedback |

---

## Troubleshooting

**Backend won't start**
```bash
PYTHONPATH=. venv/bin/python3 -c "from backend.main import app; print('ok')"
PYTHONPATH=. venv/bin/python3 -c "from backend.integrations.supabase_client import test_connection; print(test_connection())"
```

**Frontend won't load (inotify error)**
Always start with `CHOKIDAR_USEPOLLING=1 npm run dev` — this machine has a low inotify limit.

**Telegram bot not responding**
1. Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_OPERATOR_CHAT_ID` in `.env`
2. Verify webhook is registered (see "Starting the system" above)
3. Backend must be reachable from the internet for webhooks to work

**Emails not sending**
1. Check `GOOGLE_REFRESH_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` in `.env`
2. Test: `PYTHONPATH=. venv/bin/python3 -c "from backend.integrations.gmail_client import send_email; print(send_email('test@example.com', 'Test', 'Test body'))"`

**Cal.com booking fails**
1. Check `CALCOM_API_KEY` and `CALCOM_EVENT_TYPE_ID` in `.env`
2. The numeric event type ID is resolved lazily; set `CALCOM_EVENT_TYPE_NUMERIC_ID` manually if API shape differs

**Tests**
```bash
PYTHONPATH=. venv/bin/python3 -m pytest backend/tests/ -v
```
Expected: 46 passed.

---

## Environment variables

Copy `.env.example` to `.env` and fill in all values:

```
# No ANTHROPIC_API_KEY — uses Claude Max OAuth token from ~/.claude/.credentials.json
# Claude Code must be installed and authenticated on vybe-pi
SUPABASE_URL            — Supabase project URL
SUPABASE_SERVICE_ROLE_KEY — Service role key (backend only)
SUPABASE_ANON_KEY       — Anon key (frontend only)
GROQ_API_KEY            — Whisper transcription
TELEGRAM_BOT_TOKEN      — Telegram bot
TELEGRAM_OPERATOR_CHAT_ID — Liam's personal chat ID
GOOGLE_CLIENT_ID        — Gmail + Calendar OAuth
GOOGLE_CLIENT_SECRET
GOOGLE_REFRESH_TOKEN    — for liam@firstwaveai.com
GMAIL_SENDER_EMAIL      — liam@firstwaveai.com
CALCOM_API_KEY          — Cal.com scheduling
CALCOM_EVENT_TYPE_ID    — Full URL: https://cal.com/{username}/{slug}
APOLLO_API_KEY          — Lead discovery
PHANTOMBUSTER_API_KEY   — LinkedIn scraping
PHANTOMBUSTER_DEFAULT_SEARCH_URL — Default LinkedIn search for daily run
```
