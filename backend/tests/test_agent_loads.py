"""Tests for agent load search endpoint (Stage 2).

The endpoint now returns a single load object (best match by closest pickup
date) instead of an array. This is intentional — HappyRobot tool nodes parse
single objects correctly, while arrays cause {} output.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

AGENT_KEY = "hr-agent-key-change-in-production"
AGENT_HEADERS = {"X-Agent-Key": AGENT_KEY}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_agent_load_search_no_filters(client):
    """No filters: returns one available load (the soonest by pickup date)."""
    r = client.get("/api/agent/loads/search", headers=AGENT_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict), "Expected a single object, not a list"
    assert "load_id" in data
    assert "loadboard_rate" in data
    assert "per_mile_rate" in data


def test_agent_load_search_by_origin(client):
    """Filter by origin=Dallas returns a load from Dallas."""
    r = client.get("/api/agent/loads/search?origin=Dallas", headers=AGENT_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert "Dallas" in data["origin"]


def test_agent_load_search_by_equipment(client):
    """Filter by equipment_type=Dry Van returns a Dry Van load."""
    r = client.get("/api/agent/loads/search?equipment_type=Dry%20Van", headers=AGENT_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert data["equipment_type"].lower() == "dry van"


def test_agent_load_search_no_max_min_rate(client):
    """max_rate and min_rate must NEVER appear in agent load search responses."""
    r = client.get("/api/agent/loads/search", headers=AGENT_HEADERS)
    assert r.status_code == 200
    response_text = r.text
    assert "max_rate" not in response_text, "max_rate LEAKED in agent load search response!"
    assert "min_rate" not in response_text, "min_rate LEAKED in agent load search response!"


def test_agent_load_search_no_auth(client):
    """Missing X-Agent-Key should return 401."""
    r = client.get("/api/agent/loads/search")
    assert r.status_code == 401


def test_agent_load_search_no_match(client):
    """Impossible filter combo should return 404 with a clear message."""
    r = client.get(
        "/api/agent/loads/search?origin=Atlantis&destination=Mordor",
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 404
    assert "No available loads" in r.json()["detail"]
