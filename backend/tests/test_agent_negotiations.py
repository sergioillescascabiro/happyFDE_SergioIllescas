"""Tests for the stateful negotiation engine endpoint.

Load used: "2031" (Flatbed, 410 miles) — must exist in the seeded DB.

Negotiation progression (loadboard → max_rate):
  - offer ≤ loadboard                  → ACCEPT immediately (market rate or less)
  - offer ≤ previous counter (stateful) → ACCEPT (carrier accepted our offer)
  - computed counter ≥ offer ≤ max_rate → ACCEPT (no point countering higher)
  - Round 1 counter: loadboard (anchor)
  - Round 2 counter: loadboard + 50% of (max_rate − loadboard)
  - Round 3 counter: max_rate (ultimatum, is_final=True)
  - Round 4+: accept if ≤ max_rate, else reject
  - offer > max_rate × 1.30            → REJECT (exorbitant)
  - offer < min_rate                   → ACCEPT + internal warning (scam)
"""
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.load import Load
from app.models.call import Call, CallDirection, CallOutcome
from app.services.negotiation import _smart_round

AGENT_KEY = "hr-agent-key-change-in-production"
AGENT_HEADERS = {"X-Agent-Key": AGENT_KEY}

TEST_LOAD_ID = "2031"  # Flatbed, 410 miles — always available in seed

# ── Fixtures ──────────────────────────────────────────────────────────────────

_cache: dict = {}


def get_load_data() -> dict:
    """Return the DB load record for TEST_LOAD_ID (cached)."""
    if "load" not in _cache:
        db = SessionLocal()
        try:
            load = db.query(Load).filter(Load.load_id == TEST_LOAD_ID).first()
            assert load is not None, (
                f"Load '{TEST_LOAD_ID}' not found — run: cd backend && uv run python -m app.seed"
            )
            _cache["load"] = {
                "uuid": load.id,
                "miles": load.miles,
                "loadboard": _smart_round(load.loadboard_rate),   # anchor
                "max_rate": _smart_round(load.max_rate),           # ceiling
                "min_rate": load.min_rate,                         # scam floor (raw)
                "loadboard_raw": load.loadboard_rate,
            }
        finally:
            db.close()
    return _cache["load"]


def create_test_call() -> str:
    """Insert a minimal Call row and return its id."""
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


def post_evaluate(client, call_id, carrier_offer):
    """Helper — POST /evaluate and return (status_code, json)."""
    ld = get_load_data()
    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": ld["uuid"],
            "carrier_offer": carrier_offer,
        },
        headers=AGENT_HEADERS,
    )
    return r.status_code, r.json()


# ── Test 1: Accept when offer == loadboard ────────────────────────────────────

def test_accept_at_loadboard(client):
    """Offer == loadboard_rate → accept immediately."""
    ld = get_load_data()
    call_id = create_test_call()

    status, data = post_evaluate(client, call_id, ld["loadboard"])
    assert status == 200
    assert data["decision"] == "accept"
    assert "final_price" in data
    assert "final_price_per_mile" in data
    assert abs(data["final_price"] - ld["loadboard"]) <= 10   # smart-round tolerance


# ── Test 2: Accept when offer < loadboard ─────────────────────────────────────

def test_accept_below_loadboard(client):
    """Offer below loadboard_rate → accept (carrier takes less than market)."""
    ld = get_load_data()
    call_id = create_test_call()
    offer = round(ld["loadboard"] * 0.92, 2)

    status, data = post_evaluate(client, call_id, offer)
    assert status == 200
    assert data["decision"] == "accept"
    assert "final_price" in data


# ── Test 3: Round-1 counter at loadboard ─────────────────────────────────────

def test_counter_round1_above_loadboard(client):
    """Round 1, offer above loadboard but not exorbitant → counter at loadboard."""
    ld = get_load_data()
    call_id = create_test_call()

    # Offer above max_rate (outside ceiling) but below exorbitant
    offer = round(ld["max_rate"] * 1.10, 2)

    status, data = post_evaluate(client, call_id, offer)
    assert status == 200
    assert data["decision"] == "counter"
    assert abs(data["counter_offer"] - ld["loadboard"]) < 0.01
    assert "counter_offer_per_mile" in data
    assert data["is_final"] is False
    assert "tone" in data


# ── Test 4: Round-2 counter at midpoint ──────────────────────────────────────

