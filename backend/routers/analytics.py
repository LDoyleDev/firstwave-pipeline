"""Analytics router — conversion funnel and pipeline performance metrics."""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from backend.integrations.supabase_client import supabase

logger = logging.getLogger(__name__)
router = APIRouter()


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


def _week_start() -> str:
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


@router.get("/conversion")
def conversion(
    days: int = Query(default=30, ge=1, le=365),
    track: str = Query(default="client"),
) -> dict:
    """Return conversion funnel, rates, breakdowns by market/title/score/subject, and velocity."""
    since = _days_ago(days)

    if track == "client":
        leads = (
            supabase.table("leads")
            .select("id, pipeline_stage, title, location, lead_score, last_contacted_at, updated_at")
            .gte("created_at", since)
            .execute()
            .data or []
        )
        meetings = (
            supabase.table("meetings")
            .select("id, outcome, scheduled_at, lead_id, track")
            .eq("track", "client")
            .gte("scheduled_at", since)
            .execute()
            .data or []
        )
    else:
        leads = []
        meetings = (
            supabase.table("meetings")
            .select("id, outcome, scheduled_at, investor_id, track")
            .eq("track", "investor")
            .gte("scheduled_at", since)
            .execute()
            .data or []
        )

    # --- Funnel ---
    stage_order = ["discovered", "enriched", "review_queue", "contacted", "replied", "meeting_booked", "closed_won"]
    funnel: dict[str, int] = {s: 0 for s in stage_order}
    for l in leads:
        s = l.get("pipeline_stage", "")
        if s in funnel:
            funnel[s] += 1
        elif s in ("met", "closed_won"):
            funnel["closed_won"] += 1

    # Enrich meeting counts from meetings table
    funnel["meeting_booked"] = len(meetings)
    funnel["closed_won"] = sum(1 for m in meetings if m.get("outcome") in ("won", "hot", "closed_won"))

    contacted_n = funnel["contacted"] + funnel["replied"] + funnel["meeting_booked"] + funnel["closed_won"]
    replied_n = funnel["replied"] + funnel["meeting_booked"] + funnel["closed_won"]

    rates = {
        "enrichment_rate": round(
            (funnel["enriched"] + funnel["review_queue"] + contacted_n) / max(funnel["discovered"], 1), 3
        ),
        "contact_to_reply": round(replied_n / max(contacted_n, 1), 3),
        "reply_to_meeting": round(funnel["meeting_booked"] / max(replied_n, 1), 3),
        "meeting_to_close": round(funnel["closed_won"] / max(funnel["meeting_booked"], 1), 3),
    }

    # --- By market (from location field) ---
    market_map: dict[str, dict] = {}
    for l in leads:
        market = _normalise_market(l.get("location", "Unknown"))
        m = market_map.setdefault(market, {"contacted": 0, "replied": 0})
        if l["pipeline_stage"] in ("contacted", "replied", "meeting_booked", "met", "closed_won"):
            m["contacted"] += 1
        if l["pipeline_stage"] in ("replied", "meeting_booked", "met", "closed_won"):
            m["replied"] += 1
    by_market = {
        k: {**v, "reply_rate": round(v["replied"] / max(v["contacted"], 1), 3)}
        for k, v in market_map.items() if v["contacted"] > 0
    }

    # --- By title ---
    title_map: dict[str, dict] = {}
    for l in leads:
        title = _normalise_title(l.get("title", "Unknown"))
        t = title_map.setdefault(title, {"contacted": 0, "replied": 0})
        if l["pipeline_stage"] in ("contacted", "replied", "meeting_booked", "met", "closed_won"):
            t["contacted"] += 1
        if l["pipeline_stage"] in ("replied", "meeting_booked", "met", "closed_won"):
            t["replied"] += 1
    by_title = {
        k: {**v, "reply_rate": round(v["replied"] / max(v["contacted"], 1), 3)}
        for k, v in title_map.items() if v["contacted"] > 0
    }

    # --- By lead score tier ---
    tiers = {"80-100": (80, 100), "60-79": (60, 79), "40-59": (40, 59), "0-39": (0, 39)}
    by_score: dict[str, dict] = {}
    for label, (lo, hi) in tiers.items():
        group = [l for l in leads if lo <= (l.get("lead_score") or 0) <= hi]
        contacted_g = sum(1 for l in group if l["pipeline_stage"] in ("contacted", "replied", "meeting_booked", "met", "closed_won"))
        replied_g = sum(1 for l in group if l["pipeline_stage"] in ("replied", "meeting_booked", "met", "closed_won"))
        if contacted_g > 0:
            by_score[label] = {
                "contacted": contacted_g,
                "replied": replied_g,
                "reply_rate": round(replied_g / contacted_g, 3),
            }

    # --- By subject pattern (L2) ---
    seq_rows = (
        supabase.table("email_sequences")
        .select("subject_pattern, reply_snippet")
        .eq("status", "sent")
        .eq("track", "client")
        .not_.is_("subject_pattern", "null")
        .gte("sent_at", since)
        .execute()
        .data or []
    )
    pattern_map: dict[str, dict] = {}
    for row in seq_rows:
        pat = row.get("subject_pattern", "other")
        p = pattern_map.setdefault(pat, {"sent": 0, "replied": 0})
        p["sent"] += 1
        if row.get("reply_snippet"):
            p["replied"] += 1
    by_subject_pattern = {
        k: {**v, "rate": round(v["replied"] / max(v["sent"], 1), 3)}
        for k, v in pattern_map.items()
    }

    # --- Velocity ---
    week_start = _week_start()
    meetings_this_week = sum(1 for m in meetings if m.get("scheduled_at", "") >= week_start)
    cfg = supabase.table("system_config").select("value").eq("key", "meeting_target_weekly").single().execute()
    meeting_target_weekly = int(cfg.data.get("value", 8)) if cfg.data else 8

    # Days to reply: compare sent_at to when stage changed (approximate via updated_at)
    days_to_reply_list = []
    replied_leads = [l for l in leads if l["pipeline_stage"] in ("replied", "meeting_booked", "met", "closed_won")]
    for l in replied_leads:
        if l.get("last_contacted_at") and l.get("updated_at"):
            try:
                sent = datetime.fromisoformat(l["last_contacted_at"].replace("Z", "+00:00"))
                replied_at = datetime.fromisoformat(l["updated_at"].replace("Z", "+00:00"))
                delta = (replied_at - sent).days
                if 0 <= delta <= 60:
                    days_to_reply_list.append(delta)
            except Exception:
                pass

    avg_days_to_reply = round(sum(days_to_reply_list) / len(days_to_reply_list), 1) if days_to_reply_list else None

    return {
        "funnel": {
            "discovered": funnel["discovered"],
            "enriched": funnel["enriched"],
            "contacted": contacted_n,
            "replied": replied_n,
            "meeting_booked": funnel["meeting_booked"],
            "closed_won": funnel["closed_won"],
        },
        "rates": rates,
        "by_market": by_market,
        "by_title": by_title,
        "by_lead_score_tier": by_score,
        "by_subject_pattern": by_subject_pattern,
        "velocity": {
            "avg_days_to_reply": avg_days_to_reply,
            "meetings_this_week": meetings_this_week,
            "meeting_target_weekly": meeting_target_weekly,
            "on_track": meetings_this_week >= round(meeting_target_weekly * 0.7),
        },
    }


