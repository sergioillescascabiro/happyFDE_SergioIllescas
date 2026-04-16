"""End-to-end integration test: full agent call flow.

Simulates a complete inbound carrier call:
  1. Agent registers call with MC number.
  2. Carrier verified via FMCSA (mock mode).
  3. Load searched and matched.
  4. Transcript entries appended live.
  5. Negotiation rounds until accepted.
  6. Call classified as booked.
  7. Transfer simulated.
  8. Data persistence verified via dashboard endpoints.
  9. max_rate / min_rate must NOT appear in any response.

Negotiation model (stateful, profit-maximisation):
  - offer ≤ loadboard                     → accept immediately
  - offer ≤ previous counter (stateful)   → accept
  - Round 1: counter at loadboard
  - Round 2: counter at loadboard + 50% of (max − loadboard)
  - Round 3: accept if ≤ max, else counter at max (ultimatum, is_final=True)
  - Round 4+: accept if ≤ max, else reject

Run with: uv run pytest tests/test_e2e_agent_flow.py -v
"""
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models.load import Load, LoadStatus
from app.models.call import Call
from app.services.negotiation import _smart_round

AGENT_HEADERS = {"X-Agent-Key": "hr-agent-key-change-in-production"}
DASH_HEADERS = {"X-Dashboard-Token": "hr-dashboard-token-change-in-production"}

# Use MC 56789 (MARKS DISPATCH WESLEY MARKS) — authorized, in seed data
TEST_MC = "56789"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _assert_no_rate_leak(data):
    """Recursively assert that max_rate and min_rate do not appear in the data."""
    serialized = json.dumps(data)
    assert "max_rate" not in serialized, f"max_rate leaked: {serialized[:300]}"
    assert "min_rate" not in serialized, f"min_rate leaked: {serialized[:300]}"


