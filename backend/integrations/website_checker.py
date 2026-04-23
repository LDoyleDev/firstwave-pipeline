"""Lightweight website checker — detects common chatbot/live-chat widgets."""
import logging

import httpx

logger = logging.getLogger(__name__)

# Script patterns that indicate a chatbot or live chat is present on the site
_CHATBOT_SIGNATURES = [
    # Live chat / chatbot platforms
    "intercom",
    "drift.com", "driftt.com",
    "zendesk",
    "livechat",
    "tawk.to",
    "tidio",
    "crisp.chat",
    "freshchat",
    "hubspot",
    "chatlio",
    "olark",
    "purechat",
    "smartsupp",
    "userlike",
    "liveperson",
    "boldchat",
    "snapengage",
    "comm100",
    "kayako",
    "zopim",
    # AI chatbots specific
    "chatgpt", "openai",
    "gorgias",
    "kustomer",
    "helpscout",
    "freshdesk",
    "botpress",
    "manychat",
    "chatfuel",
    "dialogflow",
    "voiceflow",
    "landbot",
    # Generic patterns
    "chat-widget",
    "chat_widget",
    "livechat-button",
    "chat-bubble",
]


def check_for_chatbot(website_url: str) -> bool:
    """Fetch a hotel website homepage and check for chatbot/live-chat signatures.

    Returns True if a chatbot appears to be present, False if not or if the
    site can't be reached. Errs on the side of False (not skipping leads due
    to network errors).

    Args:
        website_url: Company website URL (with or without https://).
    """
    if not website_url:
        return False

    url = website_url if website_url.startswith("http") else f"https://{website_url}"

    try:
        resp = httpx.get(
            url,
            timeout=8,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; FirstWaveAI/1.0)"},
        )
        if resp.status_code >= 400:
            return False

        html = resp.text.lower()
        for sig in _CHATBOT_SIGNATURES:
            if sig in html:
                logger.debug("Chatbot detected on %s (signature: %s)", url, sig)
                return True

    except Exception as e:
        logger.debug("Could not fetch %s for chatbot check: %s", url, e)

    return False