def _normalise_market(location: str) -> str:
    loc = (location or "").lower()
    if any(x in loc for x in ["germany", "berlin", "munich", "hamburg", "austria", "switzerland", "zürich", "vienna", "wien"]):
        return "DACH"
    if any(x in loc for x in ["london", "uk", "england", "scotland", "wales", "manchester"]):
        return "UK"
    if any(x in loc for x in ["australia", "sydney", "melbourne", "brisbane"]):
        return "Australia"
    if any(x in loc for x in ["dubai", "uae", "abu dhabi"]):
        return "UAE"
    if any(x in loc for x in ["singapore"]):
        return "Singapore"
    if any(x in loc for x in ["ireland", "dublin"]):
        return "Ireland"
    if any(x in loc for x in ["india", "mumbai", "bangalore", "delhi"]):
        return "India"
    return location.split(",")[0].strip() if location else "Unknown"


def _normalise_title(title: str) -> str:
    t = (title or "").lower()
    if "revenue" in t and ("vp" in t or "director" in t or "head" in t):
        return "VP/Director Revenue"
    if "cmo" in t or "chief marketing" in t:
        return "CMO"
    if "chief commercial" in t or "cco" in t:
        return "CCO"
    if "general manager" in t or "gm" in t:
        return "General Manager"
    if "ceo" in t or "chief executive" in t:
        return "CEO"
    if "sales" in t and ("vp" in t or "director" in t or "head" in t):
        return "VP/Director Sales"
    if "coo" in t or "chief operating" in t:
        return "COO"
    return title[:30] if title else "Unknown"
