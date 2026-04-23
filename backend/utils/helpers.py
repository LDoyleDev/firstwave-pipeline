from datetime import datetime
from zoneinfo import ZoneInfo


BERLIN = ZoneInfo("Europe/Berlin")


def now_berlin() -> datetime:
    """Current time in Europe/Berlin."""
    return datetime.now(BERLIN)
