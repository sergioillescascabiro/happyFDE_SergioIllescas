import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

VALID_DASHBOARD_TOKEN = "hr-dashboard-token-change-in-production"
VALID_AGENT_KEY = "hr-agent-key-change-in-production"

class TestDashboardAuth:
    def test_health_auth_valid_token(self, client):
        r = client.get("/api/health/auth", headers={"X-Dashboard-Token": VALID_DASHBOARD_TOKEN})
        assert r.status_code == 200
        assert r.json()["authenticated"] is True

    def test_health_auth_missing_token(self, client):
        r = client.get("/api/health/auth")
        assert r.status_code == 401

    def test_health_auth_invalid_token(self, client):
        r = client.get("/api/health/auth", headers={"X-Dashboard-Token": "wrong-token"})
        assert r.status_code == 401

    def test_health_no_auth_needed(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200

class TestAgentAuth:
    def test_agent_key_dependency_valid(self, client):
        """Test that the agent key dependency works when a protected endpoint is added."""
        # We test via a simple check of the middleware function directly
        from app.middleware.auth import require_agent_key
        from fastapi import HTTPException
        # Valid key should not raise
        result = require_agent_key(VALID_AGENT_KEY)
        assert result == VALID_AGENT_KEY

    def test_agent_key_dependency_invalid(self, client):
        from app.middleware.auth import require_agent_key
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            require_agent_key("wrong-key")
        assert exc_info.value.status_code == 401

    def test_agent_key_dependency_missing(self, client):
        from app.middleware.auth import require_agent_key
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            require_agent_key(None)
        assert exc_info.value.status_code == 401
