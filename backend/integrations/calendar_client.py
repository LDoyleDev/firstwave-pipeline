import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

BERLIN = ZoneInfo("Europe/Berlin")
_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_credentials() -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=_SCOPES,
    )
    creds.refresh(Request())
    return creds


def create_event(
    title: str,
    start_time: datetime,
    duration_minutes: int,
    attendee_email: str,
    description: str = "",
) -> str:
    """Create a calendar event and return the google_event_id.

    Args:
        title: Event title/summary.
        start_time: Start datetime (must be timezone-aware).
        duration_minutes: Duration in minutes (typically 20 for meeting slots).
        attendee_email: Email address of the external attendee.
        description: Optional event description / notes.

    Returns:
        Google Calendar event ID string.
    """
    service = build("calendar", "v3", credentials=_get_credentials())

    end_time = start_time + timedelta(minutes=duration_minutes)

    event = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_time.isoformat(), "timeZone": "Europe/Berlin"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "Europe/Berlin"},
        "attendees": [{"email": attendee_email}],
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "email", "minutes": 60}],
        },
    }

    result = service.events().insert(calendarId="primary", body=event).execute()
    event_id = result["id"]
    logger.info("Created calendar event '%s' id=%s", title, event_id)
    return event_id


def cancel_event(google_event_id: str) -> bool:
    """Cancel (delete) a calendar event. Returns True on success."""
    service = build("calendar", "v3", credentials=_get_credentials())
    try:
        service.events().delete(calendarId="primary", eventId=google_event_id).execute()
        logger.info("Cancelled calendar event %s", google_event_id)
        return True
    except Exception as e:
        logger.error("Failed to cancel calendar event %s: %s", google_event_id, e)
        return False


def get_todays_events() -> list[dict]:
    """Return calendar events in the 10:30–11:30 meeting block for today (Europe/Berlin)."""
    service = build("calendar", "v3", credentials=_get_credentials())

    now = datetime.now(BERLIN)
    block_start = now.replace(hour=10, minute=30, second=0, microsecond=0)
    block_end = now.replace(hour=11, minute=30, second=0, microsecond=0)

    result = service.events().list(
        calendarId="primary",
        timeMin=block_start.isoformat(),
        timeMax=block_end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = result.get("items", [])
    logger.info("Fetched %d events for today's meeting block", len(events))
    return events
