import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.integrations.supabase_client import supabase
from backend.integrations import gmail_client, telegram_bot

logger = logging.getLogger(__name__)

_BERLIN_OFFSET = timedelta(hours=2)  # CEST — close enough for send-window scheduling
_SEND_WINDOW_START = 9   # 09:00 Berlin
_SEND_WINDOW_END = 17    # 17:00 Berlin


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _business_day_send_time(day_offset: int) -> datetime:
    """Return a random time in the 09:00–17:00 Berlin window on the correct business day.

    Skips weekends. day_offset=0 means today (or next business day if after 17:00 Berlin).
    """
    berlin_now = datetime.now(timezone.utc) + _BERLIN_OFFSET
    target = berlin_now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)

    # Skip weekends (Mon=0 … Sun=6)
    while target.weekday() >= 5:
        target += timedelta(days=1)

    # If today and already past send window, use next business day
    if day_offset == 0 and berlin_now.hour >= _SEND_WINDOW_END:
        target += timedelta(days=1)
        while target.weekday() >= 5:
            target += timedelta(days=1)

    rand_minute = random.randint(0, ((_SEND_WINDOW_END - _SEND_WINDOW_START) * 60) - 1)
    send_berlin = target.replace(
        hour=_SEND_WINDOW_START,
        minute=0,
        second=0,
        microsecond=0,
    ) + timedelta(minutes=rand_minute)

    # Convert back to UTC
    return send_berlin - _BERLIN_OFFSET


def _get_sends_today() -> int:
    """Count emails with status='sent' sent since midnight UTC today."""
    today_start = _now_utc().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    result = (
        supabase.table("email_sequences")
        .select("id", count="exact")
        .eq("status", "sent")
        .gte("sent_at", today_start)
        .execute()
    )
    return result.count or 0


def _daily_send_limit() -> int:
    cfg = supabase.table("system_config").select("value").eq("key", "daily_send_limit").single().execute()
    try:
        return int(cfg.data.get("value", 20)) if cfg.data else 20
    except (TypeError, ValueError):
        return 20


def classify_subject_pattern(subject: str) -> str:
    """Classify a subject line into a pattern type using keyword matching."""
    s = subject.lower()
    if s.endswith("?") or "struggling" in s or "challenge" in s or "how do you" in s:
        return "question"
    if any(x in s for x in ["%", "calls", "minutes", "hours", "staff", "stat", "unanswered"]):
        return "stat"
    if " — " in subject or " - " in subject:
        # name_hook pattern typically has em-dash separator
        return "name_hook"
    if any(x in s for x in ["recover", "save", "reduce", "increase", "boost", "how "]):
        return "benefit"
    if any(x in s for x in ["re:", "following up", "your recent", "your hiring"]):
        return "referral"
    return "other"


def _send_telegram(text: str) -> None:
    """Fire-and-forget Telegram notification."""
    try:
        asyncio.get_event_loop().run_until_complete(telegram_bot.send_operator_message(text))
    except RuntimeError:
        # If no running event loop (e.g. in tests), create a new one
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(telegram_bot.send_operator_message(text))
        finally:
            loop.close()
    except Exception:
        logger.exception("Failed to send Telegram notification")