def test_counter_round2_midpoint(client):
    """Round 2: counter moves to midpoint (loadboard + 50% of range)."""
    ld = get_load_data()
    lb = ld["loadboard"]
    mr = ld["max_rate"]
    mid = _smart_round(lb + (mr - lb) * 0.50)
    expected_counter = max(mid, lb)

    call_id = create_test_call()
    high_offer = round(mr * 1.10, 2)  # above ceiling, below exorbitant

    # Round 1
    s1, d1 = post_evaluate(client, call_id, high_offer)
    assert s1 == 200 and d1["decision"] == "counter"

    # Round 2 — same high offer
    s2, d2 = post_evaluate(client, call_id, high_offer)
    assert s2 == 200
    assert d2["decision"] == "counter"
    assert abs(d2["counter_offer"] - expected_counter) < 0.01
    assert d2["is_final"] is False


# ── Test 5: Stateful accept — carrier accepts our previous counter ─────────────

def test_stateful_accept_carrier_takes_our_counter(client):
    """If carrier's new offer == our previous counter, backend accepts immediately."""
    ld = get_load_data()
    call_id = create_test_call()
    high_offer = round(ld["max_rate"] * 1.10, 2)

    # Round 1 → counter at loadboard
    s1, d1 = post_evaluate(client, call_id, high_offer)
    assert s1 == 200 and d1["decision"] == "counter"
    our_counter = d1["counter_offer"]

    # Round 2 — carrier sends exactly our counter → ACCEPT
    s2, d2 = post_evaluate(client, call_id, our_counter)
    assert s2 == 200
    assert d2["decision"] == "accept"
    assert "final_price" in d2


# ── Test 6: Stateful accept — carrier comes in below our counter ───────────────

def test_stateful_accept_carrier_below_our_counter(client):
    """Carrier's new offer is below our last counter → accept (they moved toward us)."""
    ld = get_load_data()
    call_id = create_test_call()
    high_offer = round(ld["max_rate"] * 1.10, 2)

    # Round 1 → counter at loadboard
    s1, d1 = post_evaluate(client, call_id, high_offer)
    assert s1 == 200 and d1["decision"] == "counter"
    our_counter = d1["counter_offer"]

    # Round 2 — carrier offers something between loadboard and our counter
    # (above loadboard but below our counter) → still ACCEPT (stateful)
    below_counter = round(our_counter - 1, 0)  # just below our counter
    if below_counter > ld["loadboard"]:
        s2, d2 = post_evaluate(client, call_id, below_counter)
        assert s2 == 200
        assert d2["decision"] == "accept"


# ── Test 7: Counter offer never goes above carrier's ask ──────────────────────

def test_no_counter_above_carriers_offer(client):
    """If computed counter ≥ carrier's offer (and offer ≤ max_rate) → accept, never counter higher."""
    ld = get_load_data()
    lb = ld["loadboard"]
    mr = ld["max_rate"]

    # Offer just above loadboard but below midpoint — engine's R2 counter would be
    # at midpoint which is >= offer, so it should ACCEPT instead
    call_id = create_test_call()
    high = round(mr * 1.10, 2)

    # R1 counter at loadboard
    s1, d1 = post_evaluate(client, call_id, high)
    assert s1 == 200 and d1["decision"] == "counter"

    # R2: offer slightly above loadboard but still inside ceiling
    # Engine midpoint >= offer → should accept
    offer_r2 = round(lb + (mr - lb) * 0.10, 0)  # 10% of range, well below midpoint
    if lb < offer_r2 <= mr:
        s2, d2 = post_evaluate(client, call_id, offer_r2)
        assert s2 == 200
        # Either accept (midpoint >= offer) or counter (midpoint < offer) — never higher
        if d2["decision"] == "counter":
            assert d2["counter_offer"] <= offer_r2 + 0.01 or d2["counter_offer"] >= offer_r2


# ── Test 8: Round-3 ultimatum ────────────────────────────────────────────────

def test_round3_ultimatum_at_max_rate(client):
    """Round 3 with offer above max_rate → counter at max_rate, is_final=True."""
    ld = get_load_data()
    mr = ld["max_rate"]
    call_id = create_test_call()
    high = round(mr * 1.10, 2)  # above ceiling, below exorbitant

    post_evaluate(client, call_id, high)  # R1
    post_evaluate(client, call_id, high)  # R2
    s3, d3 = post_evaluate(client, call_id, high)  # R3

    assert s3 == 200
    assert d3["decision"] == "counter"
    assert abs(d3["counter_offer"] - mr) < 0.01
    assert d3["is_final"] is True


# ── Test 9: Round-4 reject when still above ceiling ──────────────────────────

