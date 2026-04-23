# FIRSTWAVE PIPELINE — SETUP GUIDE
> Follow this before opening Claude Code. Every account, credential, 
> and config must be in place before the build starts.

---

## OVERVIEW

You need to set up 8 external accounts/services and complete local machine setup including n8n install.
Total setup time: ~3-4 hours (most of it is waiting for verifications).
Do this in order — some steps depend on previous ones.

---

## STEP 1 — SUPABASE (Database)
**Time**: 10 minutes
**Cost**: Free

1. Go to https://supabase.com and sign up
2. Create a new project: name it `firstwave-pipeline`, set a strong database password (save it somewhere safe), choose region: **Frankfurt (eu-central-1)**
3. Wait ~2 minutes for the project to initialise
4. Go to **Project Settings → API**
5. Copy and save:
   - **Project URL** → `SUPABASE_URL` in your .env
   - **anon public key** → `SUPABASE_ANON_KEY`
   - **service_role secret key** → `SUPABASE_SERVICE_ROLE_KEY`
6. Go to **SQL Editor** → paste the contents of `supabase/schema.sql` → click Run
7. Paste and run `supabase/seed_investors.sql` → confirm 50 rows appear in `investor_targets` table

✅ Check: Go to Table Editor → you should see 7 tables populated (investor_targets has 50 rows, system_config has 5 rows)

---

## STEP 2 — TELEGRAM BOT
**Time**: 5 minutes
**Cost**: Free

1. Open Telegram on your phone and search for **@BotFather**
2. Send `/newbot`
3. Name: `FirstWave Pipeline`
4. Username: `firstwave_pipeline_bot` (or similar if taken)
5. BotFather gives you a token like `7234567890:AAHxxx...` → save as `TELEGRAM_BOT_TOKEN`
6. Now open a chat with your new bot (search for its username)
7. Send it any message (e.g. "hello")
8. Open this URL in your browser, replacing YOUR_TOKEN:
   `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
9. Find `"chat":{"id":XXXXXXXXX}` in the response — that number is your `TELEGRAM_OPERATOR_CHAT_ID`
10. Save both values in .env

✅ Check: Bot exists and responds to /start (it won't do anything meaningful yet — that comes in Phase 3)

---

## STEP 3 — GROQ API KEY
**Time**: 5 minutes  
**Cost**: Free (generous limits — Whisper transcription is nearly free at your usage level)

1. Go to https://console.groq.com and create a new account using liam@firstwaveai.com
2. Go to **API Keys** → **Create API Key**
3. Name it `firstwave-pipeline`
4. Copy key → save as `GROQ_API_KEY` in .env

✅ Check: Key is saved. The system uses the `groq` Python library — Claude Code will install it via requirements.txt.

---

## STEP 4 — ANTHROPIC API KEY
**Time**: 5 minutes
**Cost**: Pay-per-use (estimate: ~$20-30/month at this usage level)

1. Go to https://console.anthropic.com
2. Go to **API Keys** → **Create Key**
3. Name it `firstwave-pipeline`
4. Copy key → save as `ANTHROPIC_API_KEY` in .env
5. Add credit to your account: $20 is a good starting amount

✅ Check: API key is active and has credit loaded

---

## STEP 5 — GOOGLE / GMAIL OAUTH (liam@firstwaveai.com)
**Time**: 20-30 minutes
**Cost**: Free (uses your existing Google Workspace account)

This is the most involved step. Take care here.

**5a. Create a Google Cloud Project**
1. Go to https://console.cloud.google.com
2. Create a new project: name it `firstwave-pipeline`
3. Go to **APIs & Services → Library**
4. Enable these APIs (search each one):
   - **Gmail API**
   - **Google Calendar API**

**5b. Configure OAuth Consent Screen**
1. Go to **APIs & Services → OAuth consent screen**
2. User Type: **Internal** ← use this because liam@firstwaveai.com is Google Workspace. This skips the external verification process entirely.
3. App name: `FirstWave Pipeline`
4. User support email: `liam@firstwaveai.com`
5. Scopes: Add these manually:
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/calendar`
6. Save (no test users needed — Internal apps trust all users in your Workspace domain automatically)

