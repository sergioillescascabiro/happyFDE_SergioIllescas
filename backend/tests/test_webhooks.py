"""Tests for HappyRobot webhook mock endpoints (Stage 5)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.call import Call

AGENT_KEY = "hr-agent-key-change-in-production"
AGENT_HEADERS = {"X-Agent-Key": AGENT_KEY}

HR_CALL_ID_1 = "HR-TEST-001"
HR_CALL_ID_2 = "HR-TEST-002"
HR_CALL_ID_UNKNOWN = "HR-DOES-NOT-EXIST-99999"


@pytest.fixture(autouse=True)
def cleanup_webhook_calls():
    """Remove test call records created by webhook tests."""
    _delete_calls([HR_CALL_ID_1, HR_CALL_ID_2])
    yield
    _delete_calls([HR_CALL_ID_1, HR_CALL_ID_2])


def _delete_calls(hr_ids: list):
    db = SessionLocal()
    try:
        for hr_id in hr_ids:
            calls = db.query(Call).filter(Call.happyrobot_call_id == hr_id).all()
            for call in calls:
                db.delete(call)
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── Test 1: call-started creates a call record ───────────────────────────────

def test_webhook_call_started(client):
    """POST call-started payload → creates a call record."""
    r = client.post(
        "/api/webhooks/call-started",
        json={
            "call_id": HR_CALL_ID_1,
            "phone_number": "+1-312-555-0111",
            "direction": "inbound",
            "timestamp": "2026-04-13T14:30:00Z",
            "agent_id": "agent-abc123",
            "metadata": {},
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "received"
    assert "call_id" in data

    # Verify in DB
    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.happyrobot_call_id == HR_CALL_ID_1).first()
        assert call is not None
        assert call.outcome.value == "in_progress"
        assert call.phone_number == "+1-312-555-0111"
    finally:
        db.close()


# ── Test 2: call-ended updates the call record ───────────────────────────────

def test_webhook_call_ended(client):
    """Start a call, then end it with duration. Should update the record."""
    # Start
    start_r = client.post(
        "/api/webhooks/call-started",
        json={
            "call_id": HR_CALL_ID_2,
            "phone_number": "+1-800-555-9999",
            "direction": "inbound",
            "timestamp": "2026-04-13T15:00:00Z",
        },
        headers=AGENT_HEADERS,
    )
    assert start_r.status_code == 200
    internal_id = start_r.json()["call_id"]

    # End
    end_r = client.post(
        "/api/webhooks/call-ended",
        json={
            "call_id": HR_CALL_ID_2,
            "duration_seconds": 183,
            "end_timestamp": "2026-04-13T15:03:03Z",
            "recording_url": "https://storage.example.com/recording-001.mp3",
            "transcript_url": "https://storage.example.com/transcript-001.txt",
        },
        headers=AGENT_HEADERS,
    )
    assert end_r.status_code == 200, end_r.text
    data = end_r.json()
    assert data["status"] == "received"
    assert data["call_id"] == internal_id

    # Verify in DB
    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.happyrobot_call_id == HR_CALL_ID_2).first()
        assert call is not None
        assert call.duration_seconds == 183
        assert call.call_end is not None
        assert call.extracted_data is not None
        assert "recording_url" in call.extracted_data
        assert "transcript_url" in call.extracted_data
    finally:
        db.close()


# ── Test 3: transcript delivery stores data ──────────────────────────────────

def test_webhook_transcript_delivery(client):
    """Deliver transcript to existing call. Check stored correctly."""
    # Start the call first
    start_r = client.post(
        "/api/webhooks/call-started",
        json={
            "call_id": HR_CALL_ID_1,
            "direction": "inbound",
            "timestamp": "2026-04-13T14:30:00Z",
        },
        headers=AGENT_HEADERS,
    )
    assert start_r.status_code == 200
    internal_id = start_r.json()["call_id"]

    # Deliver transcript
    transcript_r = client.post(
        "/api/webhooks/transcript",
        json={
            "call_id": HR_CALL_ID_1,
            "transcript": [
                {"role": "assistant", "message": "Thank you for calling Acme Logistics.", "timestamp": "00:00:05"},
                {"role": "caller", "message": "Hi, I have MC 98765.", "timestamp": "00:00:12"},
            ],
            "summary": "Carrier booked load 202883.",
            "sentiment": "positive",
            "extracted_data": {
                "mc_number": "98765",
                "load_id": "202883",
                "agreed_rate": 820.00,
            },
        },
        headers=AGENT_HEADERS,
    )
    assert transcript_r.status_code == 200, transcript_r.text
    data = transcript_r.json()
    assert data["status"] == "received"
    assert data["call_id"] == internal_id

    # Verify in DB
    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.happyrobot_call_id == HR_CALL_ID_1).first()
        assert call is not None
        assert call.transcript_full is not None
        assert len(call.transcript_full) == 2
        assert call.transcript_full[0]["role"] == "assistant"
        assert call.transcript_summary == "Carrier booked load 202883."
        assert call.sentiment is not None
        assert call.extracted_data is not None
        assert call.extracted_data.get("mc_number") == "98765"
    finally:
        db.close()


# ── Test 4: call-ended for unknown HR call_id → 404 ─────────────────────────

def test_webhook_call_ended_not_found(client):
    """POST call-ended for unknown HR call_id returns 404."""
    r = client.post(
        "/api/webhooks/call-ended",
        json={
            "call_id": HR_CALL_ID_UNKNOWN,
            "duration_seconds": 60,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 404


# ── Test 5: partial transcript appends messages ──────────────────────────────

def test_webhook_partial_transcript(client):
    """POST partial-transcript → appends message to transcript_full."""
    # Start the call
    client.post(
        "/api/webhooks/call-started",
        json={"call_id": HR_CALL_ID_1, "timestamp": "2026-04-13T14:30:00Z"},
        headers=AGENT_HEADERS,
    )

    # Message 1
    client.post(
        "/api/webhooks/partial-transcript",
        json={"call_id": HR_CALL_ID_1, "role": "caller", "message": "First message"},
        headers=AGENT_HEADERS,
    )

    # Message 2
    client.post(
        "/api/webhooks/partial-transcript",
        json={"call_id": HR_CALL_ID_1, "role": "assistant", "message": "Second message"},
        headers=AGENT_HEADERS,
    )

    # Verify in DB
    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.happyrobot_call_id == HR_CALL_ID_1).first()
        assert call is not None
        assert len(call.transcript_full) == 2
        assert call.transcript_full[0]["message"] == "First message"
        assert call.transcript_full[1]["message"] == "Second message"
    finally:
        db.close()


# ── Test 6: Auth required ────────────────────────────────────────────────────

def test_webhooks_require_agent_key(client):
    """401 without X-Agent-Key header."""
    r = client.post(
        "/api/webhooks/call-started",
        json={
            "call_id": "HR-NO-AUTH",
            "direction": "inbound",
        },
    )
    assert r.status_code == 401
