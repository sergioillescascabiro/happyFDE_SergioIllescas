from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from app.database import get_db
from app.middleware.auth import require_agent_key
from app.models.load import Load
from app.models.negotiation import Negotiation, NegotiationResponse as NegResponseEnum
from app.services.negotiation import evaluate_offer

router = APIRouter(prefix="/api/agent/negotiations", tags=["agent-negotiations"])


# ── Request / Response schemas ──────────────────────────────────────────────

class NegotiationEvaluateRequest(BaseModel):
    call_id: str
    load_id: str
    carrier_offer: Optional[float] = None
    carrier_offer_per_mile: Optional[float] = None
    # round_number is no longer used by the engine (derived from DB),
    # but accepted for backward-compatibility with existing workflow versions.
    round_number: Optional[int] = None

    @model_validator(mode="after")
    def check_at_least_one_offer(self):
        if self.carrier_offer is None and self.carrier_offer_per_mile is None:
            raise ValueError("Either carrier_offer or carrier_offer_per_mile must be provided")
        return self


class NegotiationRoundResponse(BaseModel):
    id: str
    call_id: str
    load_id: str
    round_number: int
    carrier_offer: float
    carrier_offer_per_mile: float
    system_response: str
    counter_offer: Optional[float] = None
    counter_offer_per_mile: Optional[float] = None
    final_price: Optional[float] = None
    tone: Optional[str] = None
    is_final: Optional[bool] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/evaluate")
def evaluate_negotiation(
    payload: NegotiationEvaluateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """Evaluate a carrier's price offer.

    The engine is stateful — it reads previous rounds from the DB using
    call_id, so the agent does NOT need to track or send round_number.
    Just forward every carrier response (counter or acceptance) here.
    """
    # Resolve load
    load = db.query(Load).filter(Load.id == payload.load_id).first()
    if not load:
        raise HTTPException(404, f"Load {payload.load_id} not found")

    # Resolve total carrier offer
    if payload.carrier_offer is not None:
        total_offer = payload.carrier_offer
    else:
        total_offer = payload.carrier_offer_per_mile * load.miles

    # Run negotiation engine (stateful)
    try:
        result = evaluate_offer(
            call_id=payload.call_id,
            load_id=payload.load_id,
            carrier_offer=total_offer,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    # Extract internal fields before persisting / responding
    decision = result["decision"]
    round_number = result.pop("_round_number")
    warning = result.pop("warning", None)

    # Persist negotiation round
    carrier_offer_per_mile = round(total_offer / load.miles, 4) if load.miles > 0 else 0.0

    response_enum = {
        "accept": NegResponseEnum.accept,
        "counter": NegResponseEnum.counter,
        "reject": NegResponseEnum.reject,
    }[decision]

    neg = Negotiation(
        id=str(uuid.uuid4()),
        call_id=payload.call_id,
        load_id=payload.load_id,
        round_number=round_number,
        carrier_offer=round(total_offer, 2),
        carrier_offer_per_mile=carrier_offer_per_mile,
        system_response=response_enum,
        counter_offer=result.get("counter_offer"),
        counter_offer_per_mile=result.get("counter_offer_per_mile"),
        final_price=result.get("final_price"),
        tone=result.get("tone"),
        is_final=result.get("is_final", False),
        warning=warning,
        created_at=datetime.now(timezone.utc),
    )
    db.add(neg)
    db.commit()

    return result


@router.get("/{call_id}", response_model=List[NegotiationRoundResponse])
def get_negotiation_history(
    call_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """Return all negotiation rounds for a given call, ordered by round."""
    rounds = (
        db.query(Negotiation)
        .filter(Negotiation.call_id == call_id)
        .order_by(Negotiation.round_number.asc())
        .all()
    )

    return [
        NegotiationRoundResponse(
            id=n.id,
            call_id=n.call_id,
            load_id=n.load_id,
            round_number=n.round_number,
            carrier_offer=n.carrier_offer,
            carrier_offer_per_mile=n.carrier_offer_per_mile,
            system_response=n.system_response.value if hasattr(n.system_response, "value") else n.system_response,
            counter_offer=n.counter_offer,
            counter_offer_per_mile=n.counter_offer_per_mile,
            final_price=n.final_price,
            tone=n.tone,
            is_final=n.is_final,
            notes=n.notes,
            created_at=n.created_at,
        )
        for n in rounds
    ]
