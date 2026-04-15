"""Tests for POST /api/calls/cleanup — stale in_progress call cancellation."""
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.call import Call, CallOutcome, CallSentiment, CallDirection

TOKEN = "hr-dashboard-token-change-in-production"
HEADERS = {"X-Dashboard-Token": TOKEN}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def _make_call(outcome: CallOutcome, call_start: datetime, db) -> Call:
    """Insert a minimal call row for testing."""
    call = Call(
        id=str(uuid.uuid4()),
        mc_number="99999",
        direction=CallDirection.inbound,
        call_start=call_start,
        call_end=None,
        duration_seconds=None,
        outcome=outcome,
        sentiment=CallSentiment.neutral,
        transcript_summary="test call",
        transferred_to_rep=False,
        happyrobot_call_id=f"HR-TEST-{uuid.uuid4().hex[:6]}",
        use_case="Inbound Carrier Sales",
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


class TestCleanupEndpoint:
    def test_cleanup_requires_auth(self, client):
        r = client.post("/api/calls/cleanup")
        assert r.status_code == 401

    def test_cleanup_cancels_stale_in_progress(self, client, db):
        """in_progress call older than 30 min should be cancelled."""
        old_start = datetime.now(timezone.utc) - timedelta(minutes=60)
        call = _make_call(CallOutcome.in_progress, old_start, db)

        r = client.post("/api/calls/cleanup", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["cancelled_count"] >= 1
        assert call.id in data["call_ids"]

        # Verify the DB state changed
        db.expire(call)
        db.refresh(call)
        assert call.outcome == CallOutcome.cancelled
        assert call.call_end is not None

        # Cleanup
        db.delete(call)
        db.commit()

    def test_cleanup_does_not_cancel_recent_in_progress(self, client, db):
        """in_progress call within last 30 min should NOT be cancelled."""
        recent_start = datetime.now(timezone.utc) - timedelta(minutes=5)
        call = _make_call(CallOutcome.in_progress, recent_start, db)

        r = client.post("/api/calls/cleanup", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        # Recent call must not be in the cancelled list
        assert call.id not in data["call_ids"]

        # Verify the call is still in_progress
        db.expire(call)
        db.refresh(call)
        assert call.outcome == CallOutcome.in_progress

        # Cleanup
        db.delete(call)
        db.commit()

    def test_cleanup_returns_correct_structure(self, client):
        """Response must always include cancelled_count and call_ids."""
        r = client.post("/api/calls/cleanup", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "cancelled_count" in data
        assert "call_ids" in data
        assert isinstance(data["cancelled_count"], int)
        assert isinstance(data["call_ids"], list)

    def test_cleanup_no_stale_calls_returns_zero(self, client, db):
        """When no stale calls exist, cancelled_count should be 0."""
        # Ensure any pre-existing stale calls are cleaned first
        client.post("/api/calls/cleanup", headers=HEADERS)

        # Run cleanup again — nothing left to cancel
        r = client.post("/api/calls/cleanup", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["cancelled_count"] == 0
        assert data["call_ids"] == []
