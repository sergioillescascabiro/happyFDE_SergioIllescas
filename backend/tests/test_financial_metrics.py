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
        assert "avg_discount_pct" in data
        assert "automation_rate" in data
        assert "avg_time_to_cover_hours" in data
        assert "covered_load_count" in data
        assert "ai_booked_count" in data

    def test_avg_discount_pct_is_numeric(self, client):
        """avg_discount_pct must be a non-negative number."""
        r = client.get("/api/metrics/financial", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["avg_discount_pct"], (int, float))
        assert data["avg_discount_pct"] >= 0

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

    def test_agent_performance_requires_auth(self, client):
        r = client.get("/api/metrics/agent-performance")
        assert r.status_code == 401

    def test_agent_performance_structure(self, client):
        r = client.get("/api/metrics/agent-performance", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["agent_name"] == "Paul"
        assert "ai" in data
        assert "manual" in data
        assert "margin_delta_pct" in data
        assert "automation_rate" in data
        for key in ("count", "avg_margin_pct", "total_booked_revenue", "avg_booked_rate"):
            assert key in data["ai"]
            assert key in data["manual"]

    def test_agent_performance_automation_rate_bounds(self, client):
        r = client.get("/api/metrics/agent-performance", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert 0.0 <= data["automation_rate"] <= 100.0

    def test_quoted_rate_in_load_response(self, client):
        """quoted_rate must appear in load responses (broker dashboard needs shipper price)"""
        r = client.get("/api/loads", headers=HEADERS)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) > 0
        # Every load should have quoted_rate (may be null for loads without a linked quote)
        for item in items:
            assert "quoted_rate" in item
        # Loads that have a quote_id must have a non-null quoted_rate
        loads_with_quote = [i for i in items if i.get("quote_id")]
        for item in loads_with_quote:
            assert item["quoted_rate"] is not None, f"Load {item['load_id']} has quote_id but null quoted_rate"
