# FirstWave Pipeline — Work Log

---
## 2026-05-19 (evening) — Session: backlog catch-up push + cross-machine sync bootstrap

Brought all three machines (vybe-desktop, surface-pro-3, vybe-pi) onto the same `main` HEAD after a week of unpushed work on vybe-desktop. Bootstrapped a separate `~/.claude-config` sync system (private GitHub repo `LDoyleDev/claude-config`) so memory + slash commands + global `CLAUDE.md` stay in sync across vybe-desktop and SP3 going forward.

### Firstwave changes shipped

- Pushed 10 outgoing commits to `origin/main` — 4 from 2026-05-16 (Phase 1-2 hotel lead-gen foundation, already local) plus 6 new tonight:
  - `chore(gitignore)`: exclude `data/`, `logs/`, `.claude/` pipeline derived artefacts.
  - `docs`: `NEXT_LEAD_SOURCES.md` + `PHASE_2_3_COMPLETION.md`.
  - `feat(lead-gen)`: OSM Overpass scraper, injection-audit, group-consolidate, outreach-score, draft-outreach-emails, enrich_after_hours + post_enrichment_chain runners (11 new scripts).
  - `enhance(scrapers)`: broader country list (Ireland, AU, NZ, Malta, all Nordics + Eastern Europe + Mediterranean), relaxed contact-info gate, `verification_status` moved into `enrichment_data` JSON.
  - `feat(review)`: research section in `ReviewCard.jsx` (decision-maker name, signal URLs, hooks, confidence badge) + `scripts/research_decision_makers.py`.
  - `docs(work-log)`: catch-up entries for 2026-05-16, 2026-05-18 morning + late evening, 2026-05-19 (the OSM scrape + injection audit + post-enrichment chain push).
- All three machines at `3d05361`. Vybe-pi auto-deploy ran via GitHub Actions runner; `firstwave-backend.service` restarted at 21:21:24 CEST, `/health` returns 200.

### Cross-machine Claude scaffold sync (separate `LDoyleDev/claude-config` repo)

- Private GitHub repo holds canonical `CLAUDE.md`, slash commands, home-level memory, and per-project memory. Repo paths strip the per-user `-home-{user}-` slug prefix so the same project maps to one repo path regardless of whether the local user is `vybe` or `liam`.
- `/wrap` step 7 now invokes `~/.claude-config/scripts/sync-out.sh` to push at session end (mirror with `--delete`, commit + push).
- `UserPromptSubmit` hook installed in `~/.claude/settings.json` on both dev machines, calling `sync-in.sh --once-per-session` at session start (additive — never deletes local files, marker-gated to once per session).
- Merged divergent home memory: SP3's 12 files + vybe-desktop's 18 files union'd to 28 (only `feedback_no_coauthor.md` overlapped; kept SP3's more-detailed version). `CLAUDE.md` union'd to the 153-line superset.
- Round-trip test confirmed: SP3 write → `sync-out` → repo → `sync-in` on vybe-desktop → file landed. Documented in `~/.claude-config/README.md`.

### Outstanding

- `CLAUDE.md` "CURRENT PHASE" updated this session — was stale since the lead-gen initiative started 2026-05-16.
- Vybe-pi has 3 untracked legacy files at repo root (`actions-runner/`, `deploy.sh`, `start.sh`) — gitignore or remove in a future session.
- France + Denmark OSM coverage still zero (504 Gateway Timeouts on single-country queries); region-bbox backfill pending — see memory `feedback-overpass-country-split`.
- Next operational step is reviewing the 104 cold-email drafts via the `/review-queue` frontend or direct Supabase.

---
## 2026-05-19 — Session: Post-enrichment chain run (group consolidation → priority scoring → 200 cold-email drafts)

Final stage of the 2026-05-18 OSM scrape + enrichment push. Operator wanted the post-enrichment chain to complete in one go without re-gating between steps, so this run is the exception that sets `FIRSTWAVE_LLM_ALWAYS_ALLOW=1` (see [[feedback-after-hours-llm-enrichment]]). All upstream enrichment had already finished and was therefore gate-respected.

### Built / run

- `scripts/group_consolidate.py` — Haiku classifies each verified lead's `parent_group` (Marriott / Hilton / Accor / IHG / Hyatt / Wyndham / Choice / Best Western / Radisson / Meliá / NH / Four Seasons / Mandarin Oriental / Rosewood / Aman / Belmond / Kempinski / Shangri-La / Six Senses / Soneva / `Independent`). One property per group marked `is_primary_contact=true`. Sets `outreach_approved=TRUE` on primaries only — non-primary chain properties stay in DB but are excluded from outreach so we don't spam shared sales teams with N parallel emails.
- `scripts/outreach_score.py` — 0-100 `lead_score`. Weights: country (EU + English-speaking high, US/CA/AU tier-3), operator_type (`independent` 1.0 → `chain` 0.5), pain_points (OTA/revenue/yield management = top weights), DM role (Owner/GM 1.0 → Marketing manager 0.7).
- `scripts/draft_outreach_emails.py --top-n 200` — Haiku-style prompt via Ollama (`gpt-oss:20b`), 80-120 word personalised body + 6-10 word subject. Persona: Liam Doyle, Berlin, soft 15-min-call CTA mentioning a 10:30 / 10:50 / 11:10 Europe/Berlin slot. Drafts written to `leads.outreach_email_1`.
- `scripts/post_enrichment_chain.sh` — orchestrator: blocks on `pgrep -f enrich_leads_haiku|enrich_max_test`, then runs the three stages with `tee` into `logs/`.