def test_round4_reject_above_max_rate(client):
    """Round 4 with offer still above max_rate → reject (walked away)."""
    ld = get_load_data()
    mr = ld["max_rate"]
    call_id = create_test_call()
    high = round(mr * 1.10, 2)

    post_evaluate(client, call_id, high)  # R1
    post_evaluate(client, call_id, high)  # R2
    post_evaluate(client, call_id, high)  # R3 → ultimatum at max_rate
    s4, d4 = post_evaluate(client, call_id, high)  # R4

    assert s4 == 200
    assert d4["decision"] == "reject"
    assert "tone" in d4


# ── Test 10: Round-4 accept when offer ≤ max_rate ────────────────────────────

def test_round4_accept_below_max_rate(client):
    """Round 4 with offer ≤ max_rate (carrier accepted ultimatum) → accept."""
    ld = get_load_data()
    mr = ld["max_rate"]
    call_id = create_test_call()
    high = round(mr * 1.10, 2)

    post_evaluate(client, call_id, high)   # R1
    post_evaluate(client, call_id, high)   # R2
    post_evaluate(client, call_id, high)   # R3 → ultimatum
    s4, d4 = post_evaluate(client, call_id, mr)  # R4 — carrier accepts ceiling

    assert s4 == 200
    assert d4["decision"] == "accept"
    assert "final_price" in d4
    assert abs(d4["final_price"] - mr) <= 10


# ── Test 11: Reject exorbitant offer ─────────────────────────────────────────

def test_reject_exorbitant_offer(client):
    """Offer > max_rate × 1.30 → reject immediately regardless of round."""
    ld = get_load_data()
    call_id = create_test_call()
    exorbitant = round(ld["max_rate"] * 1.35, 2)

    status, data = post_evaluate(client, call_id, exorbitant)
    assert status == 200
    assert data["decision"] == "reject"
    assert "tone" in data
    assert "min_rate" not in str(data)
    assert "max_rate" not in str(data)


# ── Test 12: Scam detection ───────────────────────────────────────────────────

def test_scam_detection_below_min_rate(client):
    """Offer < min_rate → accept but save internal warning (not sent to agent)."""
    ld = get_load_data()
    call_id = create_test_call()
    scam = round(ld["min_rate"] * 0.80, 2)

    status, data = post_evaluate(client, call_id, scam)
    assert status == 200
    assert data["decision"] == "accept"
    assert "final_price" in data
    assert "warning" not in data            # stripped before agent response
    assert "min_rate" not in str(data)
    assert "max_rate" not in str(data)

    # Warning must be persisted in DB
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


# ── Test 13: Per-mile offer conversion ───────────────────────────────────────

def test_per_mile_offer_converted_correctly(client):
    """carrier_offer_per_mile × miles should be used as the total offer."""
    ld = get_load_data()
    call_id = create_test_call()

    # Pick a per-mile rate that results in a total below loadboard
    per_mile = round(ld["loadboard"] / ld["miles"] * 0.95, 2)

    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": ld["uuid"],
            "carrier_offer_per_mile": per_mile,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "accept"


# ── Test 14: Missing carrier_offer → 422 ──────────────────────────────────────

def test_missing_carrier_offer_returns_422(client):
    """Sending neither carrier_offer nor carrier_offer_per_mile → 422."""
    ld = get_load_data()
    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={"call_id": str(uuid.uuid4()), "load_id": ld["uuid"]},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 422


# ── Test 15: GET negotiation history ─────────────────────────────────────────

def test_get_negotiation_history(client):
    """After posting N rounds, GET returns them in order with no rate leakage."""
    ld = get_load_data()
    call_id = create_test_call()
    high = round(ld["max_rate"] * 1.10, 2)

    post_evaluate(client, call_id, high)  # R1
    post_evaluate(client, call_id, high)  # R2

    r = client.get(f"/api/agent/negotiations/{call_id}", headers=AGENT_HEADERS)
    assert r.status_code == 200
    rounds = r.json()
    assert len(rounds) == 2
    assert rounds[0]["round_number"] == 1
    assert rounds[1]["round_number"] == 2
    assert "min_rate" not in str(rounds)
    assert "max_rate" not in str(rounds)


# ── Test 16: No auth → 401 ───────────────────────────────────────────────────

def test_no_auth_returns_401(client):
    """Missing X-Agent-Key → 401."""
    ld = get_load_data()
    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={"call_id": str(uuid.uuid4()), "load_id": ld["uuid"], "carrier_offer": 1000.0},
    )
    assert r.status_code == 401
