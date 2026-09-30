"""Unit tests for the API-key gate in `backend.auth`.

These build a minimal app around the middleware rather than exercising the real
routers: the real protected routes talk to Supabase, so asserting against them
would make the result depend on a live external service (and on DNS). The
middleware's contract is what matters here, and it is testable in isolation.
"""

import pytest
from fastapi import FastAPI
from backend.auth import _is_public, api_key_middleware
from backend.tests.conftest import TEST_API_KEY, PlainTestClient

API_KEY = TEST_API_KEY


@pytest.fixture
def client(monkeypatch):
    """A minimal app carrying only the API-key middleware."""
    monkeypatch.setenv("BACKEND_API_KEY", API_KEY)

    app = FastAPI()
    app.middleware("http")(api_key_middleware)

    @app.get("/protected")
    def protected():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/u/{token}")
    def unsubscribe(token: str):
        return {"token": token}

    @app.post("/webhook/telegram")
    def telegram():
        return {"ok": True}

    # conftest patches TestClient to send the key by default; use the unpatched
    # class so each test decides what header to send.
    return PlainTestClient(app)


@pytest.mark.parametrize("path", ["/health", "/u/any-token"])
def test_public_get_routes_need_no_key(client, path):
    assert client.get(path).status_code == 200


def test_public_webhook_needs_no_key(client):
    assert client.post("/webhook/telegram").status_code == 200


def test_protected_route_without_key_is_401(client):
    assert client.get("/protected").status_code == 401


def test_protected_route_with_wrong_key_is_401(client):
    assert client.get("/protected", headers={"X-API-Key": "wrong"}).status_code == 401


def test_protected_route_with_correct_key_is_allowed(client):
    response = client.get("/protected", headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_unset_server_key_fails_closed_with_503(client, monkeypatch):
    """A missing server-side key must never mean 'allow all'."""
    monkeypatch.delenv("BACKEND_API_KEY", raising=False)
    assert client.get("/protected", headers={"X-API-Key": API_KEY}).status_code == 503


def test_options_preflight_is_not_gated(client):
    """CORS preflight carries no custom headers; the CORS layer must answer it."""
    assert client.options("/protected").status_code != 401


@pytest.mark.parametrize(
    "path,public",
    [
        ("/health", True),
        ("/u/abc123", True),
        ("/webhook/telegram", True),
        ("/leads", False),
        ("/analytics/conversion", False),
        ("/healthz", False),          # only the exact /health path is exempt
        ("/u", False),                # the prefix is "/u/", not "/u"
    ],
)
def test_is_public_classification(path, public):
    assert _is_public(path) is public
