import logging
import os
from typing import Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

CALCOM_API_KEY = os.getenv("CALCOM_API_KEY", "")

# CALCOM_EVENT_TYPE_ID is stored as a full URL: https://cal.com/{username}/{slug}
_event_type_url = os.getenv("CALCOM_EVENT_TYPE_ID", "")
_path_parts = [p for p in urlparse(_event_type_url).path.split("/") if p]
CALCOM_USERNAME = _path_parts[0] if len(_path_parts) > 0 else ""
CALCOM_EVENT_SLUG = _path_parts[1] if len(_path_parts) > 1 else ""

BASE_URL = "https://api.cal.com/v2"
_HEADERS = {
    "Authorization": f"Bearer {CALCOM_API_KEY}",
    "Content-Type": "application/json",
    "cal-api-version": "2024-08-13",
}

_event_type_id: Optional[int] = None


def _resolve_event_type_id() -> int:
    """Fetch and cache the numeric event type ID from Cal.com.

    Needed for booking creation; resolves once per process lifetime.
    """
    global _event_type_id
    if _event_type_id is not None:
        return _event_type_id

    response = httpx.get(
        f"{BASE_URL}/event-types",
        headers=_HEADERS,
        params={"username": CALCOM_USERNAME},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    # Walk the nested structure: data.eventTypeGroups[].eventTypes[]
    groups = data.get("data", {}).get("eventTypeGroups", [])
    for group in groups:
        for et in group.get("eventTypes", []):
            if et.get("slug") == CALCOM_EVENT_SLUG:
                _event_type_id = int(et["id"])
                logger.info("Resolved Cal.com event type '%s' → id=%d", CALCOM_EVENT_SLUG, _event_type_id)
                return _event_type_id

    raise ValueError(
        f"Cal.com event type '{CALCOM_EVENT_SLUG}' not found for user '{CALCOM_USERNAME}'. "
        "Check CALCOM_EVENT_TYPE_ID in .env."
    )


def get_available_slots(date: str) -> list[dict]:
    """Get available booking slots for the given date.

    Args:
        date: Date string in YYYY-MM-DD format.

    Returns:
        List of slot dicts with 'time' key (ISO datetime). Should only contain
        10:30, 10:50, 11:10 Europe/Berlin as configured in Cal.com availability.
    """
    response = httpx.get(
        f"{BASE_URL}/slots/available",
        headers=_HEADERS,
        params={
            "startTime": f"{date}T00:00:00.000Z",
            "endTime": f"{date}T23:59:59.999Z",
            "username": CALCOM_USERNAME,
            "eventTypeSlug": CALCOM_EVENT_SLUG,
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    slots_map = data.get("data", {}).get("slots", {})
    day_slots = slots_map.get(date, [])
    logger.info("Cal.com: %d slots available on %s", len(day_slots), date)
    return day_slots


def create_booking(
    slot_time: str,
    attendee_name: str,
    attendee_email: str,
    notes: str = "",
) -> dict:
    """Create a Cal.com booking.

    Args:
        slot_time: ISO datetime string for the slot start time.
        attendee_name: Full name of the external attendee.
        attendee_email: Email address of the external attendee.
        notes: Optional notes for the meeting.

    Returns:
        Booking details dict including 'id' (use as cal_event_id).
    """
    event_type_id = _resolve_event_type_id()

    payload = {
        "eventTypeId": event_type_id,
        "start": slot_time,
        "attendee": {
            "name": attendee_name,
            "email": attendee_email,
            "timeZone": "Europe/Berlin",
            "language": "en",
        },
        "metadata": {"notes": notes} if notes else {},
    }

    response = httpx.post(f"{BASE_URL}/bookings", headers=_HEADERS, json=payload, timeout=15)
    response.raise_for_status()
    booking = response.json().get("data", {})
    logger.info("Cal.com: booking created id=%s for %s", booking.get("id"), attendee_email)
    return booking


def cancel_booking(cal_event_id: str) -> bool:
    """Cancel a Cal.com booking by its booking ID. Returns True on success."""
    try:
        response = httpx.delete(
            f"{BASE_URL}/bookings/{cal_event_id}",
            headers=_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        logger.info("Cal.com: cancelled booking %s", cal_event_id)
        return True
    except Exception as e:
        logger.error("Cal.com: failed to cancel booking %s: %s", cal_event_id, e)
        return False
