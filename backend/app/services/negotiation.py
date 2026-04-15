"""Negotiation engine for freight load price negotiation.

Decision logic (broker maximizes margin — pays carrier as little as possible):

SCAM DETECTION:
- carrier_offer < min_rate  → ACCEPT but flag as 'suspiciously_low_offer' + tell agent to transfer to manager

NORMAL FLOW:
- carrier_offer <= loadboard_rate            → ACCEPT immediately (best case for broker)
- carrier_offer > max_rate * 1.30            → REJECT (exorbitant — too far apart to negotiate)
- loadboard_rate < carrier_offer <= max*1.30:
    - Round 1: COUNTER at loadboard_rate (anchor low)
    - Round 2: COUNTER at loadboard + 33% of OUR range (small concession)
    - Round 3: ACCEPT if under max, else COUNTER at max (ultimatum — is_final=True)
    - Round 4+: ACCEPT if under max, else REJECT (walk away)

Concessions are always based on OUR range (loadboard → max_rate), never the carrier's
inflated ask. This prevents the carrier from manipulating our counters by anchoring high.

Tone varies based on how far above loadboard the carrier's offer is:
  - slight    (< 10% above): friendly pushback
  - moderate  (10–25% above): firm refusal
  - aggressive (> 25% above): surprised + firm

NEVER reveal max_rate, min_rate, or floor/ceiling in the return value.
"""
from sqlalchemy.orm import Session

from app.models.load import Load


def _smart_round(value: float) -> float:
    """Round to nearest $5 if under $1,000, else nearest $10."""
    step = 5 if value < 1_000 else 10
    return float(round(value / step) * step)


def _tone(pct_above: float) -> str:
    if pct_above > 0.25:
        return "aggressive"
    elif pct_above > 0.10:
        return "moderate"
    return "slight"


def evaluate_offer(load_id: str, carrier_offer: float, round_number: int, db: Session) -> dict:
    """Evaluate a carrier's price offer against a load.

    Args:
        load_id: UUID of the load (Load.id).
        carrier_offer: Total dollar amount the carrier wants to be paid.
        round_number: Which negotiation round this is (1-based).
        db: Database session.

    Returns:
        dict with keys:
          - decision: accept | counter | reject
          - tone: slight | moderate | aggressive  (on counter/reject)
          - is_final: bool  (True when this is the last possible counter)
          - counter_offer / counter_offer_per_mile  (on counter)
          - final_price / final_price_per_mile  (on accept)
          - warning: suspiciously_low_offer  (optional, on accept)
    """
    load = db.query(Load).filter(Load.id == load_id).first()
    if not load:
        raise ValueError(f"Load {load_id} not found")

    miles = load.miles if load.miles > 0 else 1.0
    loadboard_rate_raw = load.loadboard_rate
    max_rate_raw = load.max_rate
    min_rate_raw = load.min_rate
    loadboard_rate = _smart_round(loadboard_rate_raw)
    max_rate_rounded = _smart_round(max_rate_raw)

    # ── SCAM DETECTION ───────────────────────────────────────────────────────
    if carrier_offer < min_rate_raw:
        final_price = _smart_round(carrier_offer)
        return {
            "decision": "accept",
            "final_price": final_price,
            "final_price_per_mile": round(final_price / miles, 2),
            "warning": "suspiciously_low_offer",
        }

    # ── ACCEPT: at or below loadboard_rate ───────────────────────────────────
    if carrier_offer <= loadboard_rate_raw:
        final_price = _smart_round(carrier_offer)
        return {
            "decision": "accept",
            "final_price": final_price,
            "final_price_per_mile": round(final_price / miles, 2),
        }

    # ── REJECT: exorbitant offer (> 130% of max_rate) ────────────────────────
    if carrier_offer > max_rate_raw * 1.30:
        pct_above = (carrier_offer - loadboard_rate_raw) / loadboard_rate_raw if loadboard_rate_raw > 0 else 0
        return {
            "decision": "reject",
            "tone": _tone(pct_above),
        }

    # ── NEGOTIATE: loadboard < carrier_offer <= exorbitant ───────────────────
    negotiation_range = max_rate_rounded - loadboard_rate
    pct_above = (carrier_offer - loadboard_rate_raw) / loadboard_rate_raw if loadboard_rate_raw > 0 else 0
    tone = _tone(pct_above)

    if round_number == 1:
        # Round 1: anchor at loadboard_rate
        counter = loadboard_rate
        return {
            "decision": "counter",
            "counter_offer": counter,
            "counter_offer_per_mile": round(counter / miles, 2),
            "tone": tone,
            "is_final": False,
        }

    elif round_number == 2:
        # Round 2: small concession — 33% of OUR range
        step = loadboard_rate + (negotiation_range * 0.33)
        counter = _smart_round(min(step, max_rate_rounded))
        counter = max(counter, loadboard_rate)
        return {
            "decision": "counter",
            "counter_offer": counter,
            "counter_offer_per_mile": round(counter / miles, 2),
            "tone": tone,
            "is_final": False,
        }

    elif round_number == 3:
        # Round 3: ultimatum
        if carrier_offer <= max_rate_rounded:
            final_price = _smart_round(carrier_offer)
            return {
                "decision": "accept",
                "final_price": final_price,
                "final_price_per_mile": round(final_price / miles, 2),
            }
        else:
            # Final counter at our ceiling
            return {
                "decision": "counter",
                "counter_offer": max_rate_rounded,
                "counter_offer_per_mile": round(max_rate_rounded / miles, 2),
                "tone": tone,
                "is_final": True,
            }

    else:
        # Round 4+: we already gave our ultimatum
        if carrier_offer <= max_rate_rounded:
            final_price = _smart_round(carrier_offer)
            return {
                "decision": "accept",
                "final_price": final_price,
                "final_price_per_mile": round(final_price / miles, 2),
            }
        else:
            return {
                "decision": "reject",
                "tone": tone,
            }
