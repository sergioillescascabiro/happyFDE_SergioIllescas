import pytest
from fastapi.testclient import TestClient
from app.main import app

TOKEN = "hr-dashboard-token-change-in-production"
HEADERS = {"X-Dashboard-Token": TOKEN}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_overview_metrics(client):
    r = client.get("/api/metrics/overview", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "total_loads" in data
    assert "conversion_rate" in data
    assert data["total_loads"] >= 30

def test_calls_over_time(client):
    r = client.get("/api/metrics/calls-over-time", headers=HEADERS)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_top_lanes(client):
    r = client.get("/api/metrics/top-lanes", headers=HEADERS)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_equipment_distribution(client):
    r = client.get("/api/metrics/equipment-distribution", headers=HEADERS)
    assert r.status_code == 200
    items = r.json()
    assert len(items) > 0
    assert "equipment_type" in items[0]
    assert "count" in items[0]

def test_negotiation_analysis(client):
    r = client.get("/api/metrics/negotiation-analysis", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "avg_rounds" in data

def test_sentiment_distribution(client):
    r = client.get("/api/metrics/sentiment", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "positive" in data

def test_metrics_require_auth(client):
    r = client.get("/api/metrics/overview")
    assert r.status_code == 401
