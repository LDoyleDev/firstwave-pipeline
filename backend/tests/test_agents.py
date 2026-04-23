"""Phase 2 agent tests — mock Anthropic + Supabase, verify agent logic."""
import json
import pytest
from unittest.mock import patch, MagicMock


# --- Helpers ---

def _make_mock_response(text: str):
    """Build a mock Anthropic response object."""
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


def _make_supabase_mock(data):
    """Build a mock that returns data from .execute()."""
    mock = MagicMock()
    mock.data = data
    return mock


# --- Test: enrichment agent ---

def test_enrichment_agent():
    """Mock lead data → valid enrichment JSON returned and lead updated."""
    lead = {
        "id": "test-lead-001",
        "first_name": "Anna",
        "last_name": "Schmidt",
        "title": "VP Revenue",
        "company": "Grand Hotel Group",
        "linkedin_url": "https://linkedin.com/in/anna-schmidt",
        "company_website": "https://grandhotelgroup.com",
    }
    enrichment_result = {
        "lead_score": 78,
        "warmth": "warm",
        "pain_signals": ["High OTA dependency", "Recent staff turnover post on LinkedIn"],
        "personalisation_hooks": ["Attended ITB Berlin 2026", "Multi-property European group"],
        "company_context": "Grand Hotel Group operates 12 mid-scale hotels across DACH region.",
        "recent_news": "Opened new Munich property in Q1 2026.",
        "mutual_connections_or_events": "Both attended ITB Berlin 2026",
        "recommended_opener": "Your Munich expansion shows you're scaling — most GMs don't realise how much that amplifies unanswered call losses.",
        "notes": "Strong ICP fit. VP Revenue role means she owns the problem.",
    }

    with patch("backend.agents.enrichment.generate", return_value=json.dumps(enrichment_result)), \
         patch("backend.agents.enrichment.supabase") as mock_sb:

        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = _make_supabase_mock(None)

        from backend.agents.enrichment import enrich_lead
        result = enrich_lead(lead)

    assert result["lead_score"] == 78
    assert result["warmth"] == "warm"
    assert len(result["pain_signals"]) == 2
    assert "recommended_opener" in result
    mock_sb.table.assert_called_with("leads")


def test_enrichment_json_parse_fallback():
    """JSON parse failure returns safe fallback dict, not an exception."""
    lead = {"id": "test-002", "first_name": "Max", "company": "Test Corp"}

    with patch("backend.agents.enrichment.generate", return_value="Not valid JSON at all"), \
         patch("backend.agents.enrichment.supabase") as mock_sb:

        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = _make_supabase_mock(None)

        from backend.agents.enrichment import enrich_lead
        result = enrich_lead(lead)

    assert "lead_score" in result
    assert result["lead_score"] == 0


# --- Test: client outreach agent ---

def test_client_outreach():
    """Lead with enrichment data → email draft generated and stored."""
    lead_data = {
        "id": "test-lead-003",
        "first_name": "James",
        "last_name": "Taylor",
        "title": "CMO",
        "company": "Coastal Resorts Ltd",
        "email": "james.taylor@coastalresorts.com",
        "enrichment_data": {
            "lead_score": 82,
            "warmth": "hot",
            "pain_signals": ["21% unanswered calls mentioned in review"],
            "recommended_opener": "One in five calls to your front desk is going unanswered.",
        },
    }
    draft_response = {
        "email_1_subject": "The 21% problem at Coastal Resorts",
        "email_1_body": "One in five inbound calls to your front desk goes unanswered...",
        "email_2_subject": "Quick follow-up",
        "email_2_body": "Wanted to check if my previous note landed...",
    }

    with patch("backend.agents.outreach.supabase") as mock_sb, \
         patch("backend.agents.outreach.generate", return_value=json.dumps(draft_response)):

        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = _make_supabase_mock(lead_data)
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = _make_supabase_mock(None)

        from backend.agents.outreach import generate_client_outreach
        result = generate_client_outreach("test-lead-003")

    assert "email_1_subject" in result
    assert "email_1_body" in result
    assert "email_2_subject" in result
    assert len(result["email_1_body"]) > 0


# --- Test: investor outreach agent ---

def test_investor_outreach():
    """Investor target → outreach draft generated and stored."""
    investor_data = {
        "id": "inv-001",
        "firm_name": "Derive Ventures",
        "investor_type": "VC",
        "tier": 1,
        "contact_name": "Sarah Chen",
        "why_fit": "Specialises in hospitality tech, portfolio includes HotelTech Report",
        "warm_path": "Met at ITB Berlin 2026 panel",
        "pipeline_stage": "research_needed",
    }
    draft_response = {
        "email_1_subject": "Hospitality AI — 21% of calls going unanswered",
        "email_1_body": "Sarah, given Derive's focus on hospitality tech...",
        "email_2_subject": "Following up — First Wave AI",
        "email_2_body": "Wanted to follow up on my previous note...",
    }

    with patch("backend.agents.outreach.supabase") as mock_sb, \
         patch("backend.agents.outreach.generate", return_value=json.dumps(draft_response)):

        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = _make_supabase_mock(investor_data)
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = _make_supabase_mock(None)

        from backend.agents.outreach import generate_investor_outreach
        result = generate_investor_outreach("inv-001")

    assert "email_1_subject" in result
    assert "email_1_body" in result
    assert "Derive" in result["email_1_body"] or len(result["email_1_body"]) > 0


