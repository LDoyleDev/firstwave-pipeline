"""Phase 4 — Outreach Engine tests (all external calls mocked)."""
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

FAKE_LEAD_ID = "lead-uuid-1111"
FAKE_INVESTOR_ID = "inv-uuid-2222"


def _fake_lead(overrides: dict = {}) -> dict:
    base = {
        "id": FAKE_LEAD_ID,
        "first_name": "Hans",
        "last_name": "Müller",
        "email": "hans@hotelgroup.de",
        "company": "Grand Hotel Group",
        "linkedin_url": "https://linkedin.com/in/hansmueller",
        "title": "CMO",
        "pipeline_stage": "review_queue",
        "lead_score": 75,
        "outreach_approved": False,
        "outreach_email_1": json.dumps({"subject": "Quick question", "body": "Hi Hans..."}),
        "outreach_email_2": json.dumps({"subject": "Following up", "body": "Hi again..."}),
    }
    return {**base, **overrides}


def _fake_investor(overrides: dict = {}) -> dict:
    base = {
        "id": FAKE_INVESTOR_ID,
        "firm_name": "Derive Ventures",
        "contact_name": "Sarah Chen",
        "contact_email": "sarah@derive.vc",
        "contact_linkedin": "https://linkedin.com/in/sarahchen",
        "pipeline_stage": "ready_to_contact",
        "tier": 1,
        "outreach_approved": False,
        "outreach_draft": json.dumps({
            "email_1": {"subject": "Hospitality AI insight", "body": "Hi Sarah..."},
            "email_2": {"subject": "Traction update", "body": "Hi again..."},
        }),
    }
    return {**base, **overrides}


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------

def test_get_review_queue():
    """GET /review-queue returns split client/investor lists."""
    leads = [_fake_lead()]
    investors = [_fake_investor()]

    mock_leads_result = MagicMock()
    mock_leads_result.data = leads
    mock_investor_result = MagicMock()
    mock_investor_result.data = investors

    with patch("backend.routers.sequences.supabase") as mock_sb:
        mock_sb.table.return_value.select.return_value.eq.return_value.neq.return_value.order.return_value.execute.return_value = mock_leads_result
        # second call for investor
        mock_sb.table.return_value.select.return_value.eq.return_value.neq.return_value.neq.return_value.order.return_value.execute.return_value = mock_investor_result

        resp = client.get("/review-queue")
        assert resp.status_code == 200
        data = resp.json()
        assert "client" in data
        assert "investor" in data
        assert "totals" in data


