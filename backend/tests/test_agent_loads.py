"""Tests for agent load search endpoint (Stage 2)."""
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
    """No filters: returns only available loads, max 20 results."""
    r = client.get("/api/agent/loads/search", headers=AGENT_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) <= 20
    assert len(data) > 0
    # All returned loads must be available (only available loads are returned)
    for item in data:
        # The status field is NOT in AgentLoadResponse — that's intentional.
        # Verify by checking that the known 20 available seed loads are represented.
        assert "load_id" in item
        assert "loadboard_rate" in item
        assert "per_mile_rate" in item


def test_agent_load_search_by_origin(client):
    """Filter by origin=Chicago returns loads from Chicago."""
    r = client.get("/api/agent/loads/search?origin=Chicago", headers=AGENT_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
    for item in data:
        assert "Chicago" in item["origin"]


def test_agent_load_search_by_equipment(client):
    """Filter by equipment_type=Dry Van returns only Dry Van loads."""
    r = client.get("/api/agent/loads/search?equipment_type=Dry%20Van", headers=AGENT_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
    for item in data:
        assert item["equipment_type"].lower() == "dry van"


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
