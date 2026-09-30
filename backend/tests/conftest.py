"""Shared pytest configuration.

Two things have to be true before any test module imports `backend.main`:

1. `ALLOWED_HOSTS` must include `testserver`. Starlette's `TestClient` sends
   `Host: testserver`, and `TrustedHostMiddleware` answers 400 to anything not
   on the allow-list.
2. `BACKEND_API_KEY` must be set. `backend.auth` fails closed with 503 when it
   is missing, which is the correct production behaviour but makes every test
   unreachable.

Test modules build their client at import time (`client = TestClient(app)`), so
this file also swaps in a `TestClient` subclass that presents the API key by
default. conftest is imported before the test modules, so the substitution is
in place by the time they bind the name.

The auth middleware itself is exercised directly in `test_auth.py`, using a
client that does *not* get the header for free.
"""

import os

TEST_API_KEY = "test-api-key-not-a-real-secret"

os.environ.setdefault("ALLOWED_HOSTS", "testserver,localhost,127.0.0.1")
os.environ["BACKEND_API_KEY"] = TEST_API_KEY

import fastapi.testclient as _testclient  # noqa: E402  (must follow the env setup)

_PlainTestClient = _testclient.TestClient


class _AuthedTestClient(_PlainTestClient):
    """TestClient that sends `X-API-Key` unless a test overrides it."""

    def __init__(self, *args, **kwargs):
        headers = dict(kwargs.pop("headers", None) or {})
        headers.setdefault("X-API-Key", TEST_API_KEY)
        super().__init__(*args, headers=headers, **kwargs)


_testclient.TestClient = _AuthedTestClient
