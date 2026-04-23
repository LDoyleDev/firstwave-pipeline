"""Status router — morning brief and velocity endpoints."""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from backend.integrations.supabase_client import supabase

logger = logging.getLogger(__name__)
router = APIRouter()

_BERLIN_OFFSET = timedelta(hours=2)  # CEST; close enough for brief formatting


def _today_berlin() -> str:
    return (datetime.now(timezone.utc) + _BERLIN_OFFSET).strftime("%a %d %b")


def _week_start_utc() -> str:
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _thirty_days_ago() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()


@router.get("/morning-brief")
def morning_brief() -> dict:
    """Return a pre-formatted Telegram morning brief with KPIs and today's action list."""
    week_start = _week_start_utc()
    thirty_ago = _thirty_days_ago()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    # --- Client pipeline counts ---
    leads_all = supabase.table("leads").select("id, pipeline_stage, last_contacted_at, reengagement_sent_at").execute().data or []
    discovered = sum(1 for l in leads_all if l["pipeline_stage"] == "discovered")
    enriched_count = sum(1 for l in leads_all if l["pipeline_stage"] == "enriched")
    review_q = sum(1 for l in leads_all if l["pipeline_stage"] == "review_queue")
    active_seq = sum(1 for l in leads_all if l["pipeline_stage"] == "contacted")
    replied_week = sum(
        1 for l in leads_all
        if l["pipeline_stage"] == "replied"
        # approximate — we just want leads that moved to replied this week
    )
    contacted_30d = sum(
        1 for l in leads_all
        if l["pipeline_stage"] in ("contacted", "replied", "meeting_booked")
        and (l.get("last_contacted_at") or "") >= thirty_ago
    )
    replied_30d = sum(1 for l in leads_all if l["pipeline_stage"] == "replied")
    reply_rate_30d = round(replied_30d / max(contacted_30d, 1) * 100, 1)

    # Stale leads: in 'contacted' > 30 days with no further action
    stale = [
        l for l in leads_all
        if l["pipeline_stage"] == "contacted"
        and (l.get("last_contacted_at") or "") < thirty_ago
        and not l.get("reengagement_sent_at")
    ]

    # --- Investor counts ---
    investors = supabase.table("investor_targets").select("id, pipeline_stage").execute().data or []
    inv_total = len(investors)
    inv_contacted = sum(1 for i in investors if i["pipeline_stage"] in ("contacted", "replied", "meeting_booked", "met"))
    inv_replied = sum(1 for i in investors if i["pipeline_stage"] in ("replied", "meeting_booked", "met"))

    # --- Emails sent this week ---
    sent_week = (
        supabase.table("email_sequences")
        .select("id", count="exact")
        .eq("status", "sent")
        .gte("sent_at", week_start)
        .execute()
    ).count or 0

    # --- Meetings today ---
    meetings_today = (
        supabase.table("meetings")
        .select("id, scheduled_at, track, leads(first_name, last_name), investor_targets(contact_name, firm_name)")
        .eq("status", "scheduled")
        .gte("scheduled_at", today_start)
        .order("scheduled_at")
        .execute()
        .data or []
    )

    # --- Pending reply drafts ---
    pending_replies = (
        supabase.table("leads")
        .select("id, first_name, last_name, company")
        .eq("pipeline_stage", "replied")
        .not_.is_("pending_reply_draft", "null")
        .execute()
        .data or []
    )

    # --- LinkedIn day-3 reminders due today ---
    linkedin_due = (
        supabase.table("email_sequences")
        .select("id", count="exact")
        .eq("step_type", "linkedin_touch")
        .eq("status", "pending")
        .lte("scheduled_for", datetime.now(timezone.utc).isoformat())
        .execute()
    ).count or 0

    # --- Weekly meeting target ---
    cfg = supabase.table("system_config").select("value").eq("key", "meeting_target_weekly").single().execute()
    meeting_target = int(cfg.data.get("value", 8)) if cfg.data else 8
    meetings_this_week = (
        supabase.table("meetings")
        .select("id", count="exact")
        .in_("status", ["scheduled", "completed"])
        .gte("scheduled_at", week_start)
        .execute()
    ).count or 0

    # --- Format brief ---
    divider = "━" * 25
    action_lines = []
    n = 1

    if review_q > 0:
        action_lines.append(f"{n}. 📋 {review_q} drafts in review queue — approve before 10:30")
        n += 1

    for m in meetings_today:
        track = m.get("track", "client")
        entity = m.get("leads") or m.get("investor_targets") or {}
        if track == "client":
            name = f"{entity.get('first_name', '')} {entity.get('last_name', '')}".strip()
        else:
            name = entity.get("contact_name") or entity.get("firm_name", "")
        time_str = m.get("scheduled_at", "")[:16].replace("T", " ")
        action_lines.append(f"{n}. 📞 {time_str} — {name}")
        n += 1

    for lead in pending_replies[:3]:
        name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
        action_lines.append(f"{n}. 💬 {name} ({lead.get('company', '')}) replied — draft ready, say YES to send")
        n += 1

    if linkedin_due > 0:
        action_lines.append(f"{n}. 🔗 {linkedin_due} LinkedIn day-3 reminder(s) due")
        n += 1

    if enriched_count > 0:
        action_lines.append(f"{n}. ⚡ {enriched_count} leads enriched and ready for outreach generation")
        n += 1

    if discovered > 0:
        action_lines.append(f"{n}. 🔍 {discovered} discovered leads waiting to enrich")
        n += 1

    if stale:
        action_lines.append(f"{n}. ⚠️  {len(stale)} leads stuck in contacted > 30 days — consider re-engagement")
        n += 1

    message = (
        f"📊 FIRSTWAVE — {_today_berlin()}\n"
        f"{divider}\n"
        f"CLIENT PIPELINE\n"
        f"  Discovered: {discovered}   Enriched: {enriched_count}\n"
        f"  Review queue: {review_q}   Active: {active_seq}\n"
        f"  Reply rate (30d): {reply_rate_30d}%   Replies: {replied_30d}\n\n"
        f"INVESTOR PIPELINE\n"
        f"  Contacted: {inv_contacted}/{inv_total}   Replies: {inv_replied}\n\n"
        f"SENT THIS WEEK: {sent_week} emails\n"
        f"MEETINGS THIS WEEK: {meetings_this_week}/{meeting_target} target\n"
        f"{divider}\n"
    )

    if action_lines:
        message += "🎯 TODAY'S ACTIONS\n" + "\n".join(action_lines)
    else:
        message += "✅ Nothing urgent today — keep the pipeline flowing."

    return {"message": message, "stats": {
        "discovered": discovered,
        "enriched": enriched_count,
        "review_queue": review_q,
        "active_in_sequence": active_seq,
        "reply_rate_30d": reply_rate_30d,
        "replied_total": replied_30d,
        "stale_leads": len(stale),
        "meetings_today": len(meetings_today),
        "meetings_this_week": meetings_this_week,
        "meeting_target_weekly": meeting_target,
    }}
