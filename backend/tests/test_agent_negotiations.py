"""Tests for agent negotiation engine endpoint (Stage 3).

Seed data for load "202883":
  - equipment: Flatbed, miles: 410
  - loadboard_rate: 1075.0   (target price — total)
  - max_rate:       1225.0   (ceiling — never exposed)

Decision logic (broker profit-maximization):
  - offer <= 1075.0              → accept immediately (carrier takes market rate or less)
  - 1075.0 < offer <= 1225.0, round 1  → counter at loadboard_rate (rounded to nearest $25)
  - 1075.0 < offer <= 1225.0, round 2  → counter at midpoint(loadboard_rate, offer)
  - 1075.0 < offer <= 1225.0, round 3+ → accept at carrier_offer
  - offer > 1225.0               → reject (above ceiling)
"""
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.load import Load
from app.models.call import Call, CallDirection, CallOutcome

AGENT_KEY = "hr-agent-key-change-in-production"
AGENT_HEADERS = {"X-Agent-Key": AGENT_KEY}

# Known values from seed data (computed deterministically with random.seed(42))
LOAD_ID_HUMAN = "202883"  # load_id field (human-readable)
LOADBOARD_RATE = 1075.0
MAX_RATE = 1225.0  # ~114% of loadboard_rate (never exposed in responses)

# Cache resolved UUIDs
_cache: dict = {}


def get_load_uuid() -> str:
    """Resolve the UUID (Load.id) for load 202883 from the real DB."""
    if "load_uuid" not in _cache:
        db = SessionLocal()
        try:
            load = db.query(Load).filter(Load.load_id == LOAD_ID_HUMAN).first()
            assert load is not None, f"Load {LOAD_ID_HUMAN} not found in DB — did you seed the DB?"
            _cache["load_uuid"] = load.id
        finally:
            db.close()
    return _cache["load_uuid"]


