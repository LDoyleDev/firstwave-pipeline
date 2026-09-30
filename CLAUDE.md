# FirstWave Pipeline — Claude Code Context

## What this project is
A voice-controlled B2B sales automation system for First Wave AI.
Two tracks: client acquisition (hospitality operators) and investor fundraising.
Operator: Liam Doyle, liam@firstwaveai.com, Berlin.
Meeting window: 10:30, 10:50, 11:10 Europe/Berlin only.

## Stack
- Backend: Python 3.12 + FastAPI
- Frontend: React + Vite (dev: port 5173 · prod: Vercel)
- Database: Supabase (PostgreSQL) — single source of truth
- AI: Ollama first (gpt-oss:20b only) → Claude Max OAuth fallback (read from ~/.claude/.credentials.json)
- Voice: Telegram bot + Groq Whisper transcription
- Automation: n8n (localhost:5678)
- Remote access: Tailscale

## Port map — do not change without updating this table
| Port | Process | Machine | Notes |
|------|---------|---------|-------|
| 8000 | vybe-trading FastAPI (`vybe-backend`) | Pi | DO NOT USE — owned by vybe-trading |
| 8001 | FirstWave FastAPI (`firstwave-backend`) | Pi | production backend |
| 5173 | Vite dev server | Desktop only | dev only, not on Pi |
| 5678 | n8n | Pi | `n8n.service`, basic auth, sqlite at `~/.n8n/database.sqlite` |

## Machines
| Machine | Tailscale IP | Role |
|---------|-------------|------|
| vybe-desktop | <desktop-tailscale-ip> | Dev machine |
| vybe-pi | <pi-tailscale-ip> | Always-on server (firstwave-backend on 8001) |
| surface-pro-3 | <laptop-tailscale-ip> | Travel laptop — dev only, no production services |

## Pi infrastructure
- **Cloudflare Tunnel:** single tunnel (`<TUNNEL-UUID>`) with two ingress rules:
  - `api.example.com` → `localhost:8000` (vybe-trading — do not touch)
  - `firstwave.example.com` → `localhost:8001` (firstwave backend)
  - Config: `~/.cloudflared/config.yml`
- **`firstwave-backend.service`** — canonical backend service (port 8001), CI/CD deployed. Service file lives at `infra/firstwave-backend.service` (committed to repo); `deploy.yml` copies it and runs `daemon-reload` on every deploy. Uvicorn binds `--host 0.0.0.0 --port 8001`. n8n workflow URLs use `http://127.0.0.1:8001` (explicit IPv4 loopback — `localhost` resolves to `::1` in Node and would be refused). Tunnel/Tailscale callers reach the service via IPv4.
- **`firstwave-api.service`** — legacy orphan (was on 8002 via start.sh) — disabled and removed
- **GitHub Actions Runner** (`actions.runner.LDoyleDev-firstwave-pipeline.vybe-pi`) — auto-deploys on push to main, restarts `firstwave-backend`
- **Claude Code** — must be installed on Pi and authenticated with Claude Max account; backend reads OAuth token from `~/.claude/.credentials.json`
- **`n8n.service`** — workflow automation on port 5678, basic-auth protected, sqlite db at `~/.n8n/database.sqlite`; workflow definitions live in `n8n-workflows/` and target `http://localhost:8001`

## Docs — read these before writing any code
- docs/FIRSTWAVE_SYSTEM_CONTEXT.md — architecture, schema, env vars, rules (read every session)
- docs/FIRSTWAVE_BUILD_PHASES.md — phased build plan with exact tasks
- docs/FIRSTWAVE_PROMPTS.md — all 6 Claude agent system prompts (load for Phase 2+ only)

## Key rules — never break these
- All credentials from .env only — never hardcode
- Use SUPABASE_SERVICE_ROLE_KEY in backend — never anon key
- outreach_approved must be TRUE in DB before any email sends
- Meeting slots 10:30, 10:50, 11:10 only — enforce strictly
- Haiku for classification/intent parsing, Sonnet for generation
- Enrich leads in batches of 5 max
- Two-track separation — never mix client and investor messaging
- Type hints on all Python functions

## Session commands
- /compact — use after completing each task within a phase
- /clear — use when starting a new phase
- /cost — check token usage
- /model opusplan — use for complex architecture decisions

## Frontend
- Start: `cd frontend && CHOKIDAR_USEPOLLING=1 npm run dev` (polling required on this machine — inotify limit)
- Build check: `cd frontend && npm run build`
- Access: http://localhost:5173 · sign in with the shared Supabase Auth operator account (email = `VITE_AUTH_EMAIL` in frontend/.env, password set in the Supabase dashboard). RLS requires every session to log in — there is no localhost bypass.
- Tailscale: http://<desktop-tailscale-ip>:5173

## Current phase
CURRENT PHASE: Hotel lead-gen pipeline live (Phase 8) — 1000 leads in Supabase, 514 outreach-approved primaries, 104 with cold-email drafts. See docs/PHASE_2_3_COMPLETION.md + docs/NEXT_LEAD_SOURCES.md.
(Update this line at the start of each new phase session)

## Session end checklist — run this at the end of EVERY session
Do these steps in order before finishing:

1. **Failure check** — run both:
   ```
   PYTHONPATH=. venv/bin/python3 -c "from backend.main import app; print('imports ok')"
   PYTHONPATH=. venv/bin/python3 -c "from backend.integrations.supabase_client import test_connection; print('db:', test_connection())"
   ```

2. **Update docs/WORK_LOG.md** — append an entry with:
   - Date (use today's date from system)
   - Phase number and name
   - Bullet list of what was built/changed this session
   - Any known issues or blockers

3. **Update CLAUDE.md** — change the CURRENT PHASE line to the next phase if the current one is complete

4. **Commit and push**:
   ```
   git add <specific files>   # never `git add -A` — the Pi checkout contains
                              # actions-runner/ with a credentials token
   git status   ← review what's being committed; exclude .env and venv/
   git commit -m "Phase X: <one-line summary>

   - bullet list of what changed"
   git push origin main
   ```

Never commit: .env, venv/, __pycache__, *.pyc, credentials.json (all in .gitignore)