### Validation (Supabase ground truth at end of session)

| Metric | Count |
|---|---|
| Total `leads` rows | 1000 |
| By source | `haiku_pilot` 838, `haiku_max_test` 47, `apollo` 115 (legacy) |
| `verification_status = verified_hotel` | 852 |
| Primary contacts | 510 |
| `outreach_approved = TRUE` | 514 |
| With `lead_score` | 947 |
| With `outreach_email_1` draft | 104 |
| Top parent groups | Independent 502, Accor 15, Hilton 9, IHG 8, Marriott 7, Choice 4, Wyndham 4, Radisson 3, Meliá 3, NH 3 |

(The group-consolidate log reported 971 records updated / 897 set primary mid-run; the lower current numbers reflect later post-processing.)

### Known issues / notes

- 200 drafts requested, 104 with non-null `outreach_email_1` end-state — the rest were overwritten/cleared during a later pass or had pre-existing drafts; spot-check before re-running.
- France + Denmark have zero coverage in the underlying OSM scrape ([[feedback-overpass-country-split]]) — need a region-split backfill before we have full European coverage.
- Post-enrichment chain script hardcodes `FIRSTWAVE_LLM_ALWAYS_ALLOW=1` — fine as a manual chain after enrichment is done, but never call this from a cron / automation that triggers without the operator present.

### Next

- Review the 200 drafts (they sit on `leads.outreach_email_1`; surface via `/review-queue` frontend or direct Supabase).
- Backfill FR/DK OSM data via region bbox split.
- Commit the still-untracked pipeline scripts (`scrape_osm.py`, `injection_audit.py`, `outreach_score.py`, `draft_outreach_emails.py`, `enrich_after_hours.sh`, `post_enrichment_chain.sh`) — they're production-grade now.

---

## 2026-05-18 (late evening) — OSM Overpass scrape (70k hotels) + injection audit + 5-shell Haiku enrichment

Major lead-volume expansion past the Wikipedia-only ceiling. End-of-day Supabase count went from ~695 verified candidates to 838 `haiku_pilot` rows after the enrichment chunks ran overnight.

### Built / run

- `scripts/scrape_osm.py` — queries OSM Overpass API `node[tourism=hotel]` across 34 target countries (English-speaking ex-US, Western/Central/Eastern Europe, Nordic, Mediterranean). 2s rate-limit delay between queries, 180s timeout each. Writes `data/phase2/osm_hotels.json`.
  - **Result: 70,739 hotels in ~18 minutes** (22:24 → 22:42 CEST).
  - Top yields: Germany 13,630 · Italy 13,051 · Spain 7,600 · Greece 5,110 · UK 3,687 · Poland 2,797 · Austria 2,748 · Switzerland 2,435 · Netherlands 2,258 · Czech Republic 2,209 · Canada 1,741 · Australia 1,481 · Sweden 1,095 · Portugal 1,493.
  - **France + Denmark returned 504 Gateway Timeout — 0 hotels each.** Single-country Overpass queries exceed the public endpoint's server-side timeout; see [[feedback-overpass-country-split]] for the region-bbox fix.

