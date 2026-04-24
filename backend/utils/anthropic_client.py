import os
import subprocess
import time
import logging
from pathlib import Path
from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Model aliases — Claude Code resolves these to the latest versions automatically
SONNET = "sonnet"
HAIKU = "haiku"  # most efficient for classification and intent parsing

_CLAUDE_BIN = str(Path.home() / ".local" / "bin" / "claude")
_CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"

# Direct SDK client — only used when ANTHROPIC_API_KEY is explicitly set
_sdk_client: Anthropic | None = None


def _get_sdk_client() -> Anthropic:
    global _sdk_client
    if _sdk_client is None:
        _sdk_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _sdk_client


def _call_sdk(system_prompt: str, user_message: str, model: str) -> str:
    """Direct Anthropic SDK call — used only when ANTHROPIC_API_KEY is set."""
    for attempt in range(5):
        try:
            client = _get_sdk_client()
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except RateLimitError:
            wait = 30 * (2 ** attempt)
            logger.warning("Rate limit (attempt %d/5), waiting %ds", attempt + 1, wait)
            if attempt < 4:
                time.sleep(wait)
            else:
                raise
        except (APIConnectionError, APIError) as e:
            wait = 2 ** attempt * 2
            logger.warning("API error (attempt %d/5): %s", attempt + 1, e)
            if attempt < 4:
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("All SDK retry attempts exhausted")


def _call_cli(system_prompt: str, user_message: str, model: str) -> str:
    """Claude Code CLI call — uses Claude Max OAuth, no API key needed."""
    for attempt in range(5):
        try:
            result = subprocess.run(
                [
                    _CLAUDE_BIN,
                    "-p", user_message,
                    "--system-prompt", system_prompt,
                    "--model", model,
                    "--no-session-persistence",
                    "--output-format", "text",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Claude CLI error: {result.stderr[:300]}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.warning("Claude CLI timeout (attempt %d/5)", attempt + 1)
            if attempt < 4:
                time.sleep(10 * (attempt + 1))
            else:
                raise
        except Exception as e:
            logger.warning("Claude CLI error (attempt %d/5): %s", attempt + 1, e)
            if attempt < 4:
                time.sleep(5 * (attempt + 1))
            else:
                raise
    raise RuntimeError("All CLI retry attempts exhausted")


def generate(system_prompt: str, user_message: str, model: str = SONNET) -> str:
    """Generate a response using Claude Sonnet (or specified model)."""
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        return _call_sdk(system_prompt, user_message, model)
    return _call_cli(system_prompt, user_message, model)


def classify(system_prompt: str, user_message: str) -> str:
    """Classify using Claude Haiku — fastest, most efficient for intent parsing."""
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        return _call_sdk(system_prompt, user_message, HAIKU)
    return _call_cli(system_prompt, user_message, HAIKU)
