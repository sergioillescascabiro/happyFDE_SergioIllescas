"""Tests for agent negotiation engine endpoint (Stage 3).

Seed data for load "202883":
  - equipment: Flatbed, miles: 410
  - loadboard_rate: 1075.0   (target price — total)
  - max_rate:       1100.0   (ceiling = quoted_rate * 0.85, never exposed)

Decision logic (broker profit-maximization with two-tier ceiling):
  - offer <= loadboard_rate                         → accept immediately
  - loadboard_rate < offer <= exorbitant_rate, R1    → counter at loadboard_rate
  - loadboard_rate < offer <= exorbitant_rate, R2    → counter at midpoint, capped at max_rate
  - loadboard_rate < offer <= max_rate, R3           → accept at carrier_offer
  - max_rate < offer <= exorbitant_rate, R3           → counter at max_rate (ultimatum)
  - R4+: accept if under max_rate, else reject
  - offer > exorbitant_rate (max_rate * 1.30)         → reject immediately
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
# max_rate is now quoted_rate * 0.85 — actual value from DB is 1100.0
# Use a narrow offer above loadboard that stays below max_rate
COUNTER_OFFER = 1090.0   # above loadboard (1075), below max_rate (1100)
REJECT_OFFER = 1450.0    # above exorbitant threshold (1100 * 1.30 = 1430) — always reject

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
    # final_price is smart-rounded: nearest $10 for values >= $1000
    assert abs(data["final_price"] - LOADBOARD_RATE) <= 10
    assert "final_price_per_mile" in data
    assert "message" not in data


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
    assert "message" not in data


# ── Test 3: Counter on round 1 when offer is above loadboard but below ceiling ─

def test_negotiate_counter_round1_above_loadboard(client):
    """Round 1 offer above loadboard_rate but below max_rate → counter at loadboard_rate."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()
    # COUNTER_OFFER (1090) is above loadboard (1075) but below max_rate (1100)
    offer = COUNTER_OFFER

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
    # counter is loadboard_rate smart-rounded: nearest $10 for values >= $1000
    step = 5 if LOADBOARD_RATE < 1000 else 10
    loadboard_rounded = round(LOADBOARD_RATE / step) * step
    assert abs(data["counter_offer"] - loadboard_rounded) < 0.01
    assert "counter_offer_per_mile" in data
    assert "tone" in data
    assert "is_final" in data
    assert data["is_final"] is False
    assert "message" not in data


# ── Test 4: Counter on round 2 using 33% of OUR range ───────────────────────

def test_negotiate_counter_round2_above_loadboard(client):
    """Round 2 offer above loadboard_rate → counter at loadboard + 33% of OUR range (not carrier's ask)."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()
    offer = COUNTER_OFFER  # 1090 — between loadboard (1075) and max_rate (1100)

    # New logic: counter = loadboard + 33% * (max - loadboard), capped at max
    # loadboard_rounded = 1075, max_rounded = 1100, range = 25
    # step = 1075 + 25*0.33 = 1083.25 → round to $1,075 (nearest $25)
    # But max(counter, loadboard) ensures at least $1,075
    loadboard_rounded = round(LOADBOARD_RATE / 25) * 25

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
    # Counter must be at least loadboard_rate and at most max_rate
    assert data["counter_offer"] >= loadboard_rounded
    assert data["counter_offer"] <= 1100  # max_rate from seed


# ── Test 5: Accept on round 3 when offer is above loadboard but below ceiling ─

def test_negotiate_accept_round3_above_loadboard(client):
    """Round 3 offer above loadboard but below max_rate → accept at carrier's offer."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()
    offer = COUNTER_OFFER  # 1090 — between loadboard (1075) and max_rate (1100)

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
    assert abs(data["final_price"] - offer) <= 10  # smart-rounded: nearest $10 for >= $1000


# ── Test 6: Reject when offer > exorbitant threshold (max_rate * 1.30) ───────

def test_negotiate_reject_above_exorbitant_rate(client):
    """Offer above exorbitant threshold (max_rate * 1.30) should be rejected immediately."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()
    offer = REJECT_OFFER  # 1450 — above exorbitant threshold (1100 * 1.30 = 1430)

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
    assert "tone" in data
    assert "message" not in data
    # Ensure no rate info is leaked
    assert "min_rate" not in str(data)
    assert "max_rate" not in str(data)


# ── Test 6b: Counter at max_rate when offer is between max_rate and exorbitant ─

def test_negotiate_counter_between_max_and_exorbitant(client):
    """Offer above max_rate but below exorbitant threshold on round 1 should counter."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()
    # 1200 is above max_rate (1100) but below exorbitant (1430)
    offer = 1200.0

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
    assert "tone" in data
    assert "message" not in data
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
    # final_price smart-rounded: 1066 >= 1000 → nearest $10 → 1070; tolerance $10
    assert data["decision"] == "accept"
    assert abs(data["final_price"] - round(per_mile_offer * 410, 2)) <= 10


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

    # Post two rounds with offer above loadboard but below max_rate (triggers counter both rounds)
    offer = COUNTER_OFFER  # 1090 — between loadboard (1075) and max_rate (1100)
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


# ── Test 11: Scam detection — offer below min_rate ──────────────────────────

def test_negotiate_scam_detection_below_min_rate(client):
    """Offer below min_rate should accept. Warning is NOT sent to agent but IS saved in DB."""
    load_uuid = get_load_uuid()
    call_id = create_test_call()
    # min_rate for load 202883 = round(1075 * 0.85 / 25) * 25 = 914 (approx)
    # Offer way below that
    scam_offer = 700.0

    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer": scam_offer,
            "round_number": 1,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "accept"
    assert "final_price" in data
    assert "message" not in data
    # WARNING must NOT be in agent response (it's internal)
    assert "warning" not in data
    # Ensure no rate info is leaked
    assert "min_rate" not in str(data)
    assert "max_rate" not in str(data)

    # Verify the warning IS persisted in the database
    from app.models.negotiation import Negotiation
    db = SessionLocal()
    try:
        neg = (
            db.query(Negotiation)
            .filter(Negotiation.call_id == call_id)
            .order_by(Negotiation.round_number.desc())
            .first()
        )
        assert neg is not None
        assert neg.warning == "suspiciously_low_offer"
    finally:
        db.close()
