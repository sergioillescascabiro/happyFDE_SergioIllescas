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
    - Round 3: ACCEPT if under max, else COUNTER at max (ultimatum)
    - Round 4+: ACCEPT if under max, else REJECT (walk away)

Concessions are always based on OUR range (loadboard → max_rate), never the carrier's
inflated ask. This prevents the carrier from manipulating our counters by anchoring high.

Messages vary in tone based on how far above loadboard the carrier's offer is:
  - Slight  (< 10% above): friendly pushback
  - Moderate (10–25% above): firm refusal
  - Aggressive (> 25% above): surprised + firm

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
        dict with keys: decision (accept/counter/reject), warning (optional), and relevant price fields.
    """
    load = db.query(Load).filter(Load.id == load_id).first()
    if not load:
        raise ValueError(f"Load {load_id} not found")

    miles = load.miles if load.miles > 0 else 1.0
    loadboard_rate_raw = load.loadboard_rate   # raw for comparison
    max_rate_raw = load.max_rate               # raw for comparison (never exposed)
    min_rate_raw = load.min_rate               # scam detection threshold (never exposed)
    loadboard_rate = round(load.loadboard_rate / 25) * 25  # rounded for display only

    # ── SCAM DETECTION: offer suspiciously below min_rate ────────────────────
    if carrier_offer < min_rate_raw:
        final_price = round(carrier_offer / 25) * 25
        return {
            "decision": "accept",
            "final_price": float(final_price),
            "final_price_per_mile": round(final_price / miles, 2),
            "warning": "suspiciously_low_offer",
            "message": (
                f"Hmm, ${final_price:,.0f} is actually well below market for this lane. "
                "I can work with that price, but I do need to get my manager's sign-off "
                "on anything this far below our posted rate. "
                "Let me transfer you to finalize — hold on just a sec."
            ),
        }

    # ── ACCEPT: at or below loadboard_rate (great deal for us) ──────────────
    if carrier_offer <= loadboard_rate_raw:
        final_price = round(carrier_offer / 25) * 25
        return {
            "decision": "accept",
            "final_price": float(final_price),
            "final_price_per_mile": round(final_price / miles, 2),
            "message": (
                f"Sounds good! I can get that locked in right now for ${final_price:,.0f} "
                f"(${round(final_price / miles, 2):.2f}/mile). "
                "Let me get your paperwork started right away."
            ),
        }

    # ── REJECT: exorbitant offer (> 130% of max_rate) ───────────────────────
    exorbitant_rate = max_rate_raw * 1.30
    if carrier_offer > exorbitant_rate:
        return {
            "decision": "reject",
            "message": (
                "Whoa, that's way out of the park for this lane. "
                "I can't even get close to that. Thanks anyway, safe travels!"
            ),
        }

    # ── NEGOTIATE: loadboard < carrier_offer <= exorbitant ───────────────────
    max_rate_rounded = round(max_rate_raw / 25) * 25

    # Our negotiation range — concessions are based on THIS, not on carrier's ask
    negotiation_range = max_rate_rounded - loadboard_rate

    # How aggressive is the carrier's ask? (used to vary message tone)
    pct_above = (carrier_offer - loadboard_rate_raw) / loadboard_rate_raw if loadboard_rate_raw > 0 else 0

    if round_number == 1:
        # Round 1: Strong anchor — always counter at our posted rate (lowest)
        counter = float(loadboard_rate)
        if pct_above > 0.25:
            tone = (
                f"Whoa, ${carrier_offer:,.0f}? That's way too steep for this lane. "
                f"We're at ${counter:,.0f} (${round(counter / miles, 2):.2f}/mile) on this one."
            )
        elif pct_above > 0.10:
            tone = (
                f"I can't do ${carrier_offer:,.0f}. We are currently firm at "
                f"${counter:,.0f} (${round(counter / miles, 2):.2f}/mile) on this one. "
                "It's a great load, can you work with that?"
            )
        else:
            tone = (
                f"That's a little above what we've got posted. We're at "
                f"${counter:,.0f} (${round(counter / miles, 2):.2f}/mile). "
                "Can you come down to that?"
            )
        return {
            "decision": "counter",
            "counter_offer": counter,
            "counter_offer_per_mile": round(counter / miles, 2),
            "message": tone,
        }

    elif round_number == 2:
        # Round 2: Small concession — step up by 33% of OUR range (not carrier's ask)
        step = loadboard_rate + (negotiation_range * 0.33)
        counter = round(min(step, max_rate_rounded) / 25) * 25
        # Ensure we at least match loadboard (in case range is tiny and rounding goes down)
        counter = max(counter, loadboard_rate)
        return {
            "decision": "counter",
            "counter_offer": float(counter),
            "counter_offer_per_mile": round(counter / miles, 2),
            "message": (
                f"Look, my margin is pretty tight right now. I could maybe step up to "
                f"${counter:,.0f} (${round(counter / miles, 2):.2f}/mile) to help you out. "
                "Does that work?"
            ),
        }

    elif round_number == 3:
        # Round 3: Ultimatum — accept if under our ceiling, otherwise final counter at max
        if carrier_offer <= max_rate_rounded:
            final_price = round(carrier_offer / 25) * 25
            return {
                "decision": "accept",
                "final_price": float(final_price),
                "final_price_per_mile": round(final_price / miles, 2),
                "message": (
                    f"Alright man, you drive a hard bargain. We'll do ${final_price:,.0f} "
                    f"(${round(final_price / miles, 2):.2f}/mile). Let's get it moving."
                ),
            }
        else:
            # Carrier still above our ceiling — offer max_rate as the absolute last offer
            return {
                "decision": "counter",
                "counter_offer": float(max_rate_rounded),
                "counter_offer_per_mile": round(max_rate_rounded / miles, 2),
                "message": (
                    f"I literally cannot pay ${carrier_offer:,.0f}, that puts me in the red. "
                    f"My absolute max on this is ${max_rate_rounded:,.0f}... take it or leave it."
                ),
            }

    else:
        # Round 4+: Final decision — we already gave our ultimatum
        if carrier_offer <= max_rate_rounded:
            final_price = round(carrier_offer / 25) * 25
            return {
                "decision": "accept",
                "final_price": float(final_price),
                "final_price_per_mile": round(final_price / miles, 2),
                "message": (
                    f"Okay, let's do ${final_price:,.0f}. I'll send the rate con now."
                ),
            }
        else:
            return {
                "decision": "reject",
                "message": (
                    "Yeah we're still too far apart. I'm going to have to pass and keep taking calls. "
                    "Have a good one."
                ),
            }