**5c. Create OAuth Credentials**
1. Go to **APIs & Services → Credentials → Create Credentials → OAuth Client ID**
2. Application type: **Desktop App**
3. Name: `firstwave-pipeline-desktop`
4. Download the JSON file — save it as `credentials.json` in your project root (add to .gitignore)
5. Copy:
   - `client_id` → `GOOGLE_CLIENT_ID`
   - `client_secret` → `GOOGLE_CLIENT_SECRET`

**5d. Get a Refresh Token**
Run this one-time script in your project directory after Phase 1 setup:
```python
# Run once: python scripts/get_google_token.py
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar'
]
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)
print("REFRESH TOKEN:", creds.refresh_token)
```
- A browser window opens → sign in as `liam@firstwaveai.com` → grant permissions
- Copy the refresh token printed in terminal → save as `GOOGLE_REFRESH_TOKEN`

✅ Check: Script runs without error, refresh token saved

---

## STEP 6 — CAL.COM (Meeting Scheduling)
**Time**: 15 minutes
**Cost**: Free (API access included on free tier)

1. Go to https://cal.com and sign up
2. Connect your Google Calendar (use liam@firstwaveai.com)
3. Go to **Event Types → New Event Type**
   - Title: `First Wave AI — 20 Minute Intro`
   - Duration: **20 minutes**
   - Description: `Discovery call with Liam Doyle, Advisor at First Wave AI`
4. Go to **Availability** for this event type:
   - Select **Custom Schedule**
   - Set Monday–Friday only
   - For each day, add ONLY these three times: **10:30**, **10:50**, **11:10**
   - Timezone: **Europe/Berlin**
   - Daily limit: **3 meetings**
