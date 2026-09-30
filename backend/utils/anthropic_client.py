import json
import os
import subprocess
import time
import uuid
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Model aliases — Claude Code resolves these to the latest versions automatically
SONNET = "sonnet"
HAIKU = "haiku"  # most efficient for classification and intent parsing

# Local Ollama inference (vybe-desktop over Tailscale)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
_OLLAMA_PRIMARY = "gpt-oss:20b"   # primary for all tasks — strongest reasoning, 131k context
_OLLAMA_TIMEOUT = 120.0

_CLAUDE_BIN = str(Path.home() / ".local" / "bin" / "claude")
_CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"

# Direct SDK client — only used when ANTHROPIC_API_KEY is explicitly set
_sdk_client: Anthropic | None = None

# ---------------------------------------------------------------------------
# Cross-project coordination — share GPU + Claude Max with vybe-trading
# ---------------------------------------------------------------------------
# Both projects share the desktop's Ollama instance and the user's Claude Max
# account. If firstwave-pipeline fires LLM calls while vybe-trading is in its
# active window (futures market hours), it queues Ollama requests behind
# vybe-trading's traders, slowing down setup/thesis/debate agents — and
# competes for the same Max-account fallback. Gate firstwave to off-hours.
#
# Default windows when firstwave LLM calls are allowed (UTC):
#   - All day Saturday
#   - Sunday before 22:00 UTC (futures resume at 22:00 UTC = 18:00 ET)
#   - Daily 21:00–22:00 UTC (CME futures break — vybe-trading is idle then)
# Override with FIRSTWAVE_LLM_ALWAYS_ALLOW=1 (manual jobs, tests).

_FW_ALWAYS_ALLOW = os.getenv("FIRSTWAVE_LLM_ALWAYS_ALLOW", "").strip() == "1"

# Shared cooloff key — same name vybe-trading writes (data/redis_keys.py
# CLAUDE_COOLOFF_UNTIL). Value = epoch seconds at which Claude Max resets.
_CLAUDE_COOLOFF_KEY = "llm:claude:cooloff_until"


class VybeTradingWindowError(RuntimeError):
    """Raised when firstwave tries to call an LLM during vybe-trading's active
    window. Callers should defer the task (queue / cron retry) rather than
    swallow this — the work isn't lost, just delayed to off-hours."""


def _is_vybe_trading_window(now: datetime | None = None) -> bool:
    """Return True if vybe-trading is in its active window and firstwave must
    defer LLM calls. See module docstring for the exact schedule."""
    if _FW_ALWAYS_ALLOW:
        return False
    now = now or datetime.now(UTC)
    wd = now.weekday()  # 0=Mon … 6=Sun
    minutes = now.hour * 60 + now.minute
    # Daily futures break 21:00–22:00 UTC — always allowed.
    if 21 * 60 <= minutes < 22 * 60:
        return False
    if wd == 5:  # Saturday
        return False
    if wd == 6 and minutes < 22 * 60:  # Sunday before 22:00 UTC
        return False
    return True


def _claude_in_cooloff() -> tuple[bool, int]:
    """Check the shared cooloff key. Returns (in_cooloff, seconds_remaining)."""
    r = _get_fw_redis()
    if r is None:
        return False, 0
    try:
        raw = r.get(_CLAUDE_COOLOFF_KEY)
        if not raw:
            return False, 0
        reset_unix = float(raw)
        remaining = int(reset_unix - time.time())
        return remaining > 0, max(remaining, 0)
    except Exception:
        return False, 0


# ---------------------------------------------------------------------------
# Telemetry — pushes one record per generate()/classify() call to shared
# Redis sorted set (same key as vybe-trading's llm_router)
# ---------------------------------------------------------------------------

_fw_redis: Any = None
_LLM_CALLS_KEY = "llm:calls"
_LLM_CALLS_MAX = 10_000


def _get_fw_redis() -> Any:
    global _fw_redis
    if _fw_redis is None:
        try:
            import redis as _rc  # noqa: PLC0415
            _fw_redis = _rc.from_url(
                os.getenv("REDIS_URL", "redis://127.0.0.1:6379"),
                socket_connect_timeout=1,
                socket_timeout=1,
            )
        except Exception:
            pass
    return _fw_redis


def _emit_fw_call(
    fn_name: str,
    provider: str,
    model: str,
    latency_ms: int,
    ok: bool,
    error: str | None = None,
) -> None:
    """Push firstwave LLM call record to shared llm:calls sorted set. Never raises."""
    try:
        r = _get_fw_redis()
        if r is None:
            return
        now = datetime.now(UTC)
        record: dict[str, Any] = {
            "id": str(uuid.uuid4())[:8],
            "ts": now.isoformat(),
            "ts_unix": now.timestamp(),
            "source": "firstwave",
            "caller": fn_name,
            "model_hint": fn_name,
            "force_quality": False,
            "attempts": [{"provider": provider, "model": model,
                           "latency_ms": latency_ms, "ok": ok, "error": error}],
            "winner": provider if ok else None,
            "winner_model": model if ok else None,
            "total_latency_ms": latency_ms,
            "ok": ok,
        }
        member = json.dumps(record, separators=(",", ":"))
        pipe = r.pipeline()
        pipe.zadd(_LLM_CALLS_KEY, {member: now.timestamp()})
        pipe.zremrangebyrank(_LLM_CALLS_KEY, 0, -(_LLM_CALLS_MAX + 1))
        pipe.execute()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Anthropic SDK / CLI helpers
