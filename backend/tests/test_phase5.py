"""Phase 5 — Scheduling + Meeting Flow tests (all external calls mocked)."""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

BERLIN_TZ = "Europe/Berlin"
FAKE_MEETING_ID = "meet-uuid-1234"
FAKE_LEAD_ID = "lead-uuid-5678"


def _fake_meeting(overrides: dict = {}) -> dict:
    base = {
        "id": FAKE_MEETING_ID,
        "track": "client",
        "slot_number": 1,
        "scheduled_at": (datetime.now(timezone.utc) + timedelta(minutes=25)).isoformat(),
        "duration_minutes": 20,
        "status": "scheduled",
        "briefing_sent": False,
        "briefing_content": None,
        "voice_feedback_raw": None,
        "follow_up_draft": None,
        "follow_up_sent": False,
        "outcome": None,
        "lead_id": FAKE_LEAD_ID,
        "investor_id": None,
        "leads": {"first_name": "Hans", "last_name": "Müller", "company": "Grand Hotel Group"},
        "investor_targets": None,
    }
    return {**base, **overrides}


# ---------------------------------------------------------------------------
# /meetings/upcoming-briefings
# ---------------------------------------------------------------------------

def test_upcoming_briefings_sends_and_marks():
    """GET /meetings/upcoming-briefings generates briefing and marks briefing_sent."""
    meeting = _fake_meeting()

    with (
        patch("backend.routers.meetings.supabase") as mock_sb,
        patch("backend.routers.meetings._send_telegram"),
        patch("backend.agents.briefing.supabase") as mock_brief_sb,
        patch("backend.agents.briefing.generate") as mock_gen,
    ):
        # Meeting query
        mock_result = MagicMock()
        mock_result.data = [meeting]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = mock_result

        # briefing agent DB fetch
        mock_brief_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=meeting)
        mock_gen.return_value = "Key facts: Hans Müller is CMO at Grand Hotel Group."
        mock_brief_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resp = client.get("/meetings/upcoming-briefings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["checked"] == 1
        assert data["briefings_sent"] == 1


def test_upcoming_briefings_none_due():
    """GET /meetings/upcoming-briefings returns 0 when no meetings are due."""
    with patch("backend.routers.meetings.supabase") as mock_sb:
        mock_result = MagicMock()
        mock_result.data = []
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = mock_result

        resp = client.get("/meetings/upcoming-briefings")
        assert resp.status_code == 200
        assert resp.json()["checked"] == 0


# ---------------------------------------------------------------------------
# /meetings/completed-pending-feedback
# ---------------------------------------------------------------------------

def test_completed_pending_feedback_prompts():
    """GET /meetings/completed-pending-feedback sends Telegram prompt for completed meeting."""
    past_meeting = _fake_meeting({
        "scheduled_at": (datetime.now(timezone.utc) - timedelta(minutes=25)).isoformat(),
        "status": "scheduled",
        "voice_feedback_raw": None,
    })

    with (
        patch("backend.routers.meetings.supabase") as mock_sb,
        patch("backend.routers.meetings._send_telegram") as mock_tg,
    ):
        mock_result = MagicMock()
        mock_result.data = [past_meeting]
        mock_sb.table.return_value.select.return_value.eq.return_value.is_.return_value.lte.return_value.execute.return_value = mock_result
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resp = client.get("/meetings/completed-pending-feedback")
        assert resp.status_code == 200
        data = resp.json()
        assert data["prompted"] == 1
        # Telegram message should mention the attendee name
        call_text = mock_tg.call_args[0][0]
        assert "Hans" in call_text or "Grand Hotel" in call_text


# ---------------------------------------------------------------------------
# /meetings/{id}/confirm-followup
# ---------------------------------------------------------------------------

def test_confirm_followup_sends_email():
    """POST /meetings/{id}/confirm-followup sends follow-up email via Gmail."""
    meeting = _fake_meeting({
        "follow_up_draft": "Hi Hans, great to chat...",
        "follow_up_sent": False,
        "outcome": "warm",
        "leads": {"email": "hans@hotelgroup.de", "first_name": "Hans", "last_name": "Müller"},
    })

    with (
        patch("backend.routers.meetings.supabase") as mock_sb,
        patch("backend.routers.meetings._send_telegram"),
        patch("backend.routers.meetings.send_email") as mock_gmail,
    ):
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=meeting)
        mock_gmail.return_value = "gmail-msg-id-abc"
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resp = client.post(f"/meetings/{FAKE_MEETING_ID}/confirm-followup")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "sent"
        assert data["to"] == "hans@hotelgroup.de"


