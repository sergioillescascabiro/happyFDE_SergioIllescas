from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone, timezone
import uuid

from app.database import get_db
from app.middleware.auth import require_agent_key
from app.models.call import Call, CallDirection, CallOutcome, CallSentiment
from app.models.carrier import Carrier, CarrierStatus, CarrierSource

router = APIRouter(prefix="/api/agent/calls", tags=["agent-calls"])


# ── Request / Response schemas ──────────────────────────────────────────────

class CallCreateRequest(BaseModel):
    mc_number: str
    direction: str = "inbound"
    phone_number: Optional[str] = None
    happyrobot_call_id: Optional[str] = None

    @field_validator("mc_number", mode="before")
    @classmethod
    def coerce_mc_number(cls, v):
        return str(v) if v is not None else v


class CallUpdateRequest(BaseModel):
    mc_number: Optional[str] = None
    load_id: Optional[str] = None
    outcome: Optional[str] = None
    sentiment: Optional[str] = None
    transcript_summary: Optional[str] = None
    extracted_data: Optional[dict] = None
    happyrobot_call_id: Optional[str] = None


class CallClassifyRequest(BaseModel):
    outcome: str
    sentiment: Optional[str] = None
    transcript_summary: Optional[str] = None
    extracted_data: Optional[dict] = None

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, v):
        valid = {e.value for e in CallOutcome}
        if v not in valid:
            raise ValueError(f"outcome must be one of {sorted(valid)}")
        return v


class TranscriptAppendRequest(BaseModel):
    role: str
    message: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in {"assistant", "caller"}:
            raise ValueError("role must be 'assistant' or 'caller'")
        return v


def _call_response(call: Call) -> dict:
    """Build a standard call response dict."""
    return {
        "call_id": call.id,
        "carrier_id": call.carrier_id,
        "mc_number": call.mc_number,
        "direction": call.direction.value if hasattr(call.direction, "value") else call.direction,
        "call_start": call.call_start.isoformat() if call.call_start else None,
        "call_end": call.call_end.isoformat() if call.call_end else None,
        "duration_seconds": call.duration_seconds,
        "outcome": call.outcome.value if hasattr(call.outcome, "value") else call.outcome,
        "sentiment": call.sentiment.value if call.sentiment and hasattr(call.sentiment, "value") else call.sentiment,
        "transcript_summary": call.transcript_summary,
        "extracted_data": call.extracted_data,
        "transferred_to_rep": call.transferred_to_rep,
        "happyrobot_call_id": call.happyrobot_call_id,
        "phone_number": call.phone_number,
        "load_id": call.load_id,
    }


# ── POST /api/agent/calls ────────────────────────────────────────────────────

