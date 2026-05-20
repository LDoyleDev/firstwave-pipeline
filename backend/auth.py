"""API-key gate for the FastAPI backend.

The backend is published on the public internet via the Cloudflare tunnel
(`firstwave.vybe-dev.com`). Every route except a small public set requires an
`X-API-Key` header matching `BACKEND_API_KEY`. Server-to-server callers (the
n8n crons, scripts) and the dev dashboard send the key; the genuinely public
routes below are exempt because their callers cannot present it.
"""

import logging
import os
import secrets
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Routes reachable WITHOUT the API key:
#   /health            — liveness probe (uptime checks, the deploy pipeline).
#   /u/{token}         — one-click unsubscribe, opened by email recipients.
#   /webhook/telegram  — called by Telegram's servers, which cannot send our key.
_PUBLIC_EXACT: frozenset[str] = frozenset({"/health"})
_PUBLIC_PREFIXES: tuple[str, ...] = ("/u/", "/webhook/telegram")


def _is_public(path: str) -> bool:
    """True if `path` may be served without an API key."""
    return path in _PUBLIC_EXACT or path.startswith(_PUBLIC_PREFIXES)


async def api_key_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Reject any non-public request that lacks a valid `X-API-Key` header."""
    # CORS preflight carries no custom headers — let the CORS middleware answer it.
    if request.method == "OPTIONS" or _is_public(request.url.path):
        return await call_next(request)

    expected = os.getenv("BACKEND_API_KEY", "")
    if not expected:
        # Fail closed: a missing server-side key must never mean "allow all".
        logger.error("BACKEND_API_KEY is not set — refusing protected requests")
        return JSONResponse({"detail": "server auth not configured"}, status_code=503)

    provided = request.headers.get("X-API-Key", "")
    # compare_digest avoids leaking the key length/prefix via response timing.
    if not (provided and secrets.compare_digest(provided, expected)):
        return JSONResponse({"detail": "unauthorized"}, status_code=401)

    return await call_next(request)
