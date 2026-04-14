from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from app.database import get_db
from app.middleware.auth import require_agent_key
from app.models.call import Call, CallDirection, CallOutcome

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

class WebhookCallStartedRequest(BaseModel):
    call_id: str
    phone_number: Optional[str] = None
    direction: Optional[str] = "inbound"
    timestamp: Optional[str] = None
    agent_id: Optional[str] = None
    metadata: Optional[dict] = None

class WebhookCallEndedRequest(BaseModel):
    call_id: str
    duration_seconds: Optional[int] = None
    end_timestamp: Optional[str] = None
    recording_url: Optional[str] = None
    transcript_url: Optional[str] = None

class TranscriptEntry(BaseModel):
    role: str
    message: str
    timestamp: Optional[str] = None

class WebhookTranscriptRequest(BaseModel):
    call_id: str
    transcript: Optional[List[TranscriptEntry]] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    extracted_data: Optional[dict] = None

@router.post("/call-started")
def webhook_call_started(
    payload: WebhookCallStartedRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    existing = db.query(Call).filter(Call.happyrobot_call_id == payload.call_id).first()
    if existing:
        return {"status": "received", "call_id": existing.id}

    call_start = datetime.now(timezone.utc)
    if payload.timestamp:
        try:
            call_start = datetime.fromisoformat(payload.timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
        except:
            pass

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

@router.post("/call-ended")
def webhook_call_ended(
    payload: WebhookCallEndedRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    call = db.query(Call).filter(Call.happyrobot_call_id == payload.call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    call_end = datetime.now(timezone.utc)
    if payload.end_timestamp:
        try:
            call_end = datetime.fromisoformat(payload.end_timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
        except:
            pass

    call.call_end = call_end
    if payload.duration_seconds is not None:
        call.duration_seconds = payload.duration_seconds
    elif call.call_start:
        call.duration_seconds = int((call_end - call.call_start).total_seconds())

    if payload.recording_url or payload.transcript_url:
        existing_data = dict(call.extracted_data or {})
        if payload.recording_url: existing_data["recording_url"] = payload.recording_url
        if payload.transcript_url: existing_data["transcript_url"] = payload.transcript_url
        call.extracted_data = existing_data

    db.commit()
    return {"status": "received", "call_id": call.id}

@router.post("/partial-transcript")
def webhook_partial_transcript(
    payload: dict,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    call_id = payload.get("call_id")
    message = payload.get("message")
    role = payload.get("role", "assistant")
    
    if not call_id or not message:
        raise HTTPException(status_code=400, detail="Missing call_id or message")
        
    call = db.query(Call).filter(Call.happyrobot_call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
        
    current_transcript = list(call.transcript_full or [])
    current_transcript.append({
        "role": role,
        "message": message,
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")
    })
    call.transcript_full = current_transcript
    db.commit()
    return {"status": "received"}

@router.post("/transcript")
def webhook_transcript(
    payload: WebhookTranscriptRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    call = db.query(Call).filter(Call.happyrobot_call_id == payload.call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if payload.transcript is not None:
        call.transcript_full = [entry.model_dump() for entry in payload.transcript]

    if payload.summary is not None:
        call.transcript_summary = payload.summary

    if payload.sentiment is not None:
        from app.models.call import CallSentiment
        try:
            call.sentiment = CallSentiment(payload.sentiment)
        except ValueError:
            pass

    if payload.extracted_data is not None:
        existing_data = dict(call.extracted_data or {})
        existing_data.update(payload.extracted_data)
        call.extracted_data = existing_data

    db.commit()
    return {"status": "received", "call_id": call.id}