@router.post("")
def create_call(
    payload: CallCreateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """Register a new inbound call. Creates carrier if not in DB."""
    mc = payload.mc_number.strip()

    # Look up or create carrier
    carrier = db.query(Carrier).filter(Carrier.mc_number == mc).first()
    if not carrier:
        carrier = Carrier(
            id=str(uuid.uuid4()),
            mc_number=mc,
            legal_name=f"Unknown Carrier MC#{mc}",
            status=CarrierStatus.in_review,
            source=CarrierSource.manual,
            is_authorized=False,
        )
        db.add(carrier)
        db.flush()  # get carrier.id before commit

    # Validate direction enum
    try:
        direction_enum = CallDirection(payload.direction)
    except ValueError:
        direction_enum = CallDirection.inbound

    call = Call(
        id=str(uuid.uuid4()),
        carrier_id=carrier.id,
        mc_number=mc,
        direction=direction_enum,
        call_start=datetime.now(timezone.utc),
        outcome=CallOutcome.in_progress,
        phone_number=payload.phone_number,
        happyrobot_call_id=payload.happyrobot_call_id,
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    return _call_response(call)


# ── PATCH /api/agent/calls/{call_id} ────────────────────────────────────────

@router.patch("/{call_id}")
def update_call(
    call_id: str,
    payload: CallUpdateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """Update optional fields on an existing call."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")

    if payload.mc_number is not None and payload.mc_number.strip():
        mc = payload.mc_number.strip()
        carrier = db.query(Carrier).filter(Carrier.mc_number == mc).first()
        if not carrier:
            carrier = Carrier(
                id=str(uuid.uuid4()),
                mc_number=mc,
                legal_name=f"Unknown Carrier MC#{mc}",
                status=CarrierStatus.in_review,
                source=CarrierSource.manual,
                is_authorized=False,
            )
            db.add(carrier)
            db.flush()
        call.mc_number = mc
        call.carrier_id = carrier.id

    if payload.load_id is not None:
        call.load_id = payload.load_id

    if payload.outcome is not None:
        try:
            call.outcome = CallOutcome(payload.outcome)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid outcome: {payload.outcome}")

    if payload.sentiment is not None:
        try:
            call.sentiment = CallSentiment(payload.sentiment)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid sentiment: {payload.sentiment}")

    if payload.transcript_summary is not None:
        call.transcript_summary = payload.transcript_summary

    if payload.extracted_data is not None:
        call.extracted_data = payload.extracted_data

    if payload.happyrobot_call_id is not None:
        call.happyrobot_call_id = payload.happyrobot_call_id

    db.commit()
    db.refresh(call)
    return _call_response(call)


# ── POST /api/agent/calls/{call_id}/update (alias for PATCH) ─────────────────

@router.post("/{call_id}/update")
def update_call_post(
    call_id: str,
    payload: CallUpdateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """POST alias for PATCH update_call — for platforms that don't support PATCH."""
    return update_call(call_id, payload, db)


# ── POST /api/agent/calls/{call_id}/transfer ────────────────────────────────

@router.post("/{call_id}/transfer")
def transfer_call(
    call_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """Mock transfer to sales rep."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")

    call.transferred_to_rep = True
    call.outcome = CallOutcome.transferred
    db.commit()

    return {
        "status": "success",
        "message": "Transfer was successful and now you can wrap up the conversation.",
    }


# ── POST /api/agent/calls/{call_id}/classify ────────────────────────────────

@router.post("/{call_id}/classify")
def classify_call(
    call_id: str,
    payload: CallClassifyRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """Final classification of a call — sets call_end and computes duration."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")

    now = datetime.now(timezone.utc)
    call.call_end = now
    call_start = call.call_start.replace(tzinfo=timezone.utc) if call.call_start.tzinfo is None else call.call_start
    call.duration_seconds = int((now - call_start).total_seconds())
    call.outcome = CallOutcome(payload.outcome)

    # Auto-mark linked load as covered when call is booked, set financial fields
    if payload.outcome == "booked" and call.load_id:
        from app.models.load import Load, LoadStatus
        from app.models.negotiation import Negotiation, NegotiationResponse
        from app.models.quote import Quote
        load = db.query(Load).filter(Load.id == call.load_id).first()
        if load and load.status == LoadStatus.available:
            load.status = LoadStatus.covered
            load.is_ai_booked = True

            # Get the final accepted negotiation price as booked_rate
            last_accepted = (
                db.query(Negotiation)
                .filter(Negotiation.call_id == call.id)
                .filter(Negotiation.system_response == NegotiationResponse.accept)
                .order_by(Negotiation.round_number.desc())
                .first()
            )
            if last_accepted:
                load.booked_rate = last_accepted.carrier_offer
            else:
                # Fallback: use loadboard_rate as booked_rate
                load.booked_rate = load.loadboard_rate

            # Compute margin_pct using the linked quote's quoted_rate
            if load.quote_id:
                quote = db.query(Quote).filter(Quote.id == load.quote_id).first()
                if quote and quote.quoted_rate and load.booked_rate:
                    load.margin_pct = round(
                        (quote.quoted_rate - load.booked_rate) / quote.quoted_rate * 100, 2
                    )
                    # Mark quote as accepted
                    quote.status = "accepted"

    if payload.sentiment is not None:
        try:
            call.sentiment = CallSentiment(payload.sentiment)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid sentiment: {payload.sentiment}")

    if payload.transcript_summary is not None:
        call.transcript_summary = payload.transcript_summary

    if payload.extracted_data is not None:
        call.extracted_data = payload.extracted_data

    db.commit()
    db.refresh(call)

    return {
        "status": "classified",
        "call_id": call.id,
        "outcome": call.outcome.value if hasattr(call.outcome, "value") else call.outcome,
        "duration_seconds": call.duration_seconds,
    }


# ── POST /api/agent/calls/{call_id}/transcript ──────────────────────────────

@router.post("/{call_id}/transcript")
def append_transcript(
    call_id: str,
    payload: TranscriptAppendRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """Append a single transcript entry to the live call transcript."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")

    # Compute elapsed time since call_start
    now = datetime.now(timezone.utc)
    call_start = call.call_start.replace(tzinfo=timezone.utc) if call.call_start.tzinfo is None else call.call_start
    elapsed = int((now - call_start).total_seconds())
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60
    timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    entry = {
        "role": payload.role,
        "message": payload.message,
        "timestamp": timestamp_str,
    }

    current = call.transcript_full or []
    current = list(current)  # defensive copy
    current.append(entry)
    call.transcript_full = current

    db.commit()
    db.refresh(call)

    return {"status": "ok", "entry_count": len(call.transcript_full)}
