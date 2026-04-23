# FirstWave Pipeline — Claude Code Context

## What this project is
A voice-controlled B2B sales automation system for First Wave AI.
Two tracks: client acquisition (hospitality operators) and investor fundraising.
Operator: Liam Doyle, liam@firstwaveai.com, Berlin.
Meeting window: 10:30, 10:50, 11:10 Europe/Berlin only.

## Stack
- Backend: Python 3.11 + FastAPI (port 8000)
- Frontend: React + Vite (port 5173)
- Database: Supabase (PostgreSQL) — single source of truth
- AI: Anthropic API — Sonnet for generation, Haiku for classification
- Voice: Telegram bot + Groq Whisper transcription
- Automation: n8n (localhost:5678)
- Remote access: Tailscale

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

## Current phase
CURRENT PHASE: 1 — Foundation
(Update this line at the start of each new phase session)
