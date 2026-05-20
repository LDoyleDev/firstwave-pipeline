import base64
import logging
import os
import re
from email.mime.text import MIMEText
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL", "liam@firstwaveai.com")
_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


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


UNSUBSCRIBE_MAILTO = os.getenv("UNSUBSCRIBE_MAILTO", "unsubscribe@firstwaveai.com")


def send_email(
    to: str,
    subject: str,
    body: str,
    reply_to_message_id: Optional[str] = None,
    unsubscribe_url: Optional[str] = None,
) -> str:
    """Send a plain-text email from liam@firstwaveai.com.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text body (no HTML — keeps deliverability high).
        reply_to_message_id: gmail_message_id of the email being replied to (sets threading headers).
        unsubscribe_url: per-recipient one-click unsubscribe URL. When set, adds the
            RFC 8058 List-Unsubscribe / List-Unsubscribe-Post headers. Required for
            compliant marketing email — see backend/routers/compliance.py.

    Returns:
        gmail_message_id of the sent message.
    """
    service = build("gmail", "v1", credentials=_get_credentials())

    msg = MIMEText(body, "plain")
    msg["to"] = to
    msg["from"] = SENDER_EMAIL
    msg["subject"] = subject

    if reply_to_message_id:
        msg["In-Reply-To"] = reply_to_message_id
        msg["References"] = reply_to_message_id

    if unsubscribe_url:
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>, <mailto:{UNSUBSCRIBE_MAILTO}?subject=unsubscribe>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()

    gmail_id = result["id"]
    logger.info("Sent email to %s subject=%r gmail_id=%s", to, subject, gmail_id)
    return gmail_id


def check_replies(gmail_message_ids: list[str]) -> list[dict]:
    """Check whether Gmail message threads have received replies.

    Args:
        gmail_message_ids: List of Gmail message IDs (from email_sequences.gmail_message_id).

    Returns:
        List of dicts: {gmail_message_id, replied: bool, reply_snippet: str|None}.
    """
    results: list[dict] = []
    service = build("gmail", "v1", credentials=_get_credentials())

    for gm_id in gmail_message_ids:
        try:
            msg = service.users().messages().get(
                userId="me", id=gm_id, format="minimal"
            ).execute()
            thread_id = msg["threadId"]
            thread = service.users().threads().get(
                userId="me", id=thread_id, format="minimal"
            ).execute()
            messages = thread.get("messages", [])
            replied = len(messages) > 1
            reply_snippet = messages[-1].get("snippet", "") if replied else None
            results.append({
                "gmail_message_id": gm_id,
                "replied": replied,
                "reply_snippet": reply_snippet,
            })
        except Exception as e:
            logger.warning("Could not check replies for gmail_id %s: %s", gm_id, e)
            results.append({"gmail_message_id": gm_id, "replied": False, "reply_snippet": None})

    return results


# Failed-recipient / DSN-status patterns for bounce parsing (RFC 3464).
_FAILED_RECIPIENT_RE = re.compile(
    r"(?:Final-Recipient:\s*rfc822;|X-Failed-Recipients:|Original-Recipient:\s*rfc822;)\s*"
    r"([^\s<>]+@[^\s<>]+)",
    re.IGNORECASE,
)
_DSN_STATUS_RE = re.compile(r"Status:\s*([245])\.\d+\.\d+", re.IGNORECASE)


def detect_bounces(newer_than_days: int = 2) -> list[dict]:
    """Scan the mailbox for delivery-failure notices (NDRs) and extract failures.

    Gmail has no push bounce API for sent mail — bounces arrive as Mailer-Daemon
    messages. Uses the existing gmail.readonly scope.

    Args:
        newer_than_days: how far back to scan.

    Returns:
        List of {email, bounce_type: 'hard'|'soft', diagnostic}. 'hard' = a 5.x.x
        DSN status (permanent — suppress); 'soft' = 4.x.x (transient — log only).
    """
    service = build("gmail", "v1", credentials=_get_credentials())
    query = (
        f"newer_than:{newer_than_days}d "
        "(from:mailer-daemon OR from:postmaster) "
        "subject:(delivery OR undeliverable OR failure OR returned OR failed)"
    )
    bounces: list[dict] = []
    seen: set[str] = set()
    try:
        listing = service.users().messages().list(userId="me", q=query, maxResults=100).execute()
    except Exception:
        logger.exception("Bounce scan: message list failed")
        return bounces

    for ref in listing.get("messages", []):
        try:
            full = service.users().messages().get(userId="me", id=ref["id"], format="raw").execute()
            raw = base64.urlsafe_b64decode(full["raw"].encode()).decode("utf-8", errors="ignore")
        except Exception:
            logger.warning("Bounce scan: could not fetch message %s", ref.get("id"))
            continue

        rcpt_match = _FAILED_RECIPIENT_RE.search(raw)
        if not rcpt_match:
            continue
        email_addr = rcpt_match.group(1).strip().strip("<>").lower()
        if email_addr in seen:
            continue
        seen.add(email_addr)

        status_match = _DSN_STATUS_RE.search(raw)
        bounce_type = "soft"
        if status_match and status_match.group(1) == "5":
            bounce_type = "hard"
        elif status_match and status_match.group(1) == "4":
            bounce_type = "soft"
        elif not status_match:
            # No machine-readable status — treat as hard (NDR subject implies failure).
            bounce_type = "hard"

        bounces.append({
            "email": email_addr,
            "bounce_type": bounce_type,
            "diagnostic": status_match.group(0) if status_match else "no DSN status",
        })

    logger.info("Bounce scan: %d distinct failed recipients", len(bounces))
    return bounces
