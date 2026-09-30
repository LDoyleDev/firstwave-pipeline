"""Phase 3 integration tests — all external calls mocked."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Groq transcription
# ---------------------------------------------------------------------------

def test_groq_transcribe_audio():
    """Audio bytes → transcript string returned."""
    mock_transcription = MagicMock()
    mock_transcription.text = "What is my pipeline looking like today?"

    with patch("backend.integrations.groq_client._client") as mock_client:
        mock_client.audio.transcriptions.create.return_value = mock_transcription

        from backend.integrations.groq_client import transcribe_audio
        result = transcribe_audio(b"fake-ogg-bytes", "voice.ogg")

    assert result == "What is my pipeline looking like today?"
    mock_client.audio.transcriptions.create.assert_called_once()


def test_groq_string_response_fallback():
    """If the API returns a plain string (response_format=text), it is handled correctly."""
    with patch("backend.integrations.groq_client._client") as mock_client:
        mock_client.audio.transcriptions.create.return_value = "Plain text transcript"

        from backend.integrations.groq_client import transcribe_audio
        result = transcribe_audio(b"bytes", "audio.wav")

    assert result == "Plain text transcript"


# ---------------------------------------------------------------------------
# Gmail send_email
# ---------------------------------------------------------------------------

def test_gmail_send_email():
    """send_email builds correct MIME message and returns gmail_message_id."""
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "gmail-msg-abc123"
    }

    with patch("backend.integrations.gmail_client._get_credentials"), \
         patch("backend.integrations.gmail_client.build", return_value=mock_service):

        from backend.integrations.gmail_client import send_email
        result = send_email("test@example.com", "Test Subject", "Hello body")

    assert result == "gmail-msg-abc123"
    mock_service.users.return_value.messages.return_value.send.assert_called_once()


def _gmail_service(thread_messages):
    """A mock Gmail service whose thread returns `thread_messages`."""
    svc = MagicMock()
    svc.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        "threadId": "thread-xyz"
    }
    svc.users.return_value.threads.return_value.get.return_value.execute.return_value = {
        "messages": thread_messages
    }
    return svc


def test_gmail_check_replies_single_message_thread():
    """Thread with only the sent message -> replied=False, no snippet."""
    with patch("backend.integrations.gmail_client._get_credentials"), \
         patch("backend.integrations.gmail_client.build",
               return_value=_gmail_service([{"snippet": "Original"}])):

        from backend.integrations.gmail_client import check_replies
        result = check_replies(["msg-111"])

    assert result[0]["gmail_message_id"] == "msg-111"
    assert result[0]["replied"] is False
    assert result[0]["reply_snippet"] is None


def test_gmail_check_replies_thread_has_reply():
    """Thread with 2 messages -> replied=True, snippet from the latest."""
    with patch("backend.integrations.gmail_client._get_credentials"), \
         patch("backend.integrations.gmail_client.build",
               return_value=_gmail_service(
                   [{"snippet": "Original"}, {"snippet": "Reply here"}])):

        from backend.integrations.gmail_client import check_replies
        result = check_replies(["msg-111"])

    assert result[0]["gmail_message_id"] == "msg-111"
    assert result[0]["replied"] is True
    assert result[0]["reply_snippet"] == "Reply here"


def test_gmail_check_replies_api_error_is_not_fatal():
    """A Gmail API failure degrades to replied=False rather than raising."""
    svc = MagicMock()
    svc.users.return_value.messages.return_value.get.return_value.execute.side_effect = (
        RuntimeError("gmail unavailable")
    )

    with patch("backend.integrations.gmail_client._get_credentials"), \
         patch("backend.integrations.gmail_client.build", return_value=svc):

        from backend.integrations.gmail_client import check_replies
        result = check_replies(["msg-111", "msg-222"])

    assert [r["gmail_message_id"] for r in result] == ["msg-111", "msg-222"]
    assert all(r["replied"] is False and r["reply_snippet"] is None for r in result)


# ---------------------------------------------------------------------------
# Cal.com
# ---------------------------------------------------------------------------

def test_calcom_get_available_slots():
    """get_available_slots parses slots response for the requested date."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "slots": {
                "2026-04-25": [
                    {"time": "2026-04-25T08:30:00.000Z"},
                    {"time": "2026-04-25T08:50:00.000Z"},
                    {"time": "2026-04-25T09:10:00.000Z"},
                ]
            }
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch("backend.integrations.calcom_client.httpx") as mock_httpx:
        mock_httpx.get.return_value = mock_response

        from backend.integrations.calcom_client import get_available_slots
        result = get_available_slots("2026-04-25")

    assert len(result) == 3
    assert result[0]["time"] == "2026-04-25T08:30:00.000Z"


