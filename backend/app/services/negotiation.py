"""Negotiation engine for freight load price negotiation.

Decision logic (all rates are TOTALS, not per-mile):
- carrier_offer >= load.loadboard_rate  → ACCEPT immediately
- carrier_offer >= load.min_rate AND round_number == 1  → COUNTER at loadboard_rate
- carrier_offer >= load.min_rate AND round_number == 2  → COUNTER at midpoint(carrier_offer, loadboard_rate)
- carrier_offer >= load.min_rate AND round_number >= 3  → ACCEPT at carrier_offer
- carrier_offer < load.min_rate  → REJECT

NEVER reveal max_rate, min_rate, or floor/ceiling in the return value.
"""
from sqlalchemy.orm import Session

from app.models.load import Load


def evaluate_offer(load_id: str, carrier_offer: float, round_number: int, db: Session) -> dict:
    """Evaluate a carrier's price offer against a load.

    Args:
        load_id: UUID of the load (Load.id).
        carrier_offer: Total dollar offer from the carrier.
        round_number: Which negotiation round this is (1-based).
        db: Database session.

    Returns:
        dict with keys: decision (accept/counter/reject), and relevant price fields.
    """
    load = db.query(Load).filter(Load.id == load_id).first()
    if not load:
        raise ValueError(f"Load {load_id} not found")

    miles = load.miles if load.miles > 0 else 1.0
    loadboard_rate = load.loadboard_rate  # total target price
    min_rate = load.min_rate              # floor (never exposed in response)

    if carrier_offer >= loadboard_rate:
        # Accept immediately at their offer (don't give a discount)
        final_price = round(carrier_offer, 2)
        return {
            "decision": "accept",
            "final_price": final_price,
            "final_price_per_mile": round(final_price / miles, 4),
            "message": (
                f"Great news! We accept your offer of ${final_price:,.2f} "
                f"(${round(final_price / miles, 2):.2f}/mile). "
                "We'll get your paperwork started right away."
            ),
        }

    if carrier_offer >= min_rate:
        if round_number == 1:
            counter = round(loadboard_rate, 2)
            return {
                "decision": "counter",
                "counter_offer": counter,
                "counter_offer_per_mile": round(counter / miles, 4),
                "message": (
                    f"Thank you for the offer. Our best rate for this load is "
                    f"${counter:,.2f} (${round(counter / miles, 2):.2f}/mile). "
                    "Can you work with that?"
                ),
            }
        elif round_number == 2:
            midpoint = round((carrier_offer + loadboard_rate) / 2, 2)
            return {
                "decision": "counter",
                "counter_offer": midpoint,
                "counter_offer_per_mile": round(midpoint / miles, 4),
                "message": (
                    f"We appreciate your flexibility. Let's meet in the middle at "
                    f"${midpoint:,.2f} (${round(midpoint / miles, 2):.2f}/mile). "
                    "Does that work for you?"
                ),
            }
        else:
            # round_number >= 3: accept at their offer
            final_price = round(carrier_offer, 2)
            return {
                "decision": "accept",
                "final_price": final_price,
                "final_price_per_mile": round(final_price / miles, 4),
                "message": (
                    f"We'll accept your offer of ${final_price:,.2f} "
                    f"(${round(final_price / miles, 2):.2f}/mile). "
                    "Let's get this load moving!"
                ),
            }

    # carrier_offer < min_rate
    return {
        "decision": "reject",
        "message": (
            f"Unfortunately, we're unable to accept an offer of ${carrier_offer:,.2f} "
            "for this load. The rate is below our minimum threshold. "
            "We appreciate your call and hope to work together on future loads."
        ),
    }
