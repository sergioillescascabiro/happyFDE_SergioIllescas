"""Tests for agent call management endpoints (Stage 4)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.carrier import Carrier

AGENT_KEY = "hr-agent-key-change-in-production"
AGENT_HEADERS = {"X-Agent-Key": AGENT_KEY}

# MC numbers
EXISTING_MC = "98765"   # present in seed data
NEW_MC = "77777"        # not in seed data


@pytest.fixture(autouse=True)
def cleanup_new_carrier():
    """Remove the test carrier for MC 77777 before and after each test."""
    _delete_carrier(NEW_MC)
    yield
    _delete_carrier(NEW_MC)


def _delete_carrier(mc: str):
    db = SessionLocal()
    try:
        carrier = db.query(Carrier).filter(Carrier.mc_number == mc).first()
        if carrier:
            db.delete(carrier)
            db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── Test 1: Create call for existing carrier ─────────────────────────────────

def test_create_call_existing_carrier(client):
    """Create call for MC 98765 (in DB). Should return 200 with call_id."""
    r = client.post(
        "/api/agent/calls",
        json={"mc_number": EXISTING_MC, "direction": "inbound"},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "call_id" in data
    assert data["mc_number"] == EXISTING_MC
    assert data["direction"] == "inbound"
    assert "carrier_id" in data
    assert data["carrier_id"] is not None
    assert "call_start" in data


# ── Test 2: Create call for new carrier (not in DB) ─────────────────────────

def test_create_call_new_carrier(client):
    """Create call for MC 77777 (not in DB). Should auto-create carrier + call."""
    r = client.post(
        "/api/agent/calls",
        json={"mc_number": NEW_MC, "direction": "inbound", "phone_number": "+1-800-555-0000"},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "call_id" in data
    assert data["mc_number"] == NEW_MC
    assert data["carrier_id"] is not None

    # Carrier was created in DB
    db = SessionLocal()
    try:
        carrier = db.query(Carrier).filter(Carrier.mc_number == NEW_MC).first()
        assert carrier is not None
        assert carrier.status.value == "in_review"
        assert carrier.source.value == "manual"
        assert carrier.is_authorized is False
    finally:
        db.close()


# ── Test 3: Update call outcome ──────────────────────────────────────────────

def test_update_call_outcome(client):
    """PATCH to set outcome to 'no_loads_available'."""
    # Create a call first
    create_r = client.post(
        "/api/agent/calls",
        json={"mc_number": EXISTING_MC},
        headers=AGENT_HEADERS,
    )
    assert create_r.status_code == 200
    call_id = create_r.json()["call_id"]

    # Update outcome
    patch_r = client.patch(
        f"/api/agent/calls/{call_id}",
        json={"outcome": "no_loads_available"},
        headers=AGENT_HEADERS,
    )
    assert patch_r.status_code == 200, patch_r.text
    data = patch_r.json()
    assert data["outcome"] == "no_loads_available"
    assert data["call_id"] == call_id


# ── Test 4: Transfer call ────────────────────────────────────────────────────

def test_transfer_call(client):
    """POST /transfer sets transferred_to_rep=True and outcome='transferred'."""
    create_r = client.post(
        "/api/agent/calls",
        json={"mc_number": EXISTING_MC},
        headers=AGENT_HEADERS,
    )
    assert create_r.status_code == 200
    call_id = create_r.json()["call_id"]

    transfer_r = client.post(
        f"/api/agent/calls/{call_id}/transfer",
        headers=AGENT_HEADERS,
    )
    assert transfer_r.status_code == 200, transfer_r.text
    data = transfer_r.json()
    assert data["status"] == "success"
    assert "Transfer was successful" in data["message"]

    # Verify DB state via a patch round-trip (PATCH returns updated fields)
    get_r = client.patch(
        f"/api/agent/calls/{call_id}",
        json={},
        headers=AGENT_HEADERS,
    )
    assert get_r.json()["outcome"] == "transferred"


# ── Test 5: Classify call ────────────────────────────────────────────────────

def test_classify_call(client):
    """POST /classify sets outcome, sentiment, call_end, and duration_seconds."""
    create_r = client.post(
        "/api/agent/calls",
        json={"mc_number": EXISTING_MC},
        headers=AGENT_HEADERS,
    )
    assert create_r.status_code == 200
    call_id = create_r.json()["call_id"]

    classify_r = client.post(
        f"/api/agent/calls/{call_id}/classify",
        json={
            "outcome": "booked",
            "sentiment": "positive",
            "transcript_summary": "Carrier booked load 202883.",
            "extracted_data": {"load_id": "202883", "final_rate": 820.00},
        },
        headers=AGENT_HEADERS,
    )
    assert classify_r.status_code == 200, classify_r.text
    data = classify_r.json()
    assert data["status"] == "classified"
    assert data["call_id"] == call_id
    assert data["outcome"] == "booked"
    assert data["duration_seconds"] is not None
    assert data["duration_seconds"] >= 0


# ── Test 6: Append transcript entries ───────────────────────────────────────

def test_append_transcript(client):
    """POST /transcript appends entry; second call returns entry_count=2."""
    create_r = client.post(
        "/api/agent/calls",
        json={"mc_number": EXISTING_MC},
        headers=AGENT_HEADERS,
    )
    assert create_r.status_code == 200
    call_id = create_r.json()["call_id"]

    # First entry
    r1 = client.post(
        f"/api/agent/calls/{call_id}/transcript",
        json={"role": "assistant", "message": "What is your MC number?"},
        headers=AGENT_HEADERS,
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["entry_count"] == 1
    assert r1.json()["status"] == "ok"

    # Second entry
    r2 = client.post(
        f"/api/agent/calls/{call_id}/transcript",
        json={"role": "caller", "message": "It's MC 98765."},
        headers=AGENT_HEADERS,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["entry_count"] == 2


# ── Test 7: Auth required ────────────────────────────────────────────────────

def test_calls_require_agent_key(client):
    """401 without X-Agent-Key header."""
    r = client.post(
        "/api/agent/calls",
        json={"mc_number": EXISTING_MC},
    )
    assert r.status_code == 401


# ── Test 8: Classify with invalid outcome returns 422 ───────────────────────

def test_classify_invalid_outcome(client):
    """Invalid outcome string returns 422."""
    create_r = client.post(
        "/api/agent/calls",
        json={"mc_number": EXISTING_MC},
        headers=AGENT_HEADERS,
    )
    assert create_r.status_code == 200
    call_id = create_r.json()["call_id"]

    classify_r = client.post(
        f"/api/agent/calls/{call_id}/classify",
        json={"outcome": "invalid_outcome_value"},
        headers=AGENT_HEADERS,
    )
    assert classify_r.status_code == 422