def _get_available_load(client) -> dict:
    """Fetch any available load (any equipment type) for use in this test."""
    r = client.get(
        "/api/agent/loads/search",
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200, (
        f"Load search failed: {r.text}\n"
        "No available loads found — reseed with: cd backend && uv run python -m app.seed"
    )
    load = r.json()
    assert load.get("id"), "No available loads found — reseed the DB"
    return load


def _reset_load_to_available(load_uuid: str):
    """Restore a load's status to 'available' after a test that covered it."""
    db = SessionLocal()
    try:
        load = db.query(Load).filter(Load.id == load_uuid).first()
        if load and load.status != LoadStatus.available:
            load.status = LoadStatus.available
            load.booked_rate = None
            load.is_ai_booked = False
            db.commit()
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# E2E Test — full flow
# ─────────────────────────────────────────────────────────────────────────────

def test_e2e_full_agent_call_flow(client, monkeypatch):
    """Full carrier call flow: register → verify → search → negotiate → classify → transfer."""
    monkeypatch.setattr(settings, "FMCSA_MOCK", True)

    # ── Step 1: Register call ────────────────────────────────────────────────
    r = client.post(
        "/api/agent/calls",
        json={"mc_number": TEST_MC, "direction": "inbound", "phone_number": "+1-404-555-0333"},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200, f"Create call failed: {r.text}"
    call_data = r.json()
    call_id = call_data["call_id"]
    assert call_data["mc_number"] == TEST_MC
    assert call_data["outcome"] == "in_progress"
    _assert_no_rate_leak(call_data)

    # ── Step 2: Verify carrier via FMCSA ────────────────────────────────────
    r = client.post(
        "/api/agent/carriers/verify",
        json={"mc_number": TEST_MC},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200, f"Carrier verify failed: {r.text}"
    carrier_data = r.json()
    assert carrier_data["mc_number"] == TEST_MC
    assert isinstance(carrier_data["is_authorized"], bool)
    _assert_no_rate_leak(carrier_data)

    # ── Step 3: Search for an available load ────────────────────────────────
    chosen_load = _get_available_load(client)
    _assert_no_rate_leak(chosen_load)
    assert "max_rate" not in chosen_load
    assert "min_rate" not in chosen_load

    load_uuid = chosen_load["id"]
    loadboard_rate = chosen_load["loadboard_rate"]

    # ── Step 4: Link load to call ────────────────────────────────────────────
    r = client.patch(
        f"/api/agent/calls/{call_id}",
        json={"load_id": load_uuid},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    _assert_no_rate_leak(r.json())

    # ── Step 5: Append transcript entries ────────────────────────────────────
    entries = [
        {"role": "assistant", "message": "Thank you for calling Acme Logistics. May I have your MC number?"},
        {"role": "caller", "message": f"Sure, MC {TEST_MC}."},
        {"role": "assistant", "message": "Verified. What load are you calling about?"},
        {"role": "caller", "message": "I'm looking at a load."},
    ]
    for i, entry in enumerate(entries):
        r = client.post(
            f"/api/agent/calls/{call_id}/transcript",
            json=entry,
            headers=AGENT_HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["entry_count"] == i + 1

    # ── Step 6: Read internal rates from DB (never exposed via API) ──────────
    db = SessionLocal()
    try:
        _load = db.query(Load).filter(Load.id == load_uuid).first()
        max_rate_raw = _load.max_rate
        loadboard_rate_raw = _load.loadboard_rate
    finally:
        db.close()

    # Use engine's own rounding so carrier_offer_r1 is above loadboard but at max
    loadboard_rounded = _smart_round(loadboard_rate_raw)
    max_rate_rounded = _smart_round(max_rate_raw)

    # Offer at max_rate: above loadboard → triggers negotiation, not reject
    carrier_offer_r1 = max_rate_rounded
    if carrier_offer_r1 <= loadboard_rounded:
        carrier_offer_r1 = loadboard_rounded + 10  # failsafe for zero-range loads

    # ── Step 7: Negotiate ────────────────────────────────────────────────────
    # The backend is now stateful — derives round_number from DB.
    # We just POST each carrier response in sequence.

    def negotiate(offer):
        return client.post(
            "/api/agent/negotiations/evaluate",
            json={"call_id": call_id, "load_id": load_uuid, "carrier_offer": offer},
            headers=AGENT_HEADERS,
        )

    neg1 = negotiate(carrier_offer_r1)
    assert neg1.status_code == 200, f"Negotiation R1 failed: {neg1.text}"
    d1 = neg1.json()
    assert d1["decision"] == "counter", f"Expected counter on R1, got: {d1}"
    assert "counter_offer" in d1
    assert "tone" in d1
    assert d1["is_final"] is False
    _assert_no_rate_leak(d1)

    neg2 = negotiate(carrier_offer_r1)
    assert neg2.status_code == 200
    d2 = neg2.json()
    # R2: counter at midpoint, OR accept if counter ≥ carrier's offer (zero-range edge case)
    assert d2["decision"] in ("counter", "accept"), f"Unexpected R2 decision: {d2}"
    _assert_no_rate_leak(d2)

    if d2["decision"] == "accept":
        # Edge case: zero/tiny range, engine accepted early — still valid
        assert "final_price" in d2
        final_decision = d2
        expected_rounds = 2
    else:
        neg3 = negotiate(carrier_offer_r1)
        assert neg3.status_code == 200
        d3 = neg3.json()
        assert d3["decision"] in ("accept", "counter"), f"Unexpected R3 decision: {d3}"
        _assert_no_rate_leak(d3)

        if d3["decision"] == "counter":
            # Ultimatum path: carrier accepts the ceiling in R4
            neg4 = negotiate(d3["counter_offer"])
            assert neg4.status_code == 200
            d4 = neg4.json()
            assert d4["decision"] == "accept", f"Expected accept on R4 with ceiling offer, got: {d4}"
            final_decision = d4
            expected_rounds = 4
        else:
            final_decision = d3
            expected_rounds = 3

    assert "final_price" in final_decision
    assert "final_price_per_mile" in final_decision
    _assert_no_rate_leak(final_decision)

    # ── Step 8: Verify negotiation history ──────────────────────────────────
    r = client.get(f"/api/agent/negotiations/{call_id}", headers=AGENT_HEADERS)
    assert r.status_code == 200
    history = r.json()
    assert len(history) == expected_rounds
    for i, rnd in enumerate(history):
        assert rnd["round_number"] == i + 1
    _assert_no_rate_leak(history)

    # ── Step 9: Classify call as booked ─────────────────────────────────────
    r = client.post(
        f"/api/agent/calls/{call_id}/classify",
        json={
            "outcome": "booked",
            "sentiment": "positive",
            "transcript_summary": f"Carrier {TEST_MC} booked load after negotiation.",
            "extracted_data": {"final_rate": final_decision["final_price"], "load_id": load_uuid},
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    classify_data = r.json()
    assert classify_data["outcome"] == "booked"
    _assert_no_rate_leak(classify_data)

    # ── Step 10: Transfer call ───────────────────────────────────────────────
    r = client.post(f"/api/agent/calls/{call_id}/transfer", headers=AGENT_HEADERS)
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    # ── Step 11: Verify data persisted via dashboard ─────────────────────────
    r = client.get(f"/api/calls/{call_id}", headers=DASH_HEADERS)
    assert r.status_code == 200
    dashboard_call = r.json()
    assert dashboard_call["id"] == call_id
    assert dashboard_call["outcome"] == "transferred"
    assert dashboard_call["transferred_to_rep"] is True
    assert len(dashboard_call.get("transcript_full") or []) == 4
    assert len(dashboard_call.get("negotiations") or []) == expected_rounds
    _assert_no_rate_leak(dashboard_call)

    # ── Step 12: Dashboard metrics ───────────────────────────────────────────
    r = client.get("/api/metrics/overview", headers=DASH_HEADERS)
    assert r.status_code == 200
    assert r.json()["total_calls"] >= 1
    _assert_no_rate_leak(r.json())

    # ── Step 13: Live calls window ───────────────────────────────────────────
    r = client.get("/api/calls/live", headers=DASH_HEADERS)
    assert r.status_code == 200
    live_ids = [c["id"] for c in r.json()]
    assert call_id in live_ids, "Newly created call should appear in live view (30-min window)"
    _assert_no_rate_leak(r.json())

    # ── Cleanup: restore load so subsequent test runs have available loads ────
    _reset_load_to_available(load_uuid)


def test_e2e_reject_above_ceiling(client):
    """Offer > max_rate × 1.30 is rejected immediately (exorbitant)."""
    r = client.post(
        "/api/agent/calls",
        json={"mc_number": "97531"},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    call_id = r.json()["call_id"]

    load = _get_available_load(client)
    load_uuid = load["id"]

    # 160% of loadboard always exceeds max_rate * 1.30 for any valid seed load
    very_high_offer = round(load["loadboard_rate"] * 1.60, 2)
    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={"call_id": call_id, "load_id": load_uuid, "carrier_offer": very_high_offer},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["decision"] == "reject"
    _assert_no_rate_leak(result)


def test_e2e_accept_at_loadboard_rate(client):
    """Offer at loadboard_rate is accepted immediately (best case for broker)."""
    r = client.post(
        "/api/agent/calls",
        json={"mc_number": "13579"},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    call_id = r.json()["call_id"]

    load = _get_available_load(client)
    load_uuid = load["id"]
    loadboard_rate = load["loadboard_rate"]

    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={"call_id": call_id, "load_id": load_uuid, "carrier_offer": loadboard_rate},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["decision"] == "accept"
    assert abs(result["final_price"] - loadboard_rate) <= 10  # smart-round tolerance
    _assert_no_rate_leak(result)


def test_e2e_no_rate_leak_anywhere(client):
    """Exhaustive check: max_rate and min_rate must never appear in any response."""
    r = client.post(
        "/api/agent/carriers/verify",
        json={"mc_number": "98765"},
        headers=AGENT_HEADERS,
    )
    _assert_no_rate_leak(r.json())

    r = client.get("/api/agent/loads/search", headers=AGENT_HEADERS)
    if r.status_code == 200:
        _assert_no_rate_leak(r.json())

    r = client.get("/api/loads", headers=DASH_HEADERS)
    _assert_no_rate_leak(r.json())

    r = client.get("/api/metrics/overview", headers=DASH_HEADERS)
    _assert_no_rate_leak(r.json())

    r = client.get("/api/calls/live", headers=DASH_HEADERS)
    _assert_no_rate_leak(r.json())