def test_approve_client_outreach():
    """POST /review-queue/{id}/approve schedules sequence and returns approved status."""
    lead = _fake_lead({"outreach_approved": True})

    with (
        patch("backend.routers.sequences.supabase") as mock_sb,
        patch("backend.routers.sequences._send_telegram"),
        patch("backend.agents.sequence_executor.supabase") as mock_sb2,
        patch("backend.agents.sequence_executor._send_telegram"),
    ):
        # Approve update
        mock_update = MagicMock()
        mock_update.data = [lead]
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        # Config read
        mock_cfg = MagicMock()
        mock_cfg.data = {"value": "5"}
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_cfg

        # Config upsert
        mock_sb.table.return_value.upsert.return_value.execute.return_value = MagicMock()

        # sequence_executor supabase mocks
        mock_lead_fetch = MagicMock()
        mock_lead_fetch.data = _fake_lead()
        mock_sb2.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_lead_fetch
        mock_sb2.table.return_value.insert.return_value.execute.return_value = MagicMock()

        resp = client.post(
            f"/review-queue/{FAKE_LEAD_ID}/approve",
            json={"track": "client"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["entity_id"] == FAKE_LEAD_ID


def test_reject_client_outreach():
    """POST /review-queue/{id}/reject closes lead as closed_lost."""
    with (
        patch("backend.routers.sequences.supabase") as mock_sb,
        patch("backend.routers.sequences._send_telegram"),
    ):
        mock_result = MagicMock()
        mock_result.data = [_fake_lead({"pipeline_stage": "closed_lost"})]
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

        resp = client.post(
            f"/review-queue/{FAKE_LEAD_ID}/reject",
            json={"track": "client"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"


def test_edit_client_outreach():
    """POST /review-queue/{id}/edit updates draft without approving."""
    with patch("backend.routers.sequences.supabase") as mock_sb:
        mock_current = MagicMock()
        mock_current.data = _fake_lead()
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_current
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resp = client.post(
            f"/review-queue/{FAKE_LEAD_ID}/edit",
            json={
                "track": "client",
                "new_subject": "Updated subject",
                "new_body": "Updated body",
                "email_number": 1,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"


# ---------------------------------------------------------------------------
# Sequence processing
# ---------------------------------------------------------------------------

def test_process_sequences_endpoint():
    """POST /sequences/process calls process_due_sequences and returns counts."""
    with patch("backend.agents.sequence_executor.supabase") as mock_sb, \
         patch("backend.agents.sequence_executor._send_telegram"):
        mock_result = MagicMock()
        mock_result.data = []  # no due sequences
        mock_sb.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value = mock_result

        resp = client.post("/sequences/process")
        assert resp.status_code == 200
        data = resp.json()
        assert "sent" in data
        assert "skipped" in data
        assert data["sent"] == 0


def test_check_replies_endpoint():
    """POST /sequences/check-replies returns ok."""
    with patch("backend.agents.sequence_executor.supabase") as mock_sb:
        mock_result = MagicMock()
        mock_result.data = []
        mock_sb.table.return_value.select.return_value.eq.return_value.not_.return_value.is_.return_value.execute.return_value = mock_result

        resp = client.post("/sequences/check-replies")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def test_discovery_run_manual():
    """POST /discovery/run with source='manual' creates leads and triggers pipeline."""
    manual_lead = {
        "first_name": "Anna",
        "last_name": "Schmidt",
        "email": "anna@boutiquecollection.eu",
        "title": "CEO",
        "company": "Boutique Collection",
        "linkedin_url": "https://linkedin.com/in/annaschmidt",
    }

    with (
        patch("backend.routers.discovery.supabase") as mock_sb,
        patch("backend.routers.discovery._send_telegram"),
        patch("backend.agents.enrichment.supabase") as mock_enrich_sb,
        patch("backend.agents.enrichment.generate") as mock_gen,
        patch("backend.agents.outreach.supabase") as mock_out_sb,
        patch("backend.agents.outreach.generate") as mock_gen2,
    ):
        # Dedup check: no existing leads
        mock_dedup = MagicMock()
        mock_dedup.data = []
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_dedup

        # Lead insert
        inserted = {**manual_lead, "id": "new-lead-uuid"}
        mock_insert = MagicMock()
        mock_insert.data = [inserted]
        mock_sb.table.return_value.insert.return_value.execute.return_value = mock_insert

        # Enrichment agent mocks
        mock_enrich_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=inserted)
        mock_gen.return_value = json.dumps({"lead_score": 70, "warmth": "warm", "pain_signals": [], "personalisation_hooks": []})
        mock_enrich_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        # Outreach agent mocks
        mock_out_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=inserted)
        mock_gen2.return_value = json.dumps({"email_1_subject": "Subj", "email_1_body": "Body", "email_2_subject": "S2", "email_2_body": "B2"})
        mock_out_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resp = client.post("/discovery/run", json={
            "track": "client",
            "source": "manual",
            "leads": [manual_lead],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] == 1
        assert data["added"] == 1


def test_discovery_investor_manual_only():
    """POST /discovery/run with investor track rejects non-manual sources."""
    resp = client.post("/discovery/run", json={
        "track": "investor",
        "source": "apollo",
        "filters": {},
    })
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Sequence executor unit tests
# ---------------------------------------------------------------------------

def test_schedule_sequence_creates_steps():
    """schedule_sequence inserts 4 records (3 email + 1 linkedin touch) for client track."""
    lead = _fake_lead()

    with (
        patch("backend.agents.sequence_executor.supabase") as mock_sb,
        patch("backend.agents.sequence_executor._send_telegram"),
    ):
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=lead)
        mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock()

        from backend.agents.sequence_executor import schedule_sequence
        schedule_sequence(FAKE_LEAD_ID, "client")

        # Should be called twice: once for 3-step batch insert, once for linkedin_touch
        assert mock_sb.table.return_value.insert.call_count == 2
        # First call is the batch of 3 steps
        first_call_args = mock_sb.table.return_value.insert.call_args_list[0][0][0]
        assert len(first_call_args) == 3
        assert first_call_args[0]["step_number"] == 1
        assert first_call_args[1]["step_number"] == 2
        assert first_call_args[2]["step_number"] == 3


def test_check_all_replies_no_sequences():
    """check_all_replies returns early when no sent sequences exist."""
    with patch("backend.agents.sequence_executor.supabase") as mock_sb:
        mock_sb.table.return_value.select.return_value.eq.return_value.not_.return_value.is_.return_value.execute.return_value = MagicMock(data=[])

        from backend.agents.sequence_executor import check_all_replies
        check_all_replies()  # should not raise
