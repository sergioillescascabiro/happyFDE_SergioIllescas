from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import uuid

from app.database import get_db
from app.middleware.auth import require_agent_key
from app.models.call import Call, CallDirection, CallOutcome

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# ── Request schemas ──────────────────────────────────────────────────────────

class WebhookCallStartedRequest(BaseModel):
    call_id: str                        # HappyRobot's call identifier
    phone_number: Optional[str] = None
    direction: Optional[str] = "inbound"
    timestamp: Optional[str] = None     # ISO 8601 UTC timestamp
    agent_id: Optional[str] = None
    metadata: Optional[dict] = None


class WebhookCallEndedRequest(BaseModel):
    call_id: str                        # HappyRobot's call identifier
    duration_seconds: Optional[int] = None
    end_timestamp: Optional[str] = None
    recording_url: Optional[str] = None
    transcript_url: Optional[str] = None


class TranscriptEntry(BaseModel):
    role: str
    message: str
    timestamp: Optional[str] = None


class WebhookTranscriptRequest(BaseModel):
    call_id: str                        # HappyRobot's call identifier
    transcript: Optional[List[TranscriptEntry]] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    extracted_data: Optional[dict] = None


# ── POST /api/webhooks/call-started ─────────────────────────────────────────

@router.post("/call-started")
def webhook_call_started(
    payload: WebhookCallStartedRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """Webhook: HappyRobot notifies that a call has started.

    Expected payload from HappyRobot platform:
    {
        "call_id": "HR-12345",              # HappyRobot's call identifier
        "phone_number": "+1-312-555-0111",  # Caller's phone number
        "direction": "inbound",             # Call direction
        "timestamp": "2026-04-13T14:30:00Z",# ISO 8601 UTC timestamp
        "agent_id": "agent-abc123",         # Which agent received the call
        "metadata": {}                      # Optional caller metadata
    }

    This webhook creates or updates a Call record linked to the HappyRobot call ID.
    """
    # Check if call already exists for this HR call_id
    existing = db.query(Call).filter(Call.happyrobot_call_id == payload.call_id).first()
    if existing:
        return {"status": "received", "call_id": existing.id}

    # Parse call_start from timestamp or use now
    call_start = datetime.utcnow()
    if payload.timestamp:
        try:
            call_start = datetime.fromisoformat(payload.timestamp.replace("Z", "+00:00"))
            # Convert to naive UTC for consistency with rest of app
            if call_start.tzinfo is not None:
                call_start = call_start.replace(tzinfo=None)
        except (ValueError, AttributeError):
            call_start = datetime.utcnow()

    # Validate direction
    try:
        direction_enum = CallDirection(payload.direction or "inbound")
    except ValueError:
        direction_enum = CallDirection.inbound

    call = Call(
        id=str(uuid.uuid4()),
        mc_number="unknown",
        direction=direction_enum,
        call_start=call_start,
        outcome=CallOutcome.in_progress,
        happyrobot_call_id=payload.call_id,
        phone_number=payload.phone_number,
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    return {"status": "received", "call_id": call.id}


# ── POST /api/webhooks/call-ended ───────────────────────────────────────────

@router.post("/call-ended")
def webhook_call_ended(
    payload: WebhookCallEndedRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """Webhook: HappyRobot notifies that a call has ended.

    Expected payload from HappyRobot platform:
    {
        "call_id": "HR-12345",              # HappyRobot's call identifier
        "duration_seconds": 183,            # Call duration in seconds
        "end_timestamp": "2026-04-13T14:33:03Z",  # ISO 8601 UTC timestamp
        "recording_url": "https://...",     # Optional recording URL (stored in extracted_data)
        "transcript_url": "https://..."     # Optional transcript URL (stored in extracted_data)
    }

    Updates the linked Call record with call_end and duration_seconds.
    """
    call = db.query(Call).filter(Call.happyrobot_call_id == payload.call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail=f"No call found for HappyRobot call_id: {payload.call_id}")

    # Parse end_timestamp or use now
    call_end = datetime.utcnow()
    if payload.end_timestamp:
        try:
            call_end = datetime.fromisoformat(payload.end_timestamp.replace("Z", "+00:00"))
            if call_end.tzinfo is not None:
                call_end = call_end.replace(tzinfo=None)
        except (ValueError, AttributeError):
            call_end = datetime.utcnow()

    call.call_end = call_end

    if payload.duration_seconds is not None:
        call.duration_seconds = payload.duration_seconds
    elif call.call_start:
        call.duration_seconds = int((call_end - call.call_start).total_seconds())

    # Merge optional URLs into extracted_data
    if payload.recording_url or payload.transcript_url:
        existing_data = call.extracted_data or {}
        existing_data = dict(existing_data)
        if payload.recording_url:
            existing_data["recording_url"] = payload.recording_url
        if payload.transcript_url:
            existing_data["transcript_url"] = payload.transcript_url
        call.extracted_data = existing_data

    db.commit()
    db.refresh(call)

    return {"status": "received", "call_id": call.id}


# ── POST /api/webhooks/transcript ───────────────────────────────────────────

@router.post("/transcript")
def webhook_transcript(
    payload: WebhookTranscriptRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """Webhook: HappyRobot delivers full post-call transcript.

    Expected payload from HappyRobot platform:
    {
        "call_id": "HR-12345",             # HappyRobot's call identifier
        "transcript": [                    # Array of transcript entries
            {"role": "assistant", "message": "...", "timestamp": "00:00:05"},
            {"role": "caller", "message": "...", "timestamp": "00:00:12"}
        ],
        "summary": "Carrier booked load 202883.",   # Optional AI-generated summary
        "sentiment": "positive",                    # Optional sentiment classification
        "extracted_data": {                         # Optional structured extraction
            "mc_number": "98765",
            "load_id": "202883",
            "agreed_rate": 820.00
        }
    }

    Stores the full transcript, summary, sentiment, and extracted data on the Call record.
    """
    call = db.query(Call).filter(Call.happyrobot_call_id == payload.call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail=f"No call found for HappyRobot call_id: {payload.call_id}")

    if payload.transcript is not None:
        call.transcript_full = [entry.model_dump() for entry in payload.transcript]

    if payload.summary is not None:
        call.transcript_summary = payload.summary

    if payload.sentiment is not None:
        from app.models.call import CallSentiment
        try:
            call.sentiment = CallSentiment(payload.sentiment)
        except ValueError:
            pass  # ignore invalid sentiment from webhook

    if payload.extracted_data is not None:
        existing_data = call.extracted_data or {}
        existing_data = dict(existing_data)
        existing_data.update(payload.extracted_data)
        call.extracted_data = existing_data

    db.commit()
    db.refresh(call)

    return {"status": "received", "call_id": call.id}
