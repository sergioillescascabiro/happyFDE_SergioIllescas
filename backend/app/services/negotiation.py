"""Negotiation engine for freight load price negotiation.

Decision logic (broker maximizes margin — pays carrier as little as possible):
- carrier_offer <= loadboard_rate  → ACCEPT immediately (carrier takes market rate or less)
- carrier_offer > max_rate         → REJECT (too expensive, above ceiling)
- loadboard_rate < carrier_offer <= max_rate, round 1  → COUNTER at loadboard_rate
- loadboard_rate < carrier_offer <= max_rate, round 2  → COUNTER at midpoint(loadboard, offer)
- loadboard_rate < carrier_offer <= max_rate, round 3+ → ACCEPT at carrier_offer

NEVER reveal max_rate, min_rate, or floor/ceiling in the return value.
"""
from sqlalchemy.orm import Session

from app.models.load import Load


def evaluate_offer(load_id: str, carrier_offer: float, round_number: int, db: Session) -> dict:
    """Evaluate a carrier's price offer against a load.

    Args:
        load_id: UUID of the load (Load.id).
        carrier_offer: Total dollar amount the carrier wants to be paid.
        round_number: Which negotiation round this is (1-based).
        db: Database session.

    Returns:
        dict with keys: decision (accept/counter/reject), and relevant price fields.
    """
    load = db.query(Load).filter(Load.id == load_id).first()
    if not load:
        raise ValueError(f"Load {load_id} not found")

    miles = load.miles if load.miles > 0 else 1.0
    loadboard_rate_raw = load.loadboard_rate   # raw for comparison
    max_rate_raw = load.max_rate               # raw for comparison (never exposed)
    loadboard_rate = round(load.loadboard_rate / 25) * 25  # rounded for display only

    if carrier_offer <= loadboard_rate_raw:
        # Accept immediately — carrier wants at or below our posted rate (best case)
        final_price = round(carrier_offer / 25) * 25
        return {
            "decision": "accept",
            "final_price": float(final_price),
            "final_price_per_mile": round(final_price / miles, 2),
            "message": (
                f"Sounds good! We can do ${final_price:,.0f} "
                f"(${round(final_price / miles, 2):.2f}/mile). "
                "Let me get your paperwork started right away."
            ),
        }

    if carrier_offer > max_rate_raw:
        # Above ceiling — reject
        return {
            "decision": "reject",
            "message": (
                "Unfortunately we can't go that high on this load. "
                "We appreciate your call and hope to work together on future loads."
            ),
        }

    # loadboard_rate < carrier_offer <= max_rate — negotiate down
    if round_number == 1:
        counter = float(loadboard_rate)
        return {
            "decision": "counter",
            "counter_offer": counter,
            "counter_offer_per_mile": round(counter / miles, 2),
            "message": (
                f"I appreciate that, but our rate on this load is "
                f"${counter:,.0f} (${round(counter / miles, 2):.2f}/mile). "
                "Can you work with that?"
            ),
        }
    elif round_number == 2:
        midpoint = round(((loadboard_rate + carrier_offer) / 2) / 25) * 25
        return {
            "decision": "counter",
            "counter_offer": float(midpoint),
            "counter_offer_per_mile": round(midpoint / miles, 2),
            "message": (
                f"Let's meet in the middle — I can do "
                f"${midpoint:,.0f} (${round(midpoint / miles, 2):.2f}/mile). "
                "Does that work for you?"
            ),
        }
    else:
        # round_number >= 3: accept at carrier's offer
        final_price = round(carrier_offer / 25) * 25
        return {
            "decision": "accept",
            "final_price": float(final_price),
            "final_price_per_mile": round(final_price / miles, 2),
            "message": (
                f"Alright, we'll do ${final_price:,.0f} "
                f"(${round(final_price / miles, 2):.2f}/mile). "
                "Let's get this load moving!"
            ),
        }