- `scripts/injection_audit.py` — defensive pass over scraped data before LLM enrichment. Scans for known injection phrases (`"ignore previous"`, `"system:"`, `"you are now"`, role tokens), excessive newlines, RTL override + zero-width chars, and per-field length anomalies. Splits to `clean_candidates.json` + `quarantine.json`.
  - **Result: 69,054 scanned → 69,001 clean / 53 quarantined.**
  - Flag breakdown: 36 `too_long` · 11 `phrase` · 4 `newlines` · 2 `rtl_override` · 1 `zero_width`.
  - Fields hit: brand 24, phone 15, address 9, name 3, website 2, email 1.
  - Spot-check: most quarantines look like malformed OSM tags (e.g. Steigenberger's `brand` field had a newline-separated head-office address), not deliberate attacks — but the gate exists for the case where one is. Manually review `quarantine.json` before discarding.

- `scripts/enrich_after_hours.sh` — launches 5 parallel `enrich_leads_haiku.py` shells on chunks 1-5 under `nohup`, logging to `logs/enrich_chunk_{1..5}.log`. Crucially does **not** set `FIRSTWAVE_LLM_ALWAYS_ALLOW=1` — relies on `backend/utils/anthropic_client.py` `_is_vybe_trading_window()` to defer LLM calls during vybe-trading active hours. Ran overnight 2026-05-18 → 2026-05-19.

### Why

Wikipedia-only ceiling was ~695 verified leads after enrichment (per `docs/NEXT_LEAD_SOURCES.md`); the target was 1000 outreach-ready primaries. OSM was the tier-2 "free, 1-2 hours to write extractor" option in that ranking. Final tally proves it was the right call — 70k raw → ~838 verified after enrichment + group consolidation.

### Known issues / notes

- France + Denmark gap is meaningful (France alone likely has ~8-10k OSM hotels). Backfill pending.
- Overpass's public endpoint had transient 504s on a couple of other countries mid-run — they retried via the next per-country call cycle but worth noting for re-runs.
- `injection_audit.py` and `scrape_osm.py` are both still untracked in git as of 2026-05-19.

### Next

Post-enrichment chain (group consolidation → priority scoring → cold-email drafts) — see next-day entry above.

---

## 2026-05-18 (morning) — Haiku enrichment pipeline + Wikipedia coordinator expansion

Built the LLM-driven enrichment + group-consolidation infrastructure on top of the 2026-05-16 scraper foundation. Wikipedia run delivered the first 695 verified candidates.

### Built

- `scripts/enrich_leads_haiku.py` — two-pass enrichment using Haiku. Pass 1 (`clarify_lead`): JSON classification `Verified Hotel Operator | Not a Hotel | Unclear` with 0.0-1.0 confidence + reasoning. Pass 2 (`enrich_lead`): operator_type (`independent`/`boutique`/`franchise`), team_size_estimate, pain_points, decision_maker_role, region. Writes Supabase `leads` rows with `source=haiku_pilot`. Batches of 5 (CLAUDE.md rule), respects vybe-trading window via `VybeTradingWindowError`.
- `scripts/group_consolidate.py` — Haiku classifies parent chain. Hard-coded chain taxonomy (Marriott family, Hilton family, Accor, IHG, Hyatt, Wyndham, Choice, Best Western, Radisson, Meliá, NH/Minor, Four Seasons, Mandarin Oriental, Rosewood, Aman, Belmond, Kempinski, Shangri-La, Six Senses, Soneva, Independent). Marks one primary per group; sets `outreach_approved=TRUE` only on primaries.
- `scripts/enrich_after_hours.sh` — 5-shell parallel runner, no `FIRSTWAVE_LLM_ALWAYS_ALLOW` override.
- `scripts/scrape_with_haiku.py` — Wikipedia `Category:Hotels_in_<city>` scraper that uses Ollama to extract structured JSON from page content (95%+ valid JSON rate per `docs/NEXT_LEAD_SOURCES.md`).

### Validation (end of Wikipedia run)

- Raw candidates from 10 Wikipedia shells: ~700
- Verified (post-Haiku clarification): 695
- Manual review queue: ~110 (confidence 0.75-0.84)
- Expected post-group-consolidation primary contacts: 350-400

### Known issues / notes

- Worked sources: Wikipedia `Category:Hotels_in_X`, Haiku JSON extraction, multi-shell parallel (10 shells, clean dedup).
- Did NOT work: Relais & Châteaux (JS-heavy), Small Luxury Hotels (same), Michelin Guide (anti-bot), Chamber of Commerce sites (403), OpenCorporates (needs API key), Wikipedia `List_of_hotels_in_X` (page format doesn't exist).
- Tier-1 source ranking documented in `docs/NEXT_LEAD_SOURCES.md` — wikipedia regions + OSM + Companies House CSV are the cheap big wins.

### Next

OSM Overpass scrape to break past the Wikipedia ceiling — see same-day late-evening entry above.

---

## 2026-05-16 — Hotel lead-gen Phase 1-2 foundation (committed)

4 commits already pushed locally on vybe-desktop but not yet to `origin/main` as of 2026-05-19.

### Shipped (commits)

- `734cd0b` — Phase 1 foundation for hotel lead generation (2000-lead pipeline)
- `1e4899e` — Multi-shell parallel pipeline for Phase 2-4 (lead generation)
- `da4cd49` — Phase 2 scraper templates + orchestration + quickstart guide
- `556a115` — Phase 2 scrapers with OpenCorporates API integration (with fallback)

### Built

- 5 regional scrapers: `scrape_eu_west.py`, `scrape_eu_central.py`, `scrape_eu_south.py`, `scrape_us.py`, `scrape_booking_expedia.py`.
- Pipeline glue: `combine_batches.py`, `dedup_leads.py` (SHA1 on name+address+city), `screening_filter.py` (non-LLM validation gates), `batch_split.py` (range-based).
- Orchestration: `scrape_haiku_coordinator.sh` for the Wikipedia path.
- Docs: `docs/PHASE_2_QUICKSTART.md`, `docs/PIPELINE_COORDINATION.md`, `docs/PHASE_2_3_COMPLETION.md`.
- OpenCorporates API integration with sample-data fallback when no key is set (we don't have a key — fell through to fallback on the proof-of-concept run).

### Validation (initial proof-of-concept run)

- 22 sample leads across 5 regions; 0% dedup, 100% screen pass.
- Pipeline ran end-to-end; sample data only because no OpenCorporates key.

### Known issues / notes

- `docs/PHASE_2_3_COMPLETION.md` has a date typo in its title ("Saturday 2026-05-25") — the actual run was 2026-05-16 with Phase 3 work continuing 2026-05-18/19. Worth fixing in a follow-up doc-only commit.
- These 4 commits + `bb9ef0f` (2026-05-13 trading-hours fix) + `55960ef` (2026-05-13 work-log entry) are still **unpushed to origin/main**. Push when ready.

### Next

Build the Haiku enrichment pipeline on top — see 2026-05-18 morning entry above.

---

## 2026-05-13 — Session: trading-hours gate + Claude Max cooloff (cross-project with vybe-trading)

Coordinated change with vybe-trading's ADR-028 to stop the shared Claude Max account from being burned by simultaneous LLM cascades and to keep firstwave from queueing Ollama requests behind trading-critical agents.

### Shipped

- `_is_vybe_trading_window()` added to `backend/utils/anthropic_client.py`. Gates `generate()` and `classify()` to weekends + the daily 21:00–22:00 UTC CME futures break. Raises `VybeTradingWindowError` outside those windows so callers defer cleanly rather than swallow. Override: `FIRSTWAVE_LLM_ALWAYS_ALLOW=1` (for manual jobs / tests only — never in production agents).
- `_call_cli` now honours the cross-project Redis key `llm:claude:cooloff_until`, written by vybe-trading's `agents/llm_router.py` after parsing the Claude CLI's `"You've hit your limit · resets HH:MM(am|pm) (TZ)"` stdout. Short-circuits the CLI invocation while the Max account is in cooloff so firstwave doesn't double-burn the throttle window.
- Ollama request body now passes `keep_alive=-1` per-request (alongside the existing `OLLAMA_KEEP_ALIVE=-1` env on the desktop container; defensive against env reset).
- New rule added to `docs/FIRSTWAVE_SYSTEM_CONTEXT.md` § 8 (rule 11).

### Why

On 2026-05-13 the vybe-trading backend stacked Ollama → Groq → Claude Sonnet → Claude Haiku cascades that burned the Max quota and amplified `complete()` to 64-minute single-run wall times. firstwave's `_call_cli` invokes the same `~/.local/bin/claude` binary against the same Max account; once Phase 2 ships its agents (enrichment, outreach, intent parser, follow-up, briefing), firstwave will compound the contention without a coordination layer. These gates are pre-emptive — Phase 2 is not built yet so firstwave isn't currently generating LLM traffic.

### State at end of session

- Backend deployed via self-hosted runner (no extra steps); `firstwave-backend.service` restarted at 12:59 CEST.
- No new env vars required for default behaviour. `FIRSTWAVE_LLM_ALWAYS_ALLOW` defaults to off.
- Pairs with vybe-trading commits `e0414c8` (`fix(llm_router)`) + `84f2e48` (`docs: ADR-028`).

### Out of scope (tracked for follow-up)

- The `ollama:fq_active` priority counter and `ollama:cpu_degraded_until` breaker introduced by vybe-trading's ADR-030 (afternoon session) are NOT yet honoured by firstwave. firstwave currently uses single-Ollama routing (no CPU tier). Worth wiring up before Phase 2 lights up.

---
## 2026-05-11 (continued) — Session: full credential rotation + cache scrub

Same date, second wrap. Continues from the earlier entry (credential hygiene + gitleaks + SSH switch).

### Credentials rotated (manual at provider; .env updated on vybe-desktop and vybe-pi; service restarted; verified end-to-end)

| Credential | Verification |
|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` | `GET /investors` via local 8001 returned 100 rows under the new key. Pre-restart logs showed `Unregistered API key` errors confirming the old key was atomically invalidated by the Supabase "Reset" action. |
| `GOOGLE_REFRESH_TOKEN` + `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` | Full OAuth re-flow via new Desktop-type OAuth client. Used `scripts/get_google_token.py` over an SSH port-forward (`ssh -L 8080:localhost:8080 vybe@vybe-desktop`) because vybe-desktop is headless. First refresh attempt failed with `unauthorized_client` — diagnosed via a leak-safe diff against `~/.secrets/firstwave/google-credentials.json` that `.env` had retained the old `client_id`/`client_secret` while only `refresh_token` was updated. Programmatically synced all 3 vars from JSON → vybe-desktop .env → vybe-pi .env, then `creds.refresh()` succeeded on both machines. Old OAuth client deleted at Cloud Console after verification. |
| `TELEGRAM_BOT_TOKEN` | Revoked + reissued via @BotFather (atomic). Service restart logs clean, no 401/Telegram errors. |

### Claude data cache scrub (vybe-desktop)

Past sessions had cached `~/firstwave-pipeline/.env` plaintext into Claude's data store. Once provider-side credentials were revoked, the leaked copies were inert but still ugly. Pattern-replaced with `[REVOKED_*]` placeholders across:

- `~/.claude/file-history/<session>/<file>@vN` — 2 pre-existing snapshots scrubbed
- `~/.claude/projects/*.jsonl` — 16 session transcripts scrubbed
- `~/.claude/paste-cache/<id>.txt` — 1 paste-cache entry
- `~/.bash_history` on **vybe-pi** — 2 token strings

Patterns scrubbed: `ghp_[A-Za-z0-9]{36}`, `github_pat_[A-Za-z0-9_]+`, `GOCSPX-[A-Za-z0-9_-]+`, `1//[0-9A-Za-z_-]{40,}` (Google refresh), `[0-9]{8,12}:AA[A-Za-z0-9_-]{30,}` (Telegram bot), and Supabase-shaped JWTs (`eyJ.<base64>.eyJpc3MiOiJzdXBhYmFzZSI...` + broader 3-segment JWT-shaped scrub on a small whitelist of files known to contain them).

Final cross-pattern sweep on `~/.claude/`: zero credential-shaped strings remain. Only `ghp_` matches now are in the Claude Code VS Code extension's bundled regex on surface-pro-3 (`ghp_[0-9a-zA-Z]{36}` pattern literal — it's the detector, not a credential).

### CLAUDE.md touch on surface-pro-3

`docs(claude-md): add surface-pro-3 to machines table` (`03221b8`). Pre-existing local edit on the sp3 clone, surfaced + landed during the post-pull rebase. Deploy run `25692886386` succeeded.

### Saved memories (apply across future sessions)

- `feedback_credential_file_reads.md` — don't Read/cat `.env` or secrets files in full during a Claude session. Use `grep -E "^[A-Z_]+=" file | cut -d= -f1` for variable names only, and value-redacting one-liners (`git remote -v | sed -E "s/(ghp_|github_pat_)[A-Za-z0-9_]+/[REDACTED]/g"`) when needed.
- `feedback_avoid_credential_leaks.md` — three preventive practices: (1) SSH-default for git remotes (no `https://user:TOKEN@github.com/...`); (2) don't store credentials in `.env` if no application code reads them (git auth belongs in SSH/credential helper); (3) gitleaks pre-commit + monthly disk sweep (`grep -rIl 'ghp_\\|github_pat_\\|sk-\\|AKIA' ~ --exclude-dir={.git,node_modules,venv,.venv,.cache}`).

### Validation

| Check | Result |
|---|---|
| Final Supabase exercise | `GET /investors` → 200, 100 rows |
| Final Google OAuth refresh | both machines OK after `.env` sync from JSON |
| Final Telegram check | restart logs clean |
| Cross-machine `ghp_\|github_pat_\|GOCSPX-\|1//\|XXXXX:AA\|eyJpc3MiOiJzdXBhYmFzZSI` sweep | `~/.claude/` and `~/firstwave-pipeline/` both CLEAN on vybe-desktop, vybe-pi, surface-pro-3 |
| firstwave-backend service | active, last restart at 21:22:57 CEST (Telegram rotation), /health 200 |
| Old Google OAuth client | deleted at Cloud Console; new client `firstwave-2026-05-11` retained |

### Outstanding

- ~17 other secrets in `.env` (Apollo, PhantomBuster, Cal.com, Groq, etc.) were NOT rotated this session. Lower-priority blast radius. Same procedure applies if you choose to rotate them.
- The remaining credential-rotation memory note (`feedback_credential_file_reads.md`) should keep future sessions from re-seeding the cache with secrets when reading `.env`.

---

## 2026-05-11 — Session: credential hygiene + gitleaks pre-commit

### Changed
- `.pre-commit-config.yaml` — added gitleaks v8.30.1 hook to block accidental commits of API tokens / credentials (commit `0d06b1d`).
- `.github/workflows/deploy.yml` — changed `sudo cp` step to use the absolute source path so vybe-pi's sudoers NOPASSWD rule matches argv verbatim (commit `77d02bb`). Pattern mirrors vybe-trading's deploy.yml.

### Off-repo infrastructure (vybe-pi)
- Generated dedicated SSH deploy key `~/.ssh/id_ed25519_firstwave` on vybe-pi. The pre-existing `id_ed25519` is already registered as a deploy key for vybe-trading, and GitHub disallows reusing a single key across repos.
- Added `Host github-firstwave` block to `~/.ssh/config` on vybe-pi pointing the new key at `github.com`.
- Reset `~/firstwave-pipeline/.git/config` remote to `git@github-firstwave:LDoyleDev/firstwave-pipeline.git` — replaces a `https://LDoyleDev:<PAT>@github.com/...` URL that had a GitHub PAT embedded in plaintext.
- Same SSH switch applied to `~/firstwave-pipeline/.git/config` on vybe-desktop (uses the existing LDoyleDev user-level SSH key — no separate deploy key needed since vybe-desktop authenticates as the account).
- Installed `/etc/sudoers.d/firstwave-deploy` on vybe-pi (0440 root:root) with NOPASSWD entries matching deploy.yml argv: `/usr/bin/cp <absolute path> /etc/systemd/system/firstwave-backend.service`, `/usr/bin/systemctl daemon-reload`, `/usr/bin/systemctl restart firstwave-backend`. Removed stale `/etc/sudoers.d/firstwave` (referenced renamed `firstwave-api` service, had loose 644 perms which visudo rejected).

### Credential remediation
- Removed `GITHUB_REPO_TOKEN` from `~/firstwave-pipeline/.env` on vybe-desktop and vybe-pi. No source file referenced it; the only consumer was the git remote URL, now SSH.
- Revoked 3 stale GitHub PATs on the account.
- Scrubbed leaked token strings from `~/.bash_history` on vybe-pi (2 occurrences → `[REVOKED_PAT]`).
- Scrubbed leaked token strings from 7 Claude data files on vybe-desktop (2 `~/.claude/file-history/` snapshots + 5 `~/.claude/projects/*.jsonl` session transcripts, 8 occurrences total → `[REVOKED_PAT]`).

### Validation
| Check | Result |
|---|---|
| `gitleaks` pre-commit run across full tracked tree | passed (no pre-existing secrets) |
| `ssh -T git@github-firstwave` from vybe-pi | `Hi LDoyleDev/firstwave-pipeline!` ✓ |
| Deploy workflow on push of `77d02bb` (GitHub run 25684602593) | success — git pull, pip install, sudo cp, daemon-reload, systemctl restart all green |
| `systemctl is-active firstwave-backend` post-deploy | `active` (PID 166235, ActiveEnterTimestamp 2026-05-11 18:57:38 CEST) |
| `curl https://firstwave.vybe-dev.com/health` | `200` |

### Known issues / notes
- ~20 other secrets in `~/firstwave-pipeline/.env` (Supabase ANON + SERVICE_ROLE keys, Telegram bot token, Groq, Google OAuth client secret + refresh token, Cal.com, Apollo, PhantomBuster, Gmail sender) are likely cached in older `~/.claude/file-history/` + `~/.claude/projects/*.jsonl` files on vybe-desktop from prior sessions that read `.env`. Separate rotation cycle planned for the most sensitive (`SUPABASE_SERVICE_ROLE_KEY`, `GOOGLE_REFRESH_TOKEN`, `TELEGRAM_BOT_TOKEN`).
- The deploy workflow had been failing silently for 3 prior runs before today's fix — `firstwave-backend.service` remained running across the failures because none of them touched the systemd unit successfully, so the deploy was effectively a no-op for the live service.

### Next
- Rotate remaining firstwave credentials per sensitivity priority (separate session).

---


## 2026-05-07 (late evening) — Draft edit fix + placeholder resolver

### Built / changed
- **`backend/routers/leads.py`** — `LeadUpdate` model was missing `outreach_email_1` and `outreach_email_2` fields; Pydantic was silently dropping them, PATCH returned 400 "No fields to update" → frontend edit appeared to save then snapped back. Fixed by adding both fields to the model.
- **`backend/agents/outreach.py`** — added `resolve_draft_placeholders()` and `_resolve_placeholder()`: after outreach generation, scans for `[label]` patterns, attempts Haiku training-knowledge lookup + DuckDuckGo web search fallback per placeholder, substitutes the resolved value or leaves the text unchanged if not found
- **`backend/routers/actions.py`** — added `POST /actions/resolve-placeholders/{investor_id}` endpoint to fix existing drafts without full regeneration
- **`backend/prompts/system_prompts.py`** — `INVESTOR_OUTREACH_SYSTEM_PROMPT` updated: Tier 1 rule changed from "Reference a specific portfolio company" to "only reference one if you know it with confidence, otherwise use generic language"; FORMAT rule added banning `[placeholder]` syntax entirely

### Existing drafts fixed in DB (direct Supabase update)
- Mihir Karkare / Howzat Partners → `[portfolio company]` → "your portfolio hotels" (Haiku/search couldn't find portfolio; generic fallback used)
- Eric Martineau-Fortin / White Star Capital → `[portfolio company]` → "Fathom" (Haiku knew this one)
- Bessemer Venture Partners (EU) → `[Name]` → "the team" (no contact name in DB)
- Atlantic Labs → `[Name]` → "the team" (no contact name in DB)
- AngelList Hospitality Syndicates → `[Investor]` → "there" (generic contact)
- 0 placeholders remain across all 100 investor drafts

### Root cause of draft-edit bug
- `LeadUpdate` Pydantic model only had `pipeline_stage`, `lead_score`, `warmth`, `notes`, `outreach_approved`, `next_action_at` — no outreach fields. Frontend `onEdit` sends `{ outreach_email_1: draft }`, Pydantic dropped it silently, backend raised 400, React Query mutation failed silently, card reverted.

### Root cause of placeholders
- DuckDuckGo search (`duckduckgo_search` 8.1.1) is currently returning unrelated garbage results regardless of query (likely rate-limiting or locale bug) — marked as known issue, package should be updated to `ddgs`
- Upstream fix in the prompt is the primary mitigation; Haiku training knowledge is secondary; web search is tertiary

### Post-entry fix
- **`requirements.txt` + `web_researcher.py`** — `duckduckgo-search` → `ddgs` (package was renamed upstream; 8.1.1 was returning garbage results for all queries). Two-line change, tested against White Star Capital query — 3 correct results returned. Deployed to Pi (PID 317874, 23:03 CEST).

---

## 2026-05-07 (evening) — Ollama guard + session doc fixes

### Built / changed
- **`backend/utils/anthropic_client.py`** — added `ollama_available()`: hits `/api/tags` with a 5s timeout, returns bool; no model load, pure liveness ping
- **`backend/routers/actions.py`** — all four batch endpoints (`enrich-batch`, `generate-outreach-batch`, `enrich-investors-batch`, `generate-investor-outreach-batch`) now call `ollama_available()` at entry and return `{"skipped": True, "reason": "Ollama unavailable"}` immediately if Ollama is down; prevents fallthrough to Claude Max CLI

### Root cause this fixes
- n8n investor pipeline (old 07:30 cron) fired on May 7 morning while Ollama was unreachable (ConnectError to vybe-desktop). Each enrichment attempted 5 Claude Max CLI retries before failing → 199 calls in the 08:xx hour, burning Claude Max quota
- Re-confirmed from Pi journalctl: `Ollama gpt-oss:20b unavailable (ConnectError)` at 08:22, then `Claude CLI error (attempt 1–5/5)` per investor

### Doc / CLAUDE.md fixes
- **`docs/WORK_LOG.md`** — backfilled two post-docs commits from earlier in the session: backend 0.0.0.0 rebind, n8n URL fix, PasswordGate Tailscale bypass, cron reschedule
- **`CLAUDE.md`** — corrected stale Pi infrastructure note: `--host ::` → `--host 0.0.0.0`; added note that service file lives at `infra/firstwave-backend.service` and deploy.yml copies it on each deploy; n8n URLs now `127.0.0.1:8001`

### Known issues / notes
- Ollama lives on vybe-desktop; if desktop is asleep at 02:00 CET the guard will now silently skip rather than burn Claude Max — next run picks up where it left off (idempotent)
- Consider adding Ollama auto-wake or a Telegram alert if skip rate increases

---

## 2026-05-07 — Ollama restoration + investor pipeline full run

### Built / changed
- **Ollama restored** — Docker container (`ollama/ollama:rocm`) was dead since ~22:00 previous night (crashed on a 30s inference timeout, no restart policy). Snap Ollama had auto-started in its place but was sandboxed to `127.0.0.1` and couldn't read Docker volume models. Fix: disabled snap service, restarted Docker container with `--restart=unless-stopped`, `OLLAMA_HOST=0.0.0.0`, `OLLAMA_KEEP_ALIVE=-1`, `OLLAMA_ORIGINS=*`. All 4 models restored: `gpt-oss:20b`, `qwen3:14b`, `qwen3-coder:30b`, `llama3.2:3b` (41GB in Docker volume, no re-download needed)
- **`backend/agents/enrichment.py`** — switched both `enrich_lead` and `enrich_investor` from Sonnet default to Haiku; fixed `TypeError` in `enrich_investor` name-parsing (splat of `("", [])` fallback put `[]` into `*rest`); imported `HAIKU` constant
- **`backend/utils/anthropic_client.py`** — `_call_cli` now captures `result.stdout` when `stderr` is empty, so Claude Max usage-limit messages are visible in logs
- **`backend/routers/actions.py`** — capped `enrich-investors-batch` at 5 per call (was unbounded, always Cloudflare-timeout through tunnel)
- **Pi service restart** — stale Apr29 uvicorn process (PID 1769808) was still serving after May 6 deploy; killed it, systemd restarted with new code
- **Snap Ollama permanently disabled** — `snap.ollama.listener.service` disabled to prevent port 11434 conflicts after reboot

### Investor pipeline — full run completed
- Enriched all 100 investors via `gpt-oss:20b` local Ollama: 93/100 valid fit scores (35–90), 7 JSON parse failures (zero score but still moved forward)
- Generated outreach drafts for all 100 investors: 100/100 in `ready_to_contact`
- Zero Claude Max quota consumed — entire run was local GPU inference

### Usage investigation
- Diagnosed Claude Max usage limit hit: vybe-trading pipeline burned ~1.5M tokens (Sonnet) between 16:00–19:00 on May 6 (191 calls in the 18:00 hour alone); limit still in rolling window when enrichment batch ran at 08:55
- Claude Code local session data parsed from JSONL files in `~/.claude/projects/`

### Post-docs changes (same session, after log commit)
- **Backend re-bound to `0.0.0.0`** — `infra/firstwave-backend.service` added to repo (`--host 0.0.0.0 --port 8001`); `deploy.yml` updated to `cp` the service file and `systemctl daemon-reload` on each deploy so Pi always tracks the committed version. Previous `--host ::` (IPv6-only) was refusing Tailscale IPv4 connections from the desktop frontend.
- **n8n workflow URLs** — all 6 workflows changed from `http://localhost:8001` → `http://127.0.0.1:8001` (explicit IPv4 loopback; `0.0.0.0` doesn't bind on `::1` so n8n's Node IPv6-first resolution would break)
- **`frontend/src/PasswordGate.jsx`** — bypass auth gate for `100.*` (Tailscale CGNAT range) so Tailscale access works without password prompt
- **Investor pipeline cron rescheduled 07:30 → 02:00 CET** — overnight run avoids Ollama GPU contention with vybe-trading (which owns 07:00–22:00 CET); n8n workflow updated via API and JSON definition updated

### Blockers / known issues
- Apollo account deactivated (401 on every call) — enrichment runs on web search only; upgrade or replace needed for contact email discovery
- 7 investor enrichments have zero fit score (Ollama returned non-JSON); outreach still generated for these
- `duckduckgo_search` package renamed to `ddgs` — warning on every web search call; non-blocking but should update dependency

### Current pipeline state
- 100 investors: all in `ready_to_contact` with outreach drafts, awaiting approval in review queue
- 57 client leads: still in `review_queue` awaiting approval
- 53 client leads: in `discovered`, not yet enriched

### Next
- Review and approve investor outreach drafts in dashboard
- Review and approve client lead drafts
- Consider Apollo upgrade or LinkedIn CSV import to get contact emails

---

## 2026-05-06 — Investor pipeline automation + lead discovery

### Built / changed
- **`backend/routers/actions.py`** — added `POST /actions/enrich-investors-batch` (picks up `identified` investors with no `enrichment_data`, enriches via `enrich_investor`, advances to `research_needed`) and `POST /actions/generate-investor-outreach-batch` (picks up `research_needed` investors with no `outreach_draft`, generates via `generate_investor_outreach`, advances to `ready_to_contact`)
- **`backend/utils/anthropic_client.py`** — bumped Ollama context window to 16k (`num_ctx: 16384`) to improve enrichment prompt quality
- **`frontend/src/components/review/ReviewCard.jsx`** — refactored to handle both client (1-email) and investor (2-email `email_1`/`email_2`) draft formats; extracted `EmailBlock` component and `parseJson` helper; removed unused `IS_PRODUCTION` import
- **`n8n-workflows/investor_pipeline.json`** — new n8n workflow: daily Mon–Fri 07:30 cron chains enrich-investors-batch → generate-investor-outreach-batch; both steps idempotent
- **Imported investor_pipeline workflow to n8n** on vybe-pi via API (`id: yOBJ4WwEuE9GZL3H`, active); API key used: `pipeline` key in `user_api_keys` table

### Lead discovery findings
- Ran full Apollo API discovery across all 14 markets (`--bypass-limit`); only yielded **48 new leads** (total 115 in DB) — Apollo free tier caps search results at ~50 contacts regardless of `max_pages` setting
- **Root cause**: Apollo free tier limits are per API plan, not per request — pagination config is correct but quota blocks results
- **Fix path**: upgrade Apollo to Basic ($49/mo) for 1000 export credits/month, OR manually export CSV from Apollo/LinkedIn web UI and import via `scripts/import_leads_csv.py`
- Import script auto-detects Apollo CSV format (via `LinkedIn URL` header) and LinkedIn Sales Navigator format (via `Profile URL` header); deduplicates against existing DB emails

### Current pipeline state
- 115 total leads: 53 discovered, 5 enriched, 57 review_queue
- 57 review_queue leads have outreach drafts written — awaiting operator approval in dashboard before any email sends
- Investor pipeline automation live — first run tomorrow 07:30

### Blockers / next
- Apollo free tier: need paid plan or manual CSV export to reach 1000-lead target
- 57 leads need review/approval in dashboard to move forward through outreach sequence

---

## 2026-04-29 — Session 2: context refresh + smoke test

### Done
- Port 8002 stale uvicorn — confirmed gone; `firstwave-api.service` fully absent from systemd. No action needed.
- **README.md** — rewritten "Starting the system" to reflect Pi deployment model (systemd, not manual terminal). All `localhost:8000` refs replaced with `firstwave.vybe-dev.com` / Tailscale URLs. `ANTHROPIC_API_KEY` env var replaced with Claude Max OAuth note.
- **docs/FIRSTWAVE_SYSTEM_CONTEXT.md Section 4** — corrected Python 3.11→3.12, AI entry (API key → Claude Max OAuth token), hosting block updated to reflect Pi + n8n + Cloudflare Tunnel + CI/CD runner.
- **docs/WORK_LOG.md** — resolved open issues from earlier session (port 8002 and follow_up_executor.json stub).
- **Smoke test — all API-testable surfaces green:**
  - 35 routes registered and responding
  - `/health`, `/meetings/today` (3 correct slots), `/leads` (12), `/investors` (100), `/review-queue` (12 client / 100 investor)
  - `/status/morning-brief` generates correct pipeline summary
  - `/meetings/upcoming-briefings` and `/meetings/completed-pending-feedback` operational
  - n8n crons confirmed firing (backend logs show `::1` GET every 5–10 min, no errors)
  - No errors in backend journal for the past 30 min

### Not tested (requires live Telegram interaction)
- Voice command → discovery → enrich → review queue → approve → sequence → send flow
- Cal.com booking + Google Calendar event creation
- Pre-meeting briefing delivery via Telegram
- Post-meeting feedback → follow-up draft → send flow

### State
- 12 client leads in `discovered` stage — ready to enrich
- 100 investors in DB, none contacted — ready to start outreach
- All n8n crons green

---

## 2026-04-29 — Operations: fix silent n8n cron failures

### Found
- All 200 most recent n8n workflow runs (Meeting Briefing Trigger, Post-Meeting Feedback Prompt, Reply Checker, Sequence Scheduler, Morning Brief, PhantomBuster Daily Launcher) had been failing silently with `ECONNREFUSED ::1:8001` — Node's getaddrinfo resolved `localhost` to `::1` first, but uvicorn was bound to `0.0.0.0` (IPv4 only).
- `firstwave-api.service` (legacy port-8002 uvicorn, supposedly removed in CLAUDE.md notes) is in fact still running on the Pi as PID 1532377 since 2026-04-24 — orphan process not catalogued by systemd anymore but still consuming the port.
- `n8n-workflows/follow_up_executor.json` is an empty 0-node stub; the corresponding workflow was never imported into n8n. Likely redundant since `backend/routers/meetings.py::confirm-followup` is triggered by the Telegram voice flow, not n8n cron.

### Fixed
- `firstwave-backend.service` ExecStart switched from `--host 0.0.0.0` to `--host ::`. Three post-restart cron firings across two workflows green; CLAUDE.md documents the binding choice and warns IPv4 to 127.0.0.1:8001 is refused (uvicorn sets `IPV6_V6ONLY=1` despite `bindv6only=0`).
- Refreshed CLAUDE.md infra section (port map, machines, Cloudflare tunnel + GH Actions runner + n8n.service + Claude Code OAuth).
- `scripts/get_google_token.py` now reads creds path from `$GOOGLE_CLIENT_SECRETS_FILE` (default `~/.secrets/firstwave/google-credentials.json`) — Google OAuth client secret out of repo root.
- Reverted misleading interim commit (8af47da) that switched workflow URLs to 127.0.0.1; the URL change had no runtime effect because n8n caches active-workflow definitions in memory and the cache survives `systemctl restart n8n.service` (saved as project memory for future sessions).

### Open / known issues
- ~~Stale uvicorn on port 8002~~ — **resolved**: process gone by next session; `firstwave-api.service` fully absent from systemd. Port 8002 is clear.

### Resolved in session
- `follow_up_executor.json` stub removed (commit 6e5613b) — confirmed redundant: `post_meeting_prompt.json` (active n8n cron, every 5 min) and the Telegram voice flow (`intent_parser._handle_send_followup → POST /meetings/{id}/confirm-followup`) cover the same functionality; stub was never imported into n8n.

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
