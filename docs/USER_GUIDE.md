# FirstWave Pipeline — Operator User Guide

**For:** Liam Doyle  
**Purpose:** How to run your sales pipeline through voice and the dashboard  
**Primary interface:** Telegram bot on your phone  
**Secondary interface:** http://100.113.88.92:5173 (dashboard, any browser)

---

## How the system works

You run two parallel outreach tracks at the same time:

- **Client track** — finding and booking calls with hotel group CMOs, VPs of Revenue, and GMs across DACH, UK, and Nordics to sell First Wave AI
- **Investor track** — reaching out to the 50 pre-loaded VCs and angels to close the $750K seed round

The system handles discovery, enrichment, email drafting, sending, reply detection, and meeting prep. Your job is to make decisions at three moments: **approving outreach before it sends**, **booking and running meetings**, and **giving feedback after meetings so follow-ups write themselves**.

Everything else is automated.

---

## Getting started each day

Open Telegram. The bot sends you a morning summary automatically at 08:00 Berlin time. It will tell you:
- How many leads are waiting in the review queue
- How many emails went out overnight
- Whether anyone has replied
- What meetings you have today

If you want the summary at any time, just type: **"What's my pipeline status?"**

---

## Your daily routine

### Morning (before 10:30)

**1. Check the review queue**

Either open the dashboard at http://100.113.88.92:5173/review, or ask the bot:

> *"Show me the review queue"*

The queue shows every outreach draft the AI has written but hasn't sent yet. For each one you'll see the lead's name, company, title, lead score (0–100), and the pain signals the AI found. Expand to read the full email draft before approving.

**Your decision per card: Approve, Reject, or Edit.**

- **Approve** → email goes into the send queue. Step 1 sends today; step 2 sends on day 7; step 3 on day 14. A LinkedIn reminder lands in Telegram on day 3.
- **Reject** → lead is marked closed. No email ever sends. Use this for clearly wrong fits.
- **Edit** → inline editor opens. Change the subject or body, then explicitly approve. The system never auto-approves after an edit.

**Important:** No email ever sends without your explicit approval. The `outreach_approved` flag must be true in the database first.

After your first 20 approvals on a track, the system flips to auto-approve mode. You can flip back to manual any time by asking the bot: *"Switch client review to manual mode".*

**2. Book any meetings**

If a lead has replied or you want to proactively book someone, say to the bot:

> *"Book a client meeting with Hans from Grand Hotel Group tomorrow in slot one"*

The system looks up Hans in the database, finds his email, creates a Cal.com booking, adds it to your Google Calendar, and confirms via Telegram. Meeting slots are always 10:30, 10:50, or 11:10 Berlin time — no other times.

---

### Meeting window (10:30–11:30)

**30 minutes before each meeting:**

A briefing arrives automatically in Telegram. It includes:
- Who you're meeting and their role
- Company context and recent news
- The pain signals the AI identified
- Personalisation hooks specific to this person
- Recommended opening line

Read it. Use it. It's written by the same AI that wrote the outreach, so it knows exactly what was said in the emails.

**During the meeting:** Run the call. No system interaction needed.

**After the meeting:** Wait for the Telegram prompt — it arrives automatically 20 minutes after the slot time. It asks: *"How did the meeting with [Name] go? Send a voice note."*

Send a voice note. Say whatever comes naturally — what happened, their level of interest, any specific things they mentioned, what you promised to do next. You don't need to follow a format. Examples:

> *"Really good call. Marcus is definitely interested, said they had the exact problem with unanswered calls at their Maldives properties. He wants to see the deck and talk to Philip. Follow up in two days."*

> *"Wasn't the right fit — they outsource all front desk to a third party and aren't looking to change. Archive this one."*

> *"Warm call, not hot. She said the timing isn't right until Q3 but asked me to follow up in June. Worth staying in the sequence."*

The AI transcribes, classifies the outcome (hot/warm/cold/dead), drafts the follow-up email, and sends you a preview in Telegram:

> *"Got it. Outcome: warm. Here's your follow-up draft: [draft text]. Reply YES to send it."*

Read the draft. If it's right, reply **YES** or say **"Yes, send it"** and it goes. If you want to tweak it, say **"Don't send — I'll edit it in the dashboard"** and go to http://100.113.88.92:5173/meetings to edit inline.

---

### Between meetings / ongoing

**Checking for replies**

Reply detection runs automatically every 2 hours. When someone replies, you get an instant Telegram notification:

> *"Reply from Marcus Müller at Grand Hotel Group — check your inbox"*

The system automatically pauses the sequence for that lead (no more automated emails) and moves them to the `replied` stage. Your next step is manual — take it from the inbox.

**LinkedIn day-3 reminders**

Three days after an email goes out, Telegram sends you:

> *"LinkedIn Day 3 reminder: Send a connection request to [Name] at [Company] — [LinkedIn URL]"*