# ---------------------------------------------------------------------------


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
    """Claude Code CLI call — uses Claude Max OAuth, no API key needed.

    Gated by the shared cooloff key written by vybe-trading's llm_router:
    when the Max account is in a limit window, retries here would just burn
    the same throttle. Raise immediately and let the caller defer."""
    in_cooloff, wait_s = _claude_in_cooloff()
    if in_cooloff:
        raise RuntimeError(
            f"Claude CLI skipped — Max-limit cooloff active ({wait_s}s left)"
        )
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
                detail = (result.stderr or result.stdout or "no output")[:300]
                raise RuntimeError(f"Claude CLI error: {detail}")
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


def _try_ollama(system_prompt: str, user_message: str, model: str) -> str | None:
    """Attempt Ollama completion. Returns None if unreachable or error.

    `keep_alive=-1` keeps the model pinned in VRAM after the call returns;
    desktop also sets OLLAMA_KEEP_ALIVE=-1 globally but specifying it
    per-request survives any container env reset and makes intent explicit.
    """
    try:
        resp = httpx.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": f"{system_prompt}\n\n{user_message}" if system_prompt else user_message,
                "options": {"num_ctx": 16384},
                "keep_alive": -1,
                "stream": False,
            },
            timeout=_OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        return str(resp.json()["response"])
    except Exception as e:
        logger.warning("Ollama %s unavailable (%s)", model, e.__class__.__name__)
        return None


def ollama_available() -> bool:
    """Return True if the Ollama host is reachable (fast ping, no model load)."""
    try:
        resp = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate(system_prompt: str, user_message: str, model: str = SONNET) -> str:
    """Generate a response — Ollama first (gpt-oss → Claude)."""
    if _is_vybe_trading_window():
        raise VybeTradingWindowError(
            "firstwave LLM call deferred — vybe-trading active window. "
            "Set FIRSTWAVE_LLM_ALWAYS_ALLOW=1 to override."
        )
    t0 = time.monotonic()
    result = _try_ollama(system_prompt, user_message, _OLLAMA_PRIMARY)
    if result is not None:
        _emit_fw_call("generate", "ollama", _OLLAMA_PRIMARY,
                      int((time.monotonic() - t0) * 1000), ok=True)
        return result
    _emit_fw_call("generate", "ollama", _OLLAMA_PRIMARY,
                  int((time.monotonic() - t0) * 1000), ok=False)

    t1 = time.monotonic()
    use_sdk = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    provider = "sdk" if use_sdk else "cli"
    try:
        if use_sdk:
            out = _call_sdk(system_prompt, user_message, model)
        else:
            out = _call_cli(system_prompt, user_message, model)
        _emit_fw_call("generate", provider, model,
                      int((time.monotonic() - t1) * 1000), ok=True)
        return out
    except Exception as exc:
        _emit_fw_call("generate", provider, model,
                      int((time.monotonic() - t1) * 1000), ok=False,
                      error=type(exc).__name__)
        raise


def classify(system_prompt: str, user_message: str) -> str:
    """Classify — Ollama first (gpt-oss → Claude Haiku)."""
    if _is_vybe_trading_window():
        raise VybeTradingWindowError(
            "firstwave LLM call deferred — vybe-trading active window. "
            "Set FIRSTWAVE_LLM_ALWAYS_ALLOW=1 to override."
        )
    t0 = time.monotonic()
    result = _try_ollama(system_prompt, user_message, _OLLAMA_PRIMARY)
    if result is not None:
        _emit_fw_call("classify", "ollama", _OLLAMA_PRIMARY,
                      int((time.monotonic() - t0) * 1000), ok=True)
        return result
    _emit_fw_call("classify", "ollama", _OLLAMA_PRIMARY,
                  int((time.monotonic() - t0) * 1000), ok=False)

    t1 = time.monotonic()
    use_sdk = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    provider = "sdk" if use_sdk else "cli"
    model = HAIKU
    try:
        if use_sdk:
            out = _call_sdk(system_prompt, user_message, model)
        else:
            out = _call_cli(system_prompt, user_message, model)
        _emit_fw_call("classify", provider, model,
                      int((time.monotonic() - t1) * 1000), ok=True)
        return out
    except Exception as exc:
        _emit_fw_call("classify", provider, model,
                      int((time.monotonic() - t1) * 1000), ok=False,
                      error=type(exc).__name__)
        raise