def test_confirm_followup_no_draft():
    """POST /meetings/{id}/confirm-followup returns 400 when no draft exists."""
    meeting = _fake_meeting({"follow_up_draft": None})

    with patch("backend.routers.meetings.supabase") as mock_sb:
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=meeting)
        resp = client.post(f"/meetings/{FAKE_MEETING_ID}/confirm-followup")
        assert resp.status_code == 400


def test_confirm_followup_already_sent():
    """POST /meetings/{id}/confirm-followup returns 400 when already sent."""
    meeting = _fake_meeting({"follow_up_draft": "some draft", "follow_up_sent": True})

    with patch("backend.routers.meetings.supabase") as mock_sb:
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=meeting)
        resp = client.post(f"/meetings/{FAKE_MEETING_ID}/confirm-followup")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Intent parser — book_meeting
# ---------------------------------------------------------------------------

def test_intent_handle_book_meeting():
    """_handle_book_meeting creates Cal.com booking, Calendar event, and Supabase record."""
    from backend.agents.intent_parser import _handle_book_meeting

    with (
        patch("backend.agents.intent_parser.supabase") as mock_sb,
        patch("backend.agents.intent_parser.calcom_client") as mock_cal,
        patch("backend.agents.intent_parser.calendar_client") as mock_gcal,
        patch("backend.agents.intent_parser.telegram_bot") as mock_tg,
    ):
        # No existing lead found by name
        mock_sb.table.return_value.select.return_value.ilike.return_value.execute.return_value = MagicMock(data=[])

        # Cal.com booking
        mock_cal.create_booking.return_value = {"cal_event_id": "cal-abc-123"}

        # Google Calendar
        mock_gcal.create_event.return_value = "gcal-event-456"

        # Supabase insert
        mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{
            "id": "new-meeting-uuid",
            "slot_number": 1,
            "track": "client",
        }])

        # Telegram
        mock_tg.send_operator_message = AsyncMock()

        result = _handle_book_meeting(
            {"date": "tomorrow", "slot": 1, "attendee_name": ""},
            track="client",
        )

        assert result["success"] is True
        assert "10:30" in result["message"]
        mock_cal.create_booking.assert_called_once()
        mock_gcal.create_event.assert_called_once()


def test_intent_handle_book_meeting_slot_resolution():
    """_handle_book_meeting resolves slot by string name ('two' → slot 2 → 10:50)."""
    from backend.agents.intent_parser import _handle_book_meeting

    with (
        patch("backend.agents.intent_parser.supabase") as mock_sb,
        patch("backend.agents.intent_parser.calcom_client") as mock_cal,
        patch("backend.agents.intent_parser.calendar_client") as mock_gcal,
        patch("backend.agents.intent_parser.telegram_bot") as mock_tg,
    ):
        mock_sb.table.return_value.select.return_value.ilike.return_value.execute.return_value = MagicMock(data=[])
        mock_cal.create_booking.return_value = {"cal_event_id": "x"}
        mock_gcal.create_event.return_value = "y"
        mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "z"}])
        mock_tg.send_operator_message = AsyncMock()

        result = _handle_book_meeting({"date": "tomorrow", "slot": "two"}, track="client")
        assert "10:50" in result["message"]


# ---------------------------------------------------------------------------
# Intent parser — send_followup
# ---------------------------------------------------------------------------

def test_intent_handle_send_followup():
    """_handle_send_followup sends email and updates meeting + pipeline stage."""
    from backend.agents.intent_parser import _handle_send_followup

    meeting = {
        "id": FAKE_MEETING_ID,
        "track": "client",
        "outcome": "warm",
        "follow_up_draft": "Hi Hans, following up...",
        "follow_up_sent": False,
        "lead_id": FAKE_LEAD_ID,
        "investor_id": None,
        "leads": {"email": "hans@hotelgroup.de", "first_name": "Hans", "last_name": "Müller"},
        "investor_targets": None,
    }

    with (
        patch("backend.agents.intent_parser.supabase") as mock_sb,
        patch("backend.agents.intent_parser.gmail_client") as mock_gmail,
        patch("backend.agents.intent_parser.telegram_bot") as mock_tg,
    ):
        mock_sb.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[meeting])
        mock_gmail.send_email.return_value = "gmail-id-xyz"
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_tg.send_operator_message = AsyncMock()

        result = _handle_send_followup({}, track="client")
        assert result["success"] is True
        assert "Hans" in result["message"]
        mock_gmail.send_email.assert_called_once()


def test_intent_handle_send_followup_no_pending():
    """_handle_send_followup returns failure when no pending follow-ups exist."""
    from backend.agents.intent_parser import _handle_send_followup

    with patch("backend.agents.intent_parser.supabase") as mock_sb:
        mock_sb.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

        result = _handle_send_followup({}, track="client")
        assert result["success"] is False
