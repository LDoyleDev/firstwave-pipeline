"""Tests for the API-key gate in `backend.auth`.

Uses the unpatched TestClient so the header is only sent when a test sends it.
"""

import importlib

import pytest

from backend.main import app
from backend.tests.conftest import TEST_API_KEY, _PlainTestClient

client = _PlainTestClient(app)


@pytest.mark.parametrize("path", ["/health", "/u/some-token", "/webhook/telegram"])
def test_public_routes_need_no_key(path):
    """The three genuinely public routes must stay reachable without a key."""
    response = client.get(path) if path != "/webhook/telegram" else client.post(path, json={})
    assert response.status_code != 401, f"{path} should not require an API key"


def test_protected_route_without_key_is_401():
    assert client.get("/analytics/conversion").status_code == 401


def test_protected_route_with_wrong_key_is_401():
    response = client.get("/analytics/conversion", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_protected_route_with_correct_key_passes_the_gate():
    """A valid key must get past auth — anything but 401/503 proves the gate opened."""
    response = client.get("/analytics/conversion", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code not in (401, 503)


def test_unset_server_key_fails_closed_with_503(monkeypatch):
    """A missing server-side key must never mean 'allow all'."""
    monkeypatch.delenv("BACKEND_API_KEY", raising=False)
    response = client.get("/analytics/conversion", headers={"X-API-Key": "anything"})
    assert response.status_code == 503
