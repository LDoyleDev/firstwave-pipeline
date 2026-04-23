import base64
import logging
import os
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


def send_email(
    to: str,
    subject: str,
    body: str,
    reply_to_message_id: Optional[str] = None,
) -> str:
    """Send a plain-text email from liam@firstwaveai.com.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text body (no HTML — keeps deliverability high).
        reply_to_message_id: gmail_message_id of the email being replied to (sets threading headers).

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