# --- Test: intent parser agent ---

@pytest.mark.parametrize("transcript,expected_intent", [
    ("What's my pipeline looking like?", "check_pipeline"),
    ("Find me five hotel group CMOs in Germany", "discover_leads"),
    ("Show me the review queue", "review_queue"),
    ("That meeting was great, Marcus wants a deck, follow up in three days", "post_meeting_feedback"),
    ("Book a client meeting tomorrow in slot one", "book_meeting"),
])
def test_intent_parser(transcript: str, expected_intent: str):
    """5 sample voice transcripts → correct intents returned."""
    intent_response = {
        "intent": expected_intent,
        "track": "both",
        "parameters": {},
        "confidence": 0.92,
        "raw_transcript": transcript,
    }

    with patch("backend.agents.intent_parser.classify", return_value=json.dumps(intent_response)), \
         patch("backend.agents.intent_parser.supabase") as mock_sb:

        mock_sb.table.return_value.insert.return_value.execute.return_value = _make_supabase_mock(None)

        from backend.agents.intent_parser import parse_voice_intent
        result = parse_voice_intent(transcript)

    assert result["intent"] == expected_intent
    assert result["confidence"] > 0
    assert result["raw_transcript"] == transcript


def test_intent_parser_json_fallback():
    """Malformed Claude response → falls back to check_pipeline, no exception."""
    with patch("backend.agents.intent_parser.classify", return_value="This is not JSON"), \
         patch("backend.agents.intent_parser.supabase") as mock_sb:

        mock_sb.table.return_value.insert.return_value.execute.return_value = _make_supabase_mock(None)

        from backend.agents.intent_parser import parse_voice_intent
        result = parse_voice_intent("some transcript")

    assert "intent" in result
    assert result["confidence"] == 0.0


# --- Test: follow-up agent ---

def test_followup_agent():
    """Meeting feedback → outcome classification + follow-up draft generated."""
    meeting_data = {
        "id": "meeting-001",
        "track": "client",
        "lead_id": "lead-001",
        "scheduled_at": "2026-04-23T10:30:00+02:00",
        "status": "scheduled",
    }
    lead_data = {
        "id": "lead-001",
        "first_name": "Emma",
        "last_name": "Wilson",
        "company": "Alpine Hotels",
        "email": "emma@alpinehotels.com",
    }
    followup_response = {
        "outcome": "hot",
        "next_action": "Send one-pager + book Philip for technical demo",
        "next_action_at": "2026-04-24T10:00:00+00:00",
        "follow_up_draft": "Emma, great talking today. I'll connect you with Philip for the technical walkthrough...",
    }

    with patch("backend.agents.followup.supabase") as mock_sb, \
         patch("backend.agents.followup.generate", return_value=json.dumps(followup_response)):

        def table_side_effect(name):
            mock = MagicMock()
            if name == "meetings":
                mock.select.return_value.eq.return_value.single.return_value.execute.return_value = _make_supabase_mock(meeting_data)
                mock.update.return_value.eq.return_value.execute.return_value = _make_supabase_mock(None)
            elif name == "leads":
                mock.select.return_value.eq.return_value.single.return_value.execute.return_value = _make_supabase_mock(lead_data)
            elif name == "email_sequences":
                mock.insert.return_value.execute.return_value = _make_supabase_mock(None)
            return mock

        mock_sb.table.side_effect = table_side_effect

        from backend.agents.followup import generate_followup
        result = generate_followup("meeting-001", "Emma was really engaged, wants a demo ASAP, definitely hot")

    assert result["outcome"] == "hot"
    assert "next_action" in result
    assert "follow_up_draft" in result
    assert len(result["follow_up_draft"]) > 0


# --- Test: briefing agent ---

def test_briefing_agent():
    """Meeting ID → formatted briefing text returned and stored."""
    meeting_data = {
        "id": "meeting-002",
        "track": "investor",
        "investor_id": "inv-002",
        "scheduled_at": "2026-04-23T10:50:00+02:00",
        "status": "scheduled",
        "briefing_sent": False,
    }
    investor_data = {
        "id": "inv-002",
        "firm_name": "Heartcore Capital",
        "tier": 5,
        "contact_name": "Marie Dupont",
        "why_fit": "European early-stage focused, portfolio in SaaS",
    }
    briefing_text = "🗓 Marie Dupont — Heartcore Capital — 10:50\nTrack: Investor\n\n**Who they are** Early-stage European VC..."

    with patch("backend.agents.briefing.supabase") as mock_sb, \
         patch("backend.agents.briefing.generate", return_value=briefing_text):

        def table_side_effect(name):
            mock = MagicMock()
            if name == "meetings":
                mock.select.return_value.eq.return_value.single.return_value.execute.return_value = _make_supabase_mock(meeting_data)
                mock.update.return_value.eq.return_value.execute.return_value = _make_supabase_mock(None)
            elif name == "investor_targets":
                mock.select.return_value.eq.return_value.single.return_value.execute.return_value = _make_supabase_mock(investor_data)
            return mock

        mock_sb.table.side_effect = table_side_effect

        from backend.agents.briefing import generate_briefing
        result = generate_briefing("meeting-002")

    assert "Heartcore Capital" in result
    assert len(result) > 50
    assert mock_sb.table.call_count >= 2  # meetings fetched + updated, investor fetched
