"""Negotiation engine — stateful, profit-maximising.

RATE SEMANTICS (broker pays carrier, wants to pay as little as possible):
  - loadboard_rate  : market rate posted publicly — broker's anchor / round-1 counter
  - max_rate        : absolute ceiling broker will pay (quoted_rate × 0.92)
  - min_rate        : scam-detection floor (loadboard × 0.88) — NEVER revealed

NEGOTIATION PROGRESSION (loadboard → max_rate over 3 rounds):
  Round 1 : counter at loadboard_rate  (anchor low)
  Round 2 : counter at loadboard + 50% of range  (midpoint concession)
  Round 3 : counter at max_rate  (ultimatum, is_final=True)
  Round 4+ : accept if ≤ max_rate, else reject

STATEFUL ACCEPT (checked before progression):
  - carrier_offer ≤ loadboard                          → accept (at/below market)
  - carrier_offer ≤ previous counter from this call    → accept (carrier took our offer)
  - computed counter ≥ carrier_offer ≤ max_rate        → accept (no point countering higher)

NEVER reveal max_rate, min_rate, or internal thresholds in the returned dict.
"""
from sqlalchemy.orm import Session

from app.models.load import Load
from app.models.negotiation import Negotiation


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


def evaluate_offer(
    call_id: str,
    load_id: str,
    carrier_offer: float,
    db: Session,
) -> dict:
    """Evaluate a carrier's price offer against a load.

    Stateful — looks up previous rounds in the DB to determine the current
    round number and the broker's last counter offer.

    Args:
        call_id       : UUID of the active call (used for DB lookup).
        load_id       : UUID of the load (Load.id).
        carrier_offer : Total dollar amount the carrier wants to be paid.
        db            : Database session.

    Returns dict with keys:
        decision                : accept | counter | reject
        tone                    : slight | moderate | aggressive  (counter/reject)
        is_final                : bool  (True on round-3 ultimatum)
        counter_offer           : float  (on counter)
        counter_offer_per_mile  : float  (on counter)
        final_price             : float  (on accept)
        final_price_per_mile    : float  (on accept)
        warning                 : "suspiciously_low_offer"  (internal, stripped before agent response)
    """
    load = db.query(Load).filter(Load.id == load_id).first()
    if not load:
        raise ValueError(f"Load {load_id} not found")

    miles = load.miles if load.miles > 0 else 1.0

    # Internal thresholds (never exposed)
    min_rate_raw = load.min_rate

    # Public anchors — smart-rounded for clean numbers
    loadboard = _smart_round(load.loadboard_rate)
    max_rate = _smart_round(load.max_rate)
    negotiation_range = max(0.0, max_rate - loadboard)

    # ── Stateful: look up previous rounds for this call ───────────────────────
    prev_rounds = (
        db.query(Negotiation)
        .filter(Negotiation.call_id == call_id, Negotiation.load_id == load_id)
        .order_by(Negotiation.round_number.asc())
        .all()
    )
    round_number = len(prev_rounds) + 1
    prev_counter = prev_rounds[-1].counter_offer if prev_rounds else None

    # ── Tone helper ───────────────────────────────────────────────────────────
    pct_above = (
        (carrier_offer - load.loadboard_rate) / load.loadboard_rate
        if load.loadboard_rate > 0 else 0
    )
    tone = _tone(pct_above)

    # ── SCAM DETECTION ────────────────────────────────────────────────────────
    if carrier_offer < min_rate_raw:
        final_price = _smart_round(carrier_offer)
        return {
            "decision": "accept",
            "final_price": final_price,
            "final_price_per_mile": round(final_price / miles, 2),
            "warning": "suspiciously_low_offer",
            "_round_number": round_number,
        }

    # ── ACCEPT: at/below loadboard, OR carrier accepted our previous counter ──
    # Use raw loadboard_rate for threshold (rounding is only for counter display values)
    if carrier_offer <= load.loadboard_rate or (prev_counter is not None and carrier_offer <= prev_counter):
        final_price = _smart_round(carrier_offer)
        return {
            "decision": "accept",
            "final_price": final_price,
            "final_price_per_mile": round(final_price / miles, 2),
            "_round_number": round_number,
        }

    # ── REJECT: exorbitant (> 130% of max_rate) ───────────────────────────────
    if carrier_offer > max_rate * 1.30:
        return {
            "decision": "reject",
            "tone": tone,
            "_round_number": round_number,
        }

    # ── NEGOTIATE: loadboard < carrier_offer ≤ exorbitant ────────────────────
    if round_number == 1:
        # Anchor at loadboard
        counter = loadboard
        is_final = False

    elif round_number == 2:
        # Move to midpoint between loadboard and max_rate
        mid = _smart_round(loadboard + negotiation_range * 0.50)
        counter = max(mid, loadboard)
        is_final = False

    elif round_number == 3:
        # Ultimatum at max_rate ceiling
        if carrier_offer <= max_rate:
            final_price = _smart_round(carrier_offer)
            return {
                "decision": "accept",
                "final_price": final_price,
                "final_price_per_mile": round(final_price / miles, 2),
                "_round_number": round_number,
            }
        counter = max_rate
        is_final = True

    else:
        # Round 4+: walk away if still over ceiling
        if carrier_offer <= max_rate:
            final_price = _smart_round(carrier_offer)
            return {
                "decision": "accept",
                "final_price": final_price,
                "final_price_per_mile": round(final_price / miles, 2),
                "_round_number": round_number,
            }
        return {
            "decision": "reject",
            "tone": tone,
            "_round_number": round_number,
        }

    # If our computed counter ≥ carrier's ask and offer is within ceiling → accept
    # (avoids countering higher than what the carrier already offered)
    if carrier_offer <= max_rate and counter >= carrier_offer:
        final_price = _smart_round(carrier_offer)
        return {
            "decision": "accept",
            "final_price": final_price,
            "final_price_per_mile": round(final_price / miles, 2),
            "_round_number": round_number,
        }

    return {
        "decision": "counter",
        "counter_offer": counter,
        "counter_offer_per_mile": round(counter / miles, 2),
        "tone": tone,
        "is_final": is_final,
        "_round_number": round_number,
    }