def test_calcom_cancel_booking_success():
    """cancel_booking returns True when API returns success."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("backend.integrations.calcom_client.httpx") as mock_httpx:
        mock_httpx.delete.return_value = mock_response

        from backend.integrations.calcom_client import cancel_booking
        result = cancel_booking("booking-abc")

    assert result is True


def test_calcom_cancel_booking_failure():
    """cancel_booking returns False and does not raise on API error."""
    with patch("backend.integrations.calcom_client.httpx") as mock_httpx:
        mock_httpx.delete.side_effect = Exception("Connection refused")

        from backend.integrations.calcom_client import cancel_booking
        result = cancel_booking("booking-xyz")

    assert result is False


# ---------------------------------------------------------------------------
# Apollo
# ---------------------------------------------------------------------------

def test_apollo_find_person_email_found():
    """find_person_email returns email when Apollo responds with a match."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"person": {"email": "anna@example.com"}}

    with patch("backend.integrations.apollo_client.httpx") as mock_httpx, \
         patch("backend.integrations.apollo_client.time"):

        mock_httpx.post.return_value = mock_response

        from backend.integrations.apollo_client import find_person_email
        result = find_person_email("Anna", "Schmidt", "example.com")

    assert result == "anna@example.com"


def test_apollo_find_person_email_not_found():
    """find_person_email returns None on no match."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"person": {}}

    with patch("backend.integrations.apollo_client.httpx") as mock_httpx, \
         patch("backend.integrations.apollo_client.time"):

        mock_httpx.post.return_value = mock_response

        from backend.integrations.apollo_client import find_person_email
        result = find_person_email("Unknown", "Person", "nowhere.com")

    assert result is None


def test_apollo_search_leads():
    """search_leads normalises Apollo response into lead dicts."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "people": [
            {
                "first_name": "James",
                "last_name": "Taylor",
                "title": "Revenue Manager",
                "organization": {"name": "Grand Hotel Group"},
                "email": "james@example.com",
                "linkedin_url": "https://linkedin.com/in/james-taylor",
                "city": "Munich",
            }
        ]
    }

    with patch("backend.integrations.apollo_client.httpx") as mock_httpx, \
         patch("backend.integrations.apollo_client.time"):

        mock_httpx.post.return_value = mock_response

        from backend.integrations.apollo_client import search_leads
        result = search_leads(
            job_titles=["Revenue Manager"],
            industry="hospitality",
            geography=["Germany"],
        )

    assert len(result) == 1
    assert result[0]["first_name"] == "James"
    assert result[0]["company"] == "Grand Hotel Group"
    assert result[0]["email"] == "james@example.com"


# ---------------------------------------------------------------------------
# PhantomBuster
# ---------------------------------------------------------------------------

def test_phantombuster_launch():
    """launch_linkedin_search_scraper returns container_id on success."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"containerId": "container-abc123"}

    with patch("backend.integrations.phantombuster_client.httpx") as mock_httpx:
        mock_httpx.post.return_value = mock_response

        from backend.integrations.phantombuster_client import launch_linkedin_search_scraper
        result = launch_linkedin_search_scraper("https://linkedin.com/search?keywords=hotel")

    assert result == "container-abc123"


def test_phantombuster_get_results_json():
    """get_scraper_results parses JSON output and returns normalised lead dicts."""
    output_json = json.dumps([
        {
            "firstName": "Emma",
            "lastName": "Wilson",
            "jobTitle": "VP Revenue",
            "companyName": "Alpine Hotels",
            "profileUrl": "https://linkedin.com/in/emma-wilson",
            "location": "Vienna",
        }
    ])

    finished_response = MagicMock()
    finished_response.status_code = 200
    finished_response.json.return_value = {"status": "finished", "output": output_json}

    with patch("backend.integrations.phantombuster_client.httpx") as mock_httpx, \
         patch("backend.integrations.phantombuster_client.time"):

        mock_httpx.get.return_value = finished_response

        from backend.integrations.phantombuster_client import get_scraper_results
        result = get_scraper_results("container-abc123")

    assert len(result) == 1
    assert result[0]["first_name"] == "Emma"
    assert result[0]["title"] == "VP Revenue"
    assert result[0]["linkedin_url"] == "https://linkedin.com/in/emma-wilson"


# ---------------------------------------------------------------------------
# Telegram webhook endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_telegram_webhook_returns_ok():
    """POST /webhook/telegram → 200 {"ok": True} even when process_update succeeds."""
    from fastapi.testclient import TestClient

    with patch("backend.integrations.telegram_bot.process_webhook_update", new_callable=AsyncMock) as mock_pu:
        from backend.main import app
        client = TestClient(app)
        response = client.post(
            "/webhook/telegram",
            json={"update_id": 1, "message": {"text": "hello"}},
        )

    assert response.status_code == 200
    assert response.json()["ok"] is True
