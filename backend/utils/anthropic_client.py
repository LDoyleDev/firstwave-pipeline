import time
import logging
from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SONNET = "claude-sonnet-4-20250514"
HAIKU = "claude-haiku-4-5-20251001"

_client = Anthropic()


def _call_with_retry(system_prompt: str, user_message: str, model: str) -> str:
    """Call Anthropic API with exponential backoff (max 3 attempts)."""
    for attempt in range(3):
        try:
            response = _client.messages.create(
                model=model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except RateLimitError as e:
            wait = 2 ** attempt * 5
            logger.warning("Rate limit hit (attempt %d), waiting %ds: %s", attempt + 1, wait, e)
            if attempt < 2:
                time.sleep(wait)
            else:
                raise
        except APIConnectionError as e:
            wait = 2 ** attempt * 2
            logger.warning("Connection error (attempt %d), waiting %ds: %s", attempt + 1, wait, e)
            if attempt < 2:
                time.sleep(wait)
            else:
                raise
        except APIError as e:
            logger.error("Anthropic API error (attempt %d): %s", attempt + 1, e)
            if attempt < 2:
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
