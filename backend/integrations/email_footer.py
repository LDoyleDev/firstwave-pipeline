"""Compliance footer appended to every outbound email.

The template (sender legal entity, postal address, unsubscribe link, privacy
notice) lives in `backend/config/footer.txt` — config-as-code, edit there.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_FOOTER_PATH = Path(__file__).resolve().parent.parent / "config" / "footer.txt"
_template: str | None = None


def _load() -> str:
    global _template
    if _template is None:
        _template = _FOOTER_PATH.read_text(encoding="utf-8")
    return _template


def build_footer(unsubscribe_url: str) -> str:
    """Return the footer block with the per-lead unsubscribe URL substituted in."""
    return _load().format(unsubscribe_url=unsubscribe_url)


def append_footer(body: str, unsubscribe_url: str) -> str:
    """Append the compliance footer to an email body."""
    return f"{body.rstrip()}\n\n{build_footer(unsubscribe_url)}"
