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


def check_replies(sequence_ids: list[str]) -> list[dict]:
    """Check whether any active email sequences have received replies.

    Args:
        sequence_ids: List of email_sequence UUIDs with gmail_message_id set.

    Returns:
        List of dicts: {sequence_id, replied: bool, reply_snippet: str|None}.
    """
    from backend.integrations.supabase_client import supabase

    results: list[dict] = []
    service = build("gmail", "v1", credentials=_get_credentials())

    for seq_id in sequence_ids:
        row = (
            supabase.table("email_sequences")
            .select("gmail_message_id")
            .eq("id", seq_id)
            .single()
            .execute()
        )
        if not row.data or not row.data.get("gmail_message_id"):
            results.append({"sequence_id": seq_id, "replied": False, "reply_snippet": None})
            continue

        gmail_message_id = row.data["gmail_message_id"]

        try:
            # Fetch the original message to get its thread ID
            msg = service.users().messages().get(
                userId="me", id=gmail_message_id, format="minimal"
            ).execute()
            thread_id = msg["threadId"]

            # Fetch the thread and count messages; > 1 means a reply exists
            thread = service.users().threads().get(
                userId="me", id=thread_id, format="minimal"
            ).execute()
            messages = thread.get("messages", [])
            replied = len(messages) > 1
            reply_snippet = messages[-1].get("snippet", "") if replied else None

            results.append({
                "sequence_id": seq_id,
                "replied": replied,
                "reply_snippet": reply_snippet,
            })
        except Exception as e:
            logger.warning("Could not check replies for sequence %s: %s", seq_id, e)
            results.append({"sequence_id": seq_id, "replied": False, "reply_snippet": None})

    return results