def schedule_sequence(entity_id: str, track: str) -> None:
    """Create email_sequences records for a newly approved lead/investor.

    Steps:
      1 — Email 1 on Day 0 (send immediately after approval)
      2 — Email 2 on Day 7
      3 — Final touch on Day 14
      LinkedIn reminder on Day 3 via Telegram (not an email step)

    Args:
        entity_id: UUID of lead (client) or investor_target (investor)
        track: 'client' or 'investor'
    """
    now = _now_utc()

    if track == "client":
        row = supabase.table("leads").select("*").eq("id", entity_id).single().execute().data
        lead_id = entity_id
        investor_id = None
        email = row.get("email", "")
        name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
        email_1_raw = row.get("outreach_email_1") or "{}"
        email_2_raw = row.get("outreach_email_2") or "{}"
        try:
            import json
            e1 = json.loads(email_1_raw) if isinstance(email_1_raw, str) else email_1_raw
            e2 = json.loads(email_2_raw) if isinstance(email_2_raw, str) else email_2_raw
        except Exception:
            e1 = {}
            e2 = {}
        email_1_subject = e1.get("subject", "")
        email_1_body = e1.get("body", "")
        email_2_subject = e2.get("subject", "")
        email_2_body = e2.get("body", "")
        company = row.get("company", "")
    else:
        row = supabase.table("investor_targets").select("*").eq("id", entity_id).single().execute().data
        lead_id = None
        investor_id = entity_id
        email = row.get("contact_email", "")
        name = row.get("contact_name") or row.get("firm_name", "")
        draft_raw = row.get("outreach_draft") or "{}"
        try:
            import json
            draft = json.loads(draft_raw) if isinstance(draft_raw, str) else draft_raw
        except Exception:
            draft = {}
        e1 = draft.get("email_1", {})
        e2 = draft.get("email_2", {})
        email_1_subject = e1.get("subject", "")
        email_1_body = e1.get("body", "")
        email_2_subject = e2.get("subject", "")
        email_2_body = e2.get("body", "")
        company = row.get("firm_name", "")

    steps = [
        {
            "lead_id": lead_id,
            "investor_id": investor_id,
            "track": track,
            "step_number": 1,
            "step_type": "email",
            "subject": email_1_subject,
            "body": email_1_body,
            "subject_pattern": classify_subject_pattern(email_1_subject),
            "scheduled_for": _business_day_send_time(0).isoformat(),
            "status": "pending",
        },
        {
            "lead_id": lead_id,
            "investor_id": investor_id,
            "track": track,
            "step_number": 2,
            "step_type": "email",
            "subject": email_2_subject,
            "body": email_2_body,
            "subject_pattern": classify_subject_pattern(email_2_subject),
            "scheduled_for": _business_day_send_time(7).isoformat(),
            "status": "pending",
        },
        {
            "lead_id": lead_id,
            "investor_id": investor_id,
            "track": track,
            "step_number": 3,
            "step_type": "follow_up",
            "subject": f"Re: {email_1_subject}",
            "body": "",
            "scheduled_for": _business_day_send_time(14).isoformat(),
            "status": "pending",
        },
    ]

    supabase.table("email_sequences").insert(steps).execute()
    logger.info("Scheduled 3-step sequence for %s (%s)", entity_id, track)

    # Day 3: LinkedIn reminder via Telegram (not an email)
    linkedin_url = row.get("linkedin_url") or row.get("contact_linkedin") or "find on LinkedIn"
    reminder = (
        f"LinkedIn Day 3 reminder\n"
        f"Send a connection request to {name} at {company}\n"
        f"{linkedin_url}"
    )
    # We store as a pending Telegram notification by scheduling a sequence record with step_type=linkedin_touch
    supabase.table("email_sequences").insert({
        "lead_id": lead_id,
        "investor_id": investor_id,
        "track": track,
        "step_number": 0,  # out-of-band, not counted as email step
        "step_type": "linkedin_touch",
        "subject": "LinkedIn connection reminder",
        "body": reminder,
        "scheduled_for": (now + timedelta(days=3)).isoformat(),
        "status": "pending",
    }).execute()


