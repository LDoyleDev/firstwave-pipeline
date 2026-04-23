import json
import os
import time
import logging
from pathlib import Path
from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"

_CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"

_cached_client: Anthropic | None = None
_token_expires_at: float = 0.0


def _get_client() -> Anthropic:
    """Return an Anthropic client, refreshing if the OAuth token has changed."""
    global _cached_client, _token_expires_at

    # Prefer explicit API key from env
    env_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if env_key:
        if _cached_client is None:
            _cached_client = Anthropic(api_key=env_key)
        return _cached_client

    # Fall back to Claude Max OAuth token from Claude Code credentials
    now = time.time()
    if _cached_client is not None and now < _token_expires_at - 300:
        return _cached_client

    try:
        creds = json.loads(_CREDENTIALS_PATH.read_text())
        oauth = creds["claudeAiOauth"]
        token = oauth["accessToken"]
        _token_expires_at = oauth["expiresAt"] / 1000  # ms → s
        _cached_client = Anthropic(api_key=token)
        logger.debug("Anthropic client initialised from Claude Max OAuth token (expires %s)",
                     time.strftime("%Y-%m-%d %H:%M", time.localtime(_token_expires_at)))
        return _cached_client
    except Exception as e:
        raise RuntimeError(
            f"No ANTHROPIC_API_KEY set and could not read Claude Code OAuth token: {e}"
        ) from e


def _call_with_retry(system_prompt: str, user_message: str, model: str) -> str:
    """Call Anthropic API with exponential backoff (max 5 attempts).

    Uses longer waits to accommodate Claude Max OAuth token rate limits,
    which are shared with the interactive Claude Code session.
    """
    for attempt in range(5):
        try:
            client = _get_client()
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except RateLimitError as e:
            # Claude Max OAuth shares quota with the interactive session —
            # use longer waits: 30s, 60s, 120s, 240s
            wait = 30 * (2 ** attempt)
            logger.warning("Rate limit hit (attempt %d/%d), waiting %ds", attempt + 1, 5, wait)
            if attempt < 4:
                time.sleep(wait)
            else:
                raise
        except APIConnectionError as e:
            wait = 2 ** attempt * 2
            logger.warning("Connection error (attempt %d), waiting %ds: %s", attempt + 1, wait, e)
            if attempt < 4:
                time.sleep(wait)
            else:
                raise
        except APIError as e:
            logger.error("Anthropic API error (attempt %d): %s", attempt + 1, e)
            if attempt < 4:
                time.sleep(2 ** attempt)
            else:
                raise
    raise RuntimeError("All retry attempts exhausted")


def generate(system_prompt: str, user_message: str, model: str = SONNET) -> str:
    """Generate a response using Claude Sonnet (or specified model)."""
    return _call_with_retry(system_prompt, user_message, model)


def classify(system_prompt: str, user_message: str) -> str:
    """Classify using Claude Haiku — fast, cheap, for intent parsing and categorisation."""
    return _call_with_retry(system_prompt, user_message, HAIKU)
