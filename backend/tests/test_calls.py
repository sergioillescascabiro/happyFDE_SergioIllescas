import pytest
from fastapi.testclient import TestClient
from app.main import app

TOKEN = "hr-dashboard-token-change-in-production"
HEADERS = {"X-Dashboard-Token": TOKEN}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_list_calls(client):
    r = client.get("/api/calls", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 40
    assert "items" in data

def test_filter_calls_by_outcome(client):
    r = client.get("/api/calls?outcome=booked", headers=HEADERS)
    assert r.status_code == 200
    items = r.json()["items"]
    for item in items:
        assert item["outcome"] == "booked"

def test_get_call_detail(client):
    calls_r = client.get("/api/calls", headers=HEADERS)
    call_id = calls_r.json()["items"][0]["id"]
    r = client.get(f"/api/calls/{call_id}", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "negotiations" in data

def test_live_calls(client):
    r = client.get("/api/calls/live", headers=HEADERS)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_calls_require_auth(client):
    r = client.get("/api/calls")
    assert r.status_code == 401