def process_due_sequences() -> dict:
    """Send all email sequences that are due now.

    For each pending sequence step due <= NOW():
    - Skip if the entity has already replied (sequence complete)
    - Send email via Gmail
    - Update sequence record: sent_at, status='sent', gmail_message_id
    - For linkedin_touch steps: send Telegram reminder instead of email

    Returns:
        Summary dict with counts.
    """
    now = _now_utc()
    result = supabase.table("email_sequences").select(
        "*, leads(id, first_name, last_name, email, pipeline_stage, outreach_approved), "
        "investor_targets(id, firm_name, contact_name, contact_email, pipeline_stage, outreach_approved)"
    ).eq("status", "pending").lte("scheduled_for", now.isoformat()).execute()

    sequences = result.data or []
    sent = 0
    skipped = 0
    errors = 0
    daily_limit = _daily_send_limit()

    for seq in sequences:
        seq_id = seq["id"]
        track = seq["track"]
        step_type = seq.get("step_type", "email")

        try:
            if track == "client":
                entity = seq.get("leads") or {}
                email = entity.get("email", "")
                name = f"{entity.get('first_name', '')} {entity.get('last_name', '')}".strip()
                stage = entity.get("pipeline_stage", "")
                approved = entity.get("outreach_approved", False)
            else:
                entity = seq.get("investor_targets") or {}
                email = entity.get("contact_email", "")
                name = entity.get("contact_name") or entity.get("firm_name", "")
                stage = entity.get("pipeline_stage", "")
                approved = entity.get("outreach_approved", False)

            # Skip if already replied
            if stage == "replied":
                supabase.table("email_sequences").update({
                    "status": "skipped",
                }).eq("id", seq_id).execute()
                skipped += 1
                continue

            # Gate: outreach_approved must be true
            if not approved:
                logger.warning("Sequence %s skipped — outreach not approved", seq_id)
                skipped += 1
                continue

            if step_type == "linkedin_touch":
                _send_telegram(f"LinkedIn reminder:\n{seq.get('body', '')}")
                supabase.table("email_sequences").update({
                    "status": "sent",
                    "sent_at": now.isoformat(),
                }).eq("id", seq_id).execute()
                sent += 1
                continue

            # Daily send limit — reschedule to next business day if at cap
            if _get_sends_today() >= daily_limit:
                next_slot = _business_day_send_time(1)
                supabase.table("email_sequences").update({
                    "scheduled_for": next_slot.isoformat(),
                }).eq("id", seq_id).execute()
                logger.info("Daily limit reached — rescheduled sequence %s to %s", seq_id, next_slot.date())
                skipped += 1
                continue

            if not email:
                logger.warning("Sequence %s skipped — no email address", seq_id)
                skipped += 1
                continue

            # Find the previous step's gmail_message_id for threading
            reply_to = None
            if seq["step_number"] > 1:
                prev = supabase.table("email_sequences").select("gmail_message_id").eq(
                    "lead_id" if track == "client" else "investor_id",
                    seq.get("lead_id") or seq.get("investor_id")
                ).eq("step_number", seq["step_number"] - 1).eq("status", "sent").execute()
                if prev.data:
                    reply_to = prev.data[0].get("gmail_message_id")

            body = seq.get("body", "")
            if step_type == "follow_up" and not body.strip():
                from backend.agents.followup import generate_closing_email
                entity_id = seq.get("lead_id") or seq.get("investor_id")
                original_subject = seq.get("subject", "").removeprefix("Re: ")
                body = generate_closing_email(entity_id, track, original_subject)
                supabase.table("email_sequences").update({"body": body}).eq("id", seq_id).execute()

            gmail_id = gmail_client.send_email(
                to=email,
                subject=seq.get("subject", ""),
                body=body,
                reply_to_message_id=reply_to,
            )

            supabase.table("email_sequences").update({
                "status": "sent",
                "sent_at": now.isoformat(),
                "gmail_message_id": gmail_id,
            }).eq("id", seq_id).execute()

            # Update lead/investor last_contacted_at
            table = "leads" if track == "client" else "investor_targets"
            entity_id = seq.get("lead_id") or seq.get("investor_id")
            supabase.table(table).update({
                "last_contacted_at": now.isoformat(),
                "pipeline_stage": "contacted",
                "sequence_step": seq["step_number"],
            }).eq("id", entity_id).execute()

            logger.info("Sent sequence %s step %d to %s", seq_id, seq["step_number"], email)
            sent += 1

        except Exception:
            logger.exception("Error processing sequence %s", seq_id)
            errors += 1

    summary = {"sent": sent, "skipped": skipped, "errors": errors, "total": len(sequences)}
    logger.info("Sequence run complete: %s", summary)
    return summary


