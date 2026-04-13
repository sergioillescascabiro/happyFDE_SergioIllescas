from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
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


class CallUpdateRequest(BaseModel):
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
        call_start=datetime.utcnow(),
        outcome=CallOutcome.in_progress,
        phone_number=payload.phone_number,
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

    now = datetime.utcnow()
    call.call_end = now
    call.duration_seconds = int((now - call.call_start).total_seconds())
    call.outcome = CallOutcome(payload.outcome)

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
    now = datetime.utcnow()
    elapsed = int((now - call.call_start).total_seconds())
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