This is a manual action. Open LinkedIn, send the request. The system can't do this for you, but it makes sure you don't forget.

---

## The dashboard

Access at http://100.113.88.92:5173 (password in `.env`). Works on mobile via Tailscale.

### Dashboard home (/)

Today's three meeting slots at the top — green if booked, grey if empty. Below that: review queue count, active sequences, replies this week, and a live activity feed showing the last 10 system events.

### Client pipeline (/clients)

Kanban board showing all leads across 11 stages:

`discovered → enriched → review_queue → approved → contacted → replied → meeting_booked → met → follow_up → closed_won / closed_lost`

Drag a card to move a lead between stages manually. Click any card to open the full profile — enrichment data, all emails sent, sequence status, LinkedIn URL.

### Investor pipeline (/investors)

Table view grouped by tier. Each row shows the firm, contact name, stage, why-fit note, and whether you're leading the outreach (Liam Leads = Yes/No). Click any row for the full profile including the warm path notes and outreach draft.

**Tier priority:**
- **Tier 1 (Hospitality VCs):** You lead. Open with operator credibility. Use the warm path notes — they're specific to your Selina/A&O background and each fund's thesis.
- **Tier 2 (Vertical AI):** Apply via intake forms AND warm intro simultaneously. Philip leads applications; you're referenced for domain credibility.
- **Tier 3 (Accelerators):** Philip leads applications.
- **Tier 5 (European):** You lead, person-to-person. Not via formal pitch process.
- **Tier 6 (Angels):** Direct, one-paragraph DM on LinkedIn or Twitter/X. No deck.

### Review queue (/review)

Split view: client drafts on the left, investor drafts on the right. Approve, reject, or edit inline. Keyboard shortcuts: **A** = approve, **R** = reject, **E** = edit, **→** = next card.

### Meetings (/meetings)

Week view showing the 10:30–11:30 block for each day. Today is highlighted. Click a booked slot to see the briefing content and outcome (for past meetings). Click an empty slot to book manually.

### Voice log (/voice)

Every voice command you've ever sent, with the transcript, what the AI understood, what action it took, and whether it succeeded. Useful for checking that the bot understood you correctly.

---

## Complete voice command reference

Send any of these as a voice note or typed message to the Telegram bot. The AI parses natural language — you don't need exact wording.

### Pipeline status

| Say something like | What happens |
|---|---|
| "What's my pipeline status?" | Full summary: lead counts, review queue, active sequences, investor stages |
| "How many leads do I have?" | Same summary |
| "What should I do next?" | Returns the most urgent action (review queue count, next meeting, etc.) |
| "Show me the review queue" | Count of pending approvals split by track |

### Client leads

| Say something like | What happens |
|---|---|
| "Find me five hotel CMOs in Germany" | Queues a discovery run via Apollo with those filters |
| "Find CMOs at hotel groups in the UK and Nordics" | Same with different geography |
| "Enrich the lead for Anna Schmidt" | Triggers Claude enrichment for that lead |
| "Approve the outreach for Hans from Grand Hotel" | Approves and schedules sequence |
| "Reject the lead for the boutique hotel in Vienna" | Closes as lost |
| "Pause the sequence for Marcus Müller" | Stops automated follow-ups |

### Investor pipeline

| Say something like | What happens |
|---|---|
| "Who is Seedcamp?" | Returns full investor profile: contact, tier, why-fit, warm path, current stage |
| "Find Earlybird Ventures" | Same lookup |
| "What stage is Fifth Wall at?" | Returns current pipeline stage for that investor |

### Meeting booking

| Say something like | What happens |
|---|---|
| "Book a client meeting tomorrow in slot one" | Creates 10:30 booking for tomorrow |
| "Book an investor meeting with Brendan Wallace on Friday in slot two" | Looks up Fifth Wall, creates 10:50 booking |
| "Book a call with Anna Schmidt next Monday in the last slot" | Creates 11:10 booking |
| "Cancel my meeting tomorrow" | Asks which meeting, then cancels Cal.com + Calendar + updates DB |

Slot reference: **slot one = 10:30, slot two = 10:50, slot three / last slot = 11:10**

### Post-meeting feedback

| Say something like | What happens |
|---|---|
| "The meeting went well, he wants a demo, follow up in two days" | Generates follow-up draft, sends preview to Telegram |
| "Wasn't a fit — archive this one" | Classifies as dead, marks as closed_lost |
| "Warm call, she asked me to follow up in June" | Classifies as warm, sets next_action_at to June |
| "Yes" / "Yes, send it" / "Send the follow-up" | Sends the pending draft email |

### Sequences and follow-ups

| Say something like | What happens |
|---|---|
| "Who has replied this week?" | Lists leads/investors in 'replied' stage from the last 7 days |
| "Pause all sequences for the investor track" | Not yet automated — do this per-investor via dashboard |