def check_all_replies() -> None:
    """Check all active sequences for email replies and update pipeline accordingly.

    For any sequence with a reply:
    - Update lead/investor pipeline_stage to 'replied'
    - Mark remaining pending sequences as 'skipped'
    - Send Telegram notification to operator
    """
    # Gather all active sequences that have been sent (have gmail_message_id)
    result = supabase.table("email_sequences").select(
        "id, track, step_number, gmail_message_id, lead_id, investor_id, "
        "leads(first_name, last_name, company), "
        "investor_targets(contact_name, firm_name)"
    ).eq("status", "sent").not_.is_("gmail_message_id", "null").execute()

    sequences = result.data or []
    if not sequences:
        return

    gmail_message_ids = [s["gmail_message_id"] for s in sequences if s.get("gmail_message_id")]
    if not gmail_message_ids:
        return

    try:
        replies = gmail_client.check_replies(gmail_message_ids)
    except Exception:
        logger.exception("Failed to check replies via Gmail")
        return

    # Map gmail_message_id -> reply_snippet for all threads that have a reply
    replied_map: dict[str, str | None] = {
        r["gmail_message_id"]: r.get("reply_snippet")
        for r in replies if r.get("replied")
    }
    if not replied_map:
        return

    for seq in sequences:
        gmail_id = seq.get("gmail_message_id")
        if gmail_id not in replied_map:
            continue

        # Store the reply snippet on the sequence record for the reply auto-draft feature
        supabase.table("email_sequences").update({
            "reply_snippet": replied_map[gmail_id],
        }).eq("id", seq["id"]).execute()

        track = seq["track"]
        lead_id = seq.get("lead_id")
        investor_id = seq.get("investor_id")
        entity_id = lead_id or investor_id
        table = "leads" if track == "client" else "investor_targets"

        if track == "client":
            entity = seq.get("leads") or {}
            name = f"{entity.get('first_name', '')} {entity.get('last_name', '')}".strip()
            company = entity.get("company", "")
        else:
            entity = seq.get("investor_targets") or {}
            name = entity.get("contact_name") or entity.get("firm_name", "")
            company = entity.get("firm_name", "")

        # Update entity stage
        supabase.table(table).update({
            "pipeline_stage": "replied",
        }).eq("id", entity_id).execute()

        # Skip remaining pending steps for this entity
        supabase.table("email_sequences").update({
            "status": "skipped",
        }).eq("lead_id" if track == "client" else "investor_id", entity_id).eq(
            "status", "pending"
        ).execute()

        reply_snippet = replied_map.get(gmail_id) or ""
        lead_context = {
            "name": name,
            "company": company,
            "title": entity.get("title", "") if track == "client" else "",
            "subject": seq.get("subject", ""),
        }

        # Classify the reply
        classification: dict = {"outcome": "question", "summary": reply_snippet[:100], "next_action": "Review manually"}
        try:
            from backend.agents.reply_classifier import classify_reply
            classification = classify_reply(reply_snippet, lead_context)
        except Exception:
            logger.exception("Reply classification failed for %s", entity_id)

        # Generate reply draft (all tracks require review — no auto-send)
        draft = ""
        try:
            from backend.agents.followup import generate_reply_draft
            draft = generate_reply_draft(entity_id, track, reply_snippet, classification)
            if track == "client" and lead_id:
                supabase.table("leads").update({"pending_reply_draft": draft}).eq("id", lead_id).execute()
        except Exception:
            logger.exception("Reply draft generation failed for %s", entity_id)

        outcome = classification.get("outcome", "")
        summary = classification.get("summary", reply_snippet[:100])
        next_action = classification.get("next_action", "")
        outcome_emoji = {
            "positive": "✅", "objection": "⚠️", "question": "❓",
            "wrong_person": "↗️", "out_of_office": "🏖️",
        }.get(outcome, "💬")

        telegram_msg = (
            f"💬 Reply from {name} ({company})\n"
            f'"{reply_snippet[:200]}"\n\n'
            f"Outcome: {outcome.upper()} {outcome_emoji}\n"
            f"Summary: {summary}\n"
            f"Next: {next_action}"
        )
        if draft:
            telegram_msg += (
                f"\n\nDraft reply:\n"
                f"{'─' * 30}\n"
                f"{draft[:600]}\n"
                f"{'─' * 30}\n"
                "Reply YES to send · EDIT to revise in dashboard"
            )

        _send_telegram(telegram_msg)
        logger.info("Reply detected for %s (%s), outcome=%s", entity_id, track, outcome)


def identify_reengagement_candidates(days_cold: int = 30) -> list[str]:
    """Find leads in 'contacted' stage that have been cold for days_cold days.

    Excludes leads that already have a re-engagement step sent.

    Args:
        days_cold: Number of days since last contact before a lead qualifies.

    Returns:
        List of lead UUIDs.
    """
    from datetime import timedelta
    cutoff = (_now_utc() - timedelta(days=days_cold)).isoformat()

    rows = (
        supabase.table("leads")
        .select("id, last_contacted_at, reengagement_sent_at")
        .eq("pipeline_stage", "contacted")
        .lt("last_contacted_at", cutoff)
        .is_("reengagement_sent_at", "null")
        .execute()
        .data or []
    )

    # Confirm all sequence steps are sent/skipped (no pending steps remaining)
    candidates = []
    for row in rows:
        lead_id = row["id"]
        pending = (
            supabase.table("email_sequences")
            .select("id", count="exact")
            .eq("lead_id", lead_id)
            .eq("status", "pending")
            .execute()
        ).count or 0
        if pending == 0:
            candidates.append(lead_id)

    logger.info("Re-engagement candidates (%d day threshold): %d leads", days_cold, len(candidates))
    return candidates