5. Save the event type
6. Note the event type ID (it's in the URL: `/event-types/12345`)
   → Save as `CALCOM_EVENT_TYPE_ID`
7. Go to **Settings → Developer → API Keys → Add**
   - Name: `firstwave-pipeline`
   - Copy key → save as `CALCOM_API_KEY`

✅ Check: Go to your Cal.com booking page — only 10:30, 10:50, 11:10 should appear as options

---

## STEP 7 — APOLLO.IO
**Time**: 5 minutes
**Cost**: Free tier (50 exports/month, unlimited search)

1. Go to https://app.apollo.io and sign up (use your liam@firstwaveai.com)
2. Go to **Settings → Integrations → API**
3. Create an API key → copy → save as `APOLLO_API_KEY`

✅ Check: Key saved, account verified

---

## STEP 8 — PHANTOMBUSTER
**Time**: 10 minutes
**Cost**: Free tier (10 min/day execution — enough for 20-30 leads/day)

1. Go to https://phantombuster.com and sign up
2. Go to **Account Settings → API**
3. Copy your API key → save as `PHANTOMBUSTER_API_KEY`
4. In PhantomBuster, go to **Phantom Store** → search for **"LinkedIn Search Export"** → Add to your account
5. Note the Phantom ID (shown in the URL when you open it)
   → Claude Code will need this to launch scrapes programmatically

✅ Check: LinkedIn Search Export phantom is in your account

---

## STEP 9 — LOCAL MACHINE SETUP
**Time**: 15 minutes

**9a. Install prerequisites** (on your Ubuntu 24.04 desktop)
```bash
# Check Python version — needs 3.11+
python3 --version

# Install Node.js 20+ for React frontend
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Confirm
node --version  # should be 20+
npm --version

# Install Python virtual environment tool if not present
sudo apt install python3-venv python3-pip -y
```

**9b. Create project directory**
```bash
mkdir ~/firstwave-pipeline
cd ~/firstwave-pipeline
```

**9c. Install and start n8n**
```bash
# Install n8n globally
npm install -g n8n

# Verify install
n8n --version

# Start n8n (first run sets up local SQLite database automatically)
n8n start
```

n8n will start at **http://localhost:5678**. On first run it asks you to create an account — use any email/password, this is just local auth. Save these credentials somewhere.

To run n8n in the background (so it survives terminal closes):
```bash
# Install pm2 process manager if not already installed
npm install -g pm2

# Start n8n via pm2
pm2 start n8n -- start
pm2 save
pm2 startup  # follow the instruction it prints to make it auto-start on boot
```

✅ Check: Open http://localhost:5678 in browser → n8n dashboard loads

**9d. Confirm Tailscale is active**
```bash
tailscale status
# Should show your machine's Tailscale IP (100.x.x.x)
# Note this IP — you'll use it to access the webapp from your phone
```

---

## STEP 10 — START CLAUDE CODE
**Time**: Ongoing

**10a. Install Claude Code** (if not already installed)
```bash
npm install -g @anthropic/claude-code
```

**10b. Copy the two build documents into your project**
```bash
mkdir -p ~/firstwave-pipeline/docs
cp FIRSTWAVE_SYSTEM_CONTEXT.md ~/firstwave-pipeline/docs/
cp FIRSTWAVE_BUILD_PHASES.md ~/firstwave-pipeline/docs/
```

**10c. Create your .env file**
```bash
cd ~/firstwave-pipeline
cp .env.example .env
# Fill in all values collected in Steps 1-8
nano .env
```

**10d. Launch Claude Code**
```bash
cd ~/firstwave-pipeline
claude
```

**10e. Opening prompt for Phase 1**

Paste this exactly:
```
We are building the First Wave AI Pipeline system — a voice-controlled B2B sales 
automation tool for two tracks: client acquisition and investor fundraising for 
a hospitality AI startup.

Read these two files before doing anything:
1. docs/FIRSTWAVE_SYSTEM_CONTEXT.md
2. docs/FIRSTWAVE_BUILD_PHASES.md

We are starting on Phase 1. 
Today's task: Project initialisation, Supabase client, database schema, and basic routers.

Ask me to clarify anything before writing code.
```

---

## DAILY WORKFLOW (once built)

**Morning startup (2 minutes)**
```bash
cd ~/firstwave-pipeline
# Start backend
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# Start frontend
cd frontend && npm run dev &

# n8n is already running
# Telegram bot starts automatically with the backend
```

**Daily rhythm**
- 06:00 → PhantomBuster scrape runs automatically (n8n)
- 08:00 → Sequence scheduler sends due emails (n8n)
- Morning → Check Telegram for new lead notifications
- Open http://localhost:5173/review → approve outreach drafts
- 10:30–11:30 → Meetings (briefings arrive at 10:00, 10:20, 10:40)
- After each meeting → Send voice note to Telegram bot with feedback
- Follow-up drafts arrive in Telegram → confirm to send

---

## NOTES

- **Google Workspace**: Using Internal OAuth — no external verification needed, no test users required.
- **Groq**: Uses the `groq` Python library (installed via requirements.txt). Sign up with liam@firstwaveai.com.
- **n8n**: Fresh install via npm. Runs at localhost:5678. Use pm2 to keep it running in background.
- **PhantomBuster Phantom ID**: After signing up and adding LinkedIn Search Export, the phantom ID appears in the URL when you open it (e.g. `/phantoms/12345/console`). Note it down — Claude Code will need it in Phase 3.
- **Apollo**: Sign up with liam@firstwaveai.com. Free tier allows unlimited search, 50 email exports/month.
- **All accounts**: Use liam@firstwaveai.com as the signup email for every service.

---

## QUICK REFERENCE — ALL ACCOUNTS

| Service | URL | Key Name in .env |
|---------|-----|-----------------|
| Supabase | supabase.com | SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY |
| Telegram | t.me/BotFather | TELEGRAM_BOT_TOKEN, TELEGRAM_OPERATOR_CHAT_ID |
| Groq | console.groq.com | GROQ_API_KEY |
| Anthropic | console.anthropic.com | ANTHROPIC_API_KEY |
| Google | console.cloud.google.com | GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN |
| Cal.com | cal.com | CALCOM_API_KEY, CALCOM_EVENT_TYPE_ID |
| Apollo.io | app.apollo.io | APOLLO_API_KEY |
| PhantomBuster | phantombuster.com | PHANTOMBUSTER_API_KEY |