---

## Lead scoring explained

Every enriched lead gets a score from 0–100. The AI assigns this based on:

- **80–100 (Hot):** Clear ICP fit, strong pain signals found (e.g. job postings for CX roles, public complaints about OTA dependency, expansion news), warm path exists
- **60–79 (Warm):** Good ICP fit, some pain signals, cold outreach justified
- **40–59 (Lukewarm):** Possible fit, limited signals, lower priority
- **Below 40 (Cold):** Poor fit — consider rejecting in review queue

In the review queue, leads are sorted highest score first. If your queue is backed up, approve the top 5 and reject anything below 40.

---

## Email sequences explained

Once you approve a lead's outreach, three things happen automatically:

| Day | Action |
|---|---|
| Day 0 | **Email 1 sent** — the Challenger Sale opener. Goal: a 20-minute call. No pitch. |
| Day 3 | **Telegram reminder** — send a LinkedIn connection request to this person |
| Day 7 | **Email 2 sent** — follow-up with a new data point, if no reply |
| Day 14 | **Email 3 sent** — short "closing the loop" email, or archive |

If the person replies at any point, the sequence stops immediately. You get a Telegram notification and the remaining steps are cancelled.

**The system never sends an email without your approval.** The `outreach_approved` flag is checked before every single send.

---

## Investor outreach — how it's different

Investor outreach uses a completely separate system prompt and tone:

- **Email 1 goal:** Get a 20-minute exploratory call. Never attach the deck in email 1.
- **Pitch arc embedded in every message:** Pain (unanswered calls / OTA bleed) → Why now (AI is ready) → Why us (Philip's AWS + Liam's operator credibility + live pilot) → Why this beats alternatives (not a chatbot) → Ask ($750K, $6M pre-money)
- **By tier:**
  - Tier 1: Lead with your operator credibility. Reference their portfolio hospitality companies.
  - Tier 2: Lead with market data and traction numbers (7 LOIs, pilot proof).
  - Tier 5: Person-to-person, informal. Not via formal pitch channels.
  - Tier 6 (angels): One paragraph DM. Twitter/X or LinkedIn. No formality.

The warm path notes in each investor's profile (visible in the dashboard at `/investors`) tell you specifically how your background connects to that investor's thesis. Use them.

---

## What to do when something goes wrong

**The bot didn't understand my voice note**

Check the Voice Log at http://100.113.88.92:5173/voice — you'll see exactly what the AI parsed. If the intent is wrong, rephrase and try again. The bot always replies with what it understood, so you'll know immediately if it misread you.

**A follow-up email was sent and I want to cancel it**

You can't unsend an email, but you can pause the sequence so no more steps go out. Say: *"Pause the sequence for [Name]"* or update the sequence status to `skipped` via the API.

**The AI wrote a terrible outreach draft**

In the review queue, click Edit and rewrite it. The AI does not auto-approve after an edit — you still have to explicitly approve. Alternatively, say to the bot: *"Regenerate the outreach for [Name] with feedback: [your feedback]"* and the AI will rewrite it incorporating your notes.

**A lead moved to the wrong stage**

Open the client pipeline at `/clients`, drag the card to the correct stage. Stage changes write back to Supabase immediately.

**The bot isn't responding**

The Telegram webhook requires the backend to be running and reachable. Check that `uvicorn` is running on the desktop. If working from mobile, check Tailscale is connected.

**Two meetings got booked in the same slot**

The system checks Cal.com for availability before booking, but doesn't yet enforce uniqueness at the Supabase level. If this happens, cancel one via the dashboard at `/meetings` and then cancel the corresponding Cal.com booking manually.

---

## Key numbers to know

| Metric | Value |
|---|---|
| Meeting slots | 10:30, 10:50, 11:10 Berlin time — no other times |
| Sequence steps | Day 0, Day 7, Day 14 (email); Day 3 (LinkedIn reminder) |
| Enrichment batch size | Max 5 leads at a time |
| Daily discovery limit | 20 new leads per day |
| Auto-approve threshold | 20 approvals per track |
| Raise target | $750K at $6M pre-money |
| Pilot proof | 5,817 staff minutes saved; $2,496/month savings |
| Unanswered calls stat | 21% — use in every client opener |

---

## Quick reference card

**Morning:** Check bot → review queue → approve/reject drafts  
**Pre-meeting:** Read briefing (arrives automatically 30 min before)  
**Post-meeting:** Reply to bot's voice note prompt → say YES to send follow-up  
**Replies:** Bot alerts you automatically — take it from your inbox  
**LinkedIn:** Bot reminds you on day 3 of every sequence  
**Investors:** Use warm path notes in dashboard before each investor outreach  

---

*For technical issues, see README.md. For architecture details, see docs/FIRSTWAVE_SYSTEM_CONTEXT.md.*