def create_test_call() -> str:
    """Create a minimal Call record in the DB and return its id."""
    db = SessionLocal()
    try:
        call = Call(
            id=str(uuid.uuid4()),
            mc_number="TEST",
            direction=CallDirection.inbound,
            call_start=datetime.utcnow(),
            outcome=CallOutcome.in_progress,
            use_case="Inbound Carrier Sales",
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        return call.id
    finally:
        db.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── Test 1: Accept when offer == loadboard_rate ──────────────────────────────

def test_negotiate_accept_at_or_above_loadboard_rate(client):
    """Offer equal to loadboard_rate should be accepted immediately."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()

    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer": LOADBOARD_RATE,
            "round_number": 1,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "accept"
    assert "final_price" in data
    # final_price is rounded to nearest $25 for display; allow up to $25 tolerance
    assert abs(data["final_price"] - LOADBOARD_RATE) <= 25
    assert "final_price_per_mile" in data
    assert "message" in data


# ── Test 2: Accept immediately when offer < loadboard_rate ───────────────────

def test_negotiate_accept_below_loadboard_rate(client):
    """Offer below loadboard_rate should be accepted immediately (carrier takes less than market)."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()
    offer = round(LOADBOARD_RATE * 0.88, 2)  # ~952.29 — below loadboard_rate

    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer": offer,
            "round_number": 1,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "accept"
    assert "final_price" in data
    assert "final_price_per_mile" in data
    assert "message" in data


# ── Test 3: Counter on round 1 when offer is above loadboard but below ceiling ─

def test_negotiate_counter_round1_above_loadboard(client):
    """Round 1 offer above loadboard_rate but below max_rate → counter at loadboard_rate."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()
    offer = round(LOADBOARD_RATE * 1.10, 2)  # ~1190.37 — above loadboard, below max_rate (1244.47)

    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer": offer,
            "round_number": 1,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "counter"
    assert "counter_offer" in data
    # counter is loadboard_rate rounded to nearest $25 = 1075
    loadboard_rounded = round(LOADBOARD_RATE / 25) * 25
    assert abs(data["counter_offer"] - loadboard_rounded) < 0.01
    assert "counter_offer_per_mile" in data
    assert "message" in data


# ── Test 4: Counter at midpoint on round 2 ──────────────────────────────────

def test_negotiate_counter_round2_above_loadboard(client):
    """Round 2 offer above loadboard_rate but below max_rate → counter at midpoint."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()
    offer = round(LOADBOARD_RATE * 1.10, 2)  # ~1190.37

    loadboard_rounded = round(LOADBOARD_RATE / 25) * 25
    raw_midpoint = (loadboard_rounded + offer) / 2
    expected_midpoint = round(raw_midpoint / 25) * 25

    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer": offer,
            "round_number": 2,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "counter"
    assert abs(data["counter_offer"] - expected_midpoint) < 0.01


# ── Test 5: Accept on round 3 when offer is above loadboard but below ceiling ─

def test_negotiate_accept_round3_above_loadboard(client):
    """Round 3 offer above loadboard but below max_rate → accept at carrier's offer."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()
    offer = round(LOADBOARD_RATE * 1.10, 2)  # ~1190.37

    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer": offer,
            "round_number": 3,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "accept"
    assert abs(data["final_price"] - offer) <= 25  # rounded to nearest $25


# ── Test 6: Reject when offer > max_rate ────────────────────────────────────

def test_negotiate_reject_above_max_rate(client):
    """Offer above max_rate should be rejected regardless of round."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()
    offer = round(LOADBOARD_RATE * 1.20, 2)  # ~1298.58 — above max_rate (1244.47)

    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer": offer,
            "round_number": 1,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "reject"
    assert "message" in data
    # Ensure no rate info is leaked
    assert "min_rate" not in str(data)
    assert "max_rate" not in str(data)


# ── Test 7: Per-mile offer conversion ───────────────────────────────────────

def test_negotiate_per_mile_offer(client):
    """Sending carrier_offer_per_mile should compute total = per_mile × miles."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()

    # 410 miles × 2.60/mi = 1066.00 → below loadboard_rate (1075.0) → accept immediately
    per_mile_offer = 2.60

    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer_per_mile": per_mile_offer,
            "round_number": 1,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    # 410 * 2.60 = 1066 < 1075.0, so should accept
    # final_price is rounded to nearest $25 for display; allow up to $25 tolerance
    assert data["decision"] == "accept"
    assert abs(data["final_price"] - round(per_mile_offer * 410, 2)) <= 25


# ── Test 8: Missing both carrier_offer fields → 422 ─────────────────────────

def test_negotiate_missing_carrier_offer(client):
    """Sending neither carrier_offer nor carrier_offer_per_mile should return 422."""
    load_uuid = get_load_uuid()

    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": str(uuid.uuid4()),
            "load_id": load_uuid,
            "round_number": 1,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 422


# ── Test 9: Get negotiation history ─────────────────────────────────────────

def test_negotiate_get_history(client):
    """After posting negotiations, GET returns the rounds for that call."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()

    # Post two rounds with offer above loadboard (triggers counter both rounds)
    offer = round(LOADBOARD_RATE * 1.10, 2)
    for rnd in [1, 2]:
        r = client.post(
            "/api/agent/negotiations/evaluate",
            json={
                "call_id": call_id,
                "load_id": load_uuid,
                "carrier_offer": offer,
                "round_number": rnd,
            },
            headers=AGENT_HEADERS,
        )
        assert r.status_code == 200

    # Retrieve history
    r = client.get(f"/api/agent/negotiations/{call_id}", headers=AGENT_HEADERS)
    assert r.status_code == 200
    rounds = r.json()
    assert isinstance(rounds, list)
    assert len(rounds) == 2
    assert rounds[0]["round_number"] == 1
    assert rounds[1]["round_number"] == 2
    # Sensitive fields must not appear
    assert "min_rate" not in str(rounds)
    assert "max_rate" not in str(rounds)


# ── Test 10: No auth → 401 ───────────────────────────────────────────────────

def test_negotiate_no_auth(client):
    """Missing X-Agent-Key should return 401."""
    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": str(uuid.uuid4()),
            "load_id": str(uuid.uuid4()),
            "carrier_offer": 1000.00,
            "round_number": 1,
        },
    )
    assert r.status_code == 401
