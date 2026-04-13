import pytest
from fastapi.testclient import TestClient
from app.main import app

TOKEN = "hr-dashboard-token-change-in-production"
HEADERS = {"X-Dashboard-Token": TOKEN}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_list_carriers(client):
    r = client.get("/api/carriers", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 15
    assert len(data["items"]) >= 15

def test_get_carrier_by_mc(client):
    r = client.get("/api/carriers/98765", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["mc_number"] == "98765"
    assert data["legal_name"]  # FMCSA verification may update the name; just check it exists

def test_carrier_not_found(client):
    r = client.get("/api/carriers/999999999", headers=HEADERS)
    assert r.status_code == 404

def test_carriers_require_auth(client):
    r = client.get("/api/carriers")
    assert r.status_code == 401
