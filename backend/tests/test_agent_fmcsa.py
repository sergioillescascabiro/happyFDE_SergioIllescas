"""Tests for FMCSA carrier verification endpoint (Stage 1)."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.config import settings

AGENT_KEY = "hr-agent-key-change-in-production"
AGENT_HEADERS = {"X-Agent-Key": AGENT_KEY}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_verify_carrier_existing_mc(client, monkeypatch):
    """MC 98765 (HR Transportation) is in the seed DB. With mock mode, should return cached or
    freshly verified carrier data and is_authorized=True."""
    monkeypatch.setattr(settings, "FMCSA_MOCK", True)

    r = client.post(
        "/api/agent/carriers/verify",
        json={"mc_number": "98765"},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["mc_number"] == "98765"
    assert "legal_name" in data
    assert isinstance(data["is_authorized"], bool)
    assert "message" in data
    assert "status" in data
    assert "source" in data


def test_verify_carrier_new_mc_mock(client, monkeypatch):
    """MC 99999 is not in the seed DB. Mock mode should create a new carrier record."""
    monkeypatch.setattr(settings, "FMCSA_MOCK", True)

    r = client.post(
        "/api/agent/carriers/verify",
        json={"mc_number": "99999"},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["mc_number"] == "99999"
    assert data["legal_name"]  # non-empty
    assert "id" in data
    assert data["source"] == "fmcsa"
    # 99999 ends in 9 (not 0), so should be authorized
    assert data["is_authorized"] is True
    assert "message" in data
    assert "authorized" in data["message"].lower()


def test_verify_carrier_unauthorized_mc(client, monkeypatch):
    """MC ending in '0' (e.g. '12340') should return is_authorized=False in mock mode."""
    monkeypatch.setattr(settings, "FMCSA_MOCK", True)

    r = client.post(
        "/api/agent/carriers/verify",
        json={"mc_number": "12340"},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["mc_number"] == "12340"
    assert data["is_authorized"] is False
    assert "NOT authorized" in data["message"] or "not authorized" in data["message"].lower()


def test_verify_carrier_missing_auth(client):
    """Calling without X-Agent-Key should return 401."""
    r = client.post(
        "/api/agent/carriers/verify",
        json={"mc_number": "98765"},
    )
    assert r.status_code == 401


def test_verify_carrier_invalid_body(client):
    """Sending empty body (missing mc_number) should return 422."""
    r = client.post(
        "/api/agent/carriers/verify",
        json={},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 422
