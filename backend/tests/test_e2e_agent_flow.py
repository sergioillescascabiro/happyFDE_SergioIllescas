"""End-to-end integration test: full agent call flow.

Simulates a complete inbound carrier call:
  1. Agent registers call with MC number.
  2. Carrier verified via FMCSA (mock mode).
  3. Load searched and matched.
  4. Transcript entries appended live.
  5. 3 rounds of negotiation (offer above loadboard) → accepted on round 3.
  6. Call classified as booked.
  7. Transfer simulated.
  8. Data persistence verified via dashboard endpoints.
  9. max_rate / min_rate must NOT appear in any response.

Negotiation model (profit-maximization, two-tier ceiling):
  - offer <= loadboard_rate              → accept immediately
  - loadboard_rate < offer <= max*1.30   → counter (round 1: loadboard, round 2: midpoint, round 3: ultimatum)
  - offer > max_rate * 1.30              → reject (exorbitant)

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

AGENT_HEADERS = {"X-Agent-Key": "hr-agent-key-change-in-production"}
DASH_HEADERS = {"X-Dashboard-Token": "hr-dashboard-token-change-in-production"}

# Use MC 56789 (HappyTruckers INC) — authorized, in seed data
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
    """Fetch an available load the agent can use for this test."""
    r = client.get(
        "/api/agent/loads/search",
        params={"equipment_type": "Dry Van"},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200, f"Load search failed: {r.text}"
    load = r.json()
    assert isinstance(load, dict), "Expected a single load object"
    assert load.get("id"), "No available Dry Van loads found — did you seed the DB?"
    return load


# ─────────────────────────────────────────────────────────────────────────────
# E2E Test
# ─────────────────────────────────────────────────────────────────────────────

def test_e2e_full_agent_call_flow(client, monkeypatch):
    """Full carrier call flow: register → verify → search → negotiate → classify → transfer."""
    # Force FMCSA mock for this test
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
    assert "message" in carrier_data
    _assert_no_rate_leak(carrier_data)

    # ── Step 3: Search loads (returns single best match by closest pickup) ───
    r = client.get(
        "/api/agent/loads/search",
        params={"equipment_type": "Dry Van"},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200, f"Load search failed: {r.text}"
    chosen_load = r.json()
    assert isinstance(chosen_load, dict), "Expected a single load object"
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
        {"role": "caller", "message": "I'm looking at a dry van load."},
    ]
    for i, entry in enumerate(entries):
        r = client.post(
            f"/api/agent/calls/{call_id}/transcript",
            json=entry,
            headers=AGENT_HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["entry_count"] == i + 1

    # ── Step 6: Negotiate — round 1 (offer above loadboard, below ceiling) ─────
    # Fetch max_rate from DB (test-only: max_rate is never exposed via API).
    db = SessionLocal()
    try:
        _load = db.query(Load).filter(Load.id == load_uuid).first()
        max_rate_raw = _load.max_rate
        loadboard_rate_raw = _load.loadboard_rate
    finally:
        db.close()
    # Offer must be strictly above loadboard_raw but at or below max_rate_rounded.
    # The engine rounds max_rate to nearest $25, so we do the same to stay safe.
    max_rate_rounded = round(max_rate_raw / 25) * 25
    carrier_offer_r1 = max_rate_rounded  # exactly at the "accept on R3" threshold
    if carrier_offer_r1 <= loadboard_rate_raw:
        carrier_offer_r1 = loadboard_rate_raw + 1  # fallback for very tight spread

    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer": carrier_offer_r1,
            "round_number": 1,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200, f"Negotiation round 1 failed: {r.text}"
    neg1 = r.json()
    assert neg1["decision"] == "counter", f"Expected counter on round 1, got: {neg1}"
    assert "counter_offer" in neg1
    assert "counter_offer_per_mile" in neg1
    assert "message" in neg1
    _assert_no_rate_leak(neg1)

    # ── Step 7: Negotiate — round 2 ─────────────────────────────────────────
    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer": carrier_offer_r1,
            "round_number": 2,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    neg2 = r.json()
    assert neg2["decision"] == "counter", f"Expected counter on round 2, got: {neg2}"
    _assert_no_rate_leak(neg2)

    # ── Step 8: Negotiate — round 3 → accept or ultimatum counter ────────────
    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer": carrier_offer_r1,
            "round_number": 3,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    neg3 = r.json()
    assert neg3["decision"] in ("accept", "counter"), f"Unexpected decision on round 3: {neg3}"
    _assert_no_rate_leak(neg3)

    expected_rounds = 3
    if neg3["decision"] == "counter":
        # Ultimatum: carrier was above max — accept the counter_offer on round 4
        r = client.post(
            "/api/agent/negotiations/evaluate",
            json={
                "call_id": call_id,
                "load_id": load_uuid,
                "carrier_offer": neg3["counter_offer"],  # accept the ultimatum price
                "round_number": 4,
            },
            headers=AGENT_HEADERS,
        )
        assert r.status_code == 200
        neg4 = r.json()
        assert neg4["decision"] == "accept", f"Expected accept on round 4 with counter_offer, got: {neg4}"
        neg3 = neg4  # use for downstream assertions
        expected_rounds = 4

    assert "final_price" in neg3
    assert "final_price_per_mile" in neg3
    _assert_no_rate_leak(neg3)

    # ── Step 9: Verify negotiation history ──────────────────────────────────
    r = client.get(
        f"/api/agent/negotiations/{call_id}",
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    history = r.json()
    assert len(history) == expected_rounds
    assert history[0]["round_number"] == 1
    assert history[1]["round_number"] == 2
    assert history[2]["round_number"] == 3
    _assert_no_rate_leak(history)

    # ── Step 10: Classify call as booked ────────────────────────────────────
    r = client.post(
        f"/api/agent/calls/{call_id}/classify",
        json={
            "outcome": "booked",
            "sentiment": "positive",
            "transcript_summary": f"Carrier {TEST_MC} booked load after 3 rounds of negotiation.",
            "extracted_data": {"final_rate": neg3["final_price"], "load_id": load_uuid},
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    classify_data = r.json()
    assert classify_data["outcome"] == "booked"
    assert classify_data["duration_seconds"] >= 0
    _assert_no_rate_leak(classify_data)

    # ── Step 11: Transfer call ───────────────────────────────────────────────
    r = client.post(f"/api/agent/calls/{call_id}/transfer", headers=AGENT_HEADERS)
    assert r.status_code == 200
    transfer_data = r.json()
    assert transfer_data["status"] == "success"
    assert "Transfer was successful" in transfer_data["message"]

    # ── Step 12: Verify data persisted via dashboard ─────────────────────────
    # Get the call via dashboard endpoint
    r = client.get(f"/api/calls/{call_id}", headers=DASH_HEADERS)
    assert r.status_code == 200
    dashboard_call = r.json()
    assert dashboard_call["id"] == call_id
    assert dashboard_call["outcome"] == "transferred"  # transfer overwrites classify
    assert dashboard_call["transferred_to_rep"] is True
    # Transcript should have 4 entries from step 5
    assert len(dashboard_call.get("transcript_full") or []) == 4
    # Negotiations should be linked
    assert len(dashboard_call.get("negotiations") or []) == 3
    _assert_no_rate_leak(dashboard_call)

    # ── Step 13: Verify dashboard metrics include this call ──────────────────
    r = client.get("/api/metrics/overview", headers=DASH_HEADERS)
    assert r.status_code == 200
    metrics = r.json()
    assert metrics["total_calls"] >= 1
    _assert_no_rate_leak(metrics)

    # ── Step 14: Verify live calls endpoint ─────────────────────────────────
    # The call was just classified so it's no longer in_progress, but it was
    # created recently so it should appear in the 30-minute window.
    r = client.get("/api/calls/live", headers=DASH_HEADERS)
    assert r.status_code == 200
    live_calls = r.json()
    live_ids = [c["id"] for c in live_calls]
    assert call_id in live_ids, "Newly created call should appear in live view (30-min window)"
    _assert_no_rate_leak(live_calls)


def test_e2e_reject_above_ceiling(client):
    """Offer above exorbitant threshold (max_rate * 1.30) is rejected outright."""
    # Create a call
    r = client.post(
        "/api/agent/calls",
        json={"mc_number": "97531"},
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    call_id = r.json()["call_id"]

    # Find a load
    load = _get_available_load(client)
    load_uuid = load["id"]
    loadboard_rate = load["loadboard_rate"]

    # Offer above exorbitant threshold (160% of loadboard — exceeds max_rate*1.30)
    very_high_offer = round(loadboard_rate * 1.60, 2)
    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer": very_high_offer,
            "round_number": 1,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["decision"] == "reject"
    _assert_no_rate_leak(result)


def test_e2e_accept_at_loadboard_rate(client):
    """Offer at or above loadboard_rate is accepted immediately."""
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

    # Offer exactly at loadboard_rate
    r = client.post(
        "/api/agent/negotiations/evaluate",
        json={
            "call_id": call_id,
            "load_id": load_uuid,
            "carrier_offer": loadboard_rate,
            "round_number": 1,
        },
        headers=AGENT_HEADERS,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["decision"] == "accept"
    # final_price is rounded to nearest $25 for display; allow up to $25 tolerance
    assert abs(result["final_price"] - loadboard_rate) <= 25
    _assert_no_rate_leak(result)


def test_e2e_no_rate_leak_anywhere(client):
    """Exhaustive check: max_rate and min_rate must not appear in any agent API response."""
    # Carrier verify
    r = client.post(
        "/api/agent/carriers/verify",
        json={"mc_number": "98765"},
        headers=AGENT_HEADERS,
    )
    _assert_no_rate_leak(r.json())

    # Load search (single object now)
    r = client.get("/api/agent/loads/search", headers=AGENT_HEADERS)
    assert r.status_code == 200
    _assert_no_rate_leak(r.json())

    # Dashboard loads
    r = client.get("/api/loads", headers=DASH_HEADERS)
    _assert_no_rate_leak(r.json())

    # Dashboard metrics
    r = client.get("/api/metrics/overview", headers=DASH_HEADERS)
    _assert_no_rate_leak(r.json())

    # Live calls
    r = client.get("/api/calls/live", headers=DASH_HEADERS)
    _assert_no_rate_leak(r.json())
