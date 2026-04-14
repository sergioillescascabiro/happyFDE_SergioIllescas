import pytest
from fastapi.testclient import TestClient
from app.main import app

TOKEN = "hr-dashboard-token-change-in-production"
HEADERS = {"X-Dashboard-Token": TOKEN}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

class TestFinancialMetrics:
    def test_financial_metrics_requires_auth(self, client):
        r = client.get("/api/metrics/financial")
        assert r.status_code == 401

    def test_financial_metrics_structure(self, client):
        r = client.get("/api/metrics/financial", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "total_revenue" in data
        assert "net_margin" in data
        assert "avg_spread_pct" in data
        assert "automation_rate" in data
        assert "avg_time_to_cover_hours" in data
        assert "covered_load_count" in data
        assert "ai_booked_count" in data

    def test_covered_loads_have_booked_rate(self, client):
        r = client.get("/api/loads?status=covered", headers=HEADERS)
        assert r.status_code == 200
        items = r.json()["items"]
        for item in items:
            assert "booked_rate" in item
            assert "margin_pct" in item
            assert "is_ai_booked" in item

    def test_delivered_status_exists(self, client):
        r = client.get("/api/loads?status=delivered", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    def test_refresh_status_endpoint(self, client):
        r = client.post("/api/loads/refresh-status", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "updated" in data

    def test_quoted_rate_not_in_load_response(self, client):
        """quoted_rate must never appear in load responses (broker-only data in Quote)"""
        r = client.get("/api/loads", headers=HEADERS)
        assert r.status_code == 200
        # quoted_rate should not appear directly in load list responses
        # (it lives in the Quote entity, not Load)
        items = r.json()["items"]
        for item in items:
            assert "quoted_rate" not in item
