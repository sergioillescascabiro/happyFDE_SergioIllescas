from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import math
import json
import asyncio

from app.database import get_db, SessionLocal
from app.middleware.auth import require_dashboard_token
from app.models.call import Call, CallOutcome, CallSentiment, CallDirection
from app.models.carrier import Carrier
from app.models.load import Load
from app.models.negotiation import Negotiation
from app.schemas.call import CallResponse, CallDetailResponse, CallListResponse, NegotiationRound

router = APIRouter(prefix="/api/calls", tags=["calls"])


def _enrich(call: Call, db: Session) -> dict:
    data = {
        "id": call.id,
        "carrier_id": call.carrier_id,
        "load_id": call.load_id,
        "shipper_id": call.shipper_id,
        "mc_number": call.mc_number,
        "direction": call.direction.value,
        "call_start": call.call_start,
        "call_end": call.call_end,
        "duration_seconds": call.duration_seconds,
        "outcome": call.outcome.value,
        "sentiment": call.sentiment.value if call.sentiment else None,
        "transcript_summary": call.transcript_summary,
        "transferred_to_rep": call.transferred_to_rep,
        "happyrobot_call_id": call.happyrobot_call_id,
        "phone_number": call.phone_number,
        "use_case": call.use_case,
        "created_at": call.created_at,
        "updated_at": call.updated_at,
        "carrier_name": None,
        "load_load_id": None,
    }
    if call.carrier_id:
        carrier = db.query(Carrier).filter(Carrier.id == call.carrier_id).first()
        if carrier:
            data["carrier_name"] = carrier.legal_name
    if call.load_id:
        load = db.query(Load).filter(Load.id == call.load_id).first()
        if load:
            data["load_load_id"] = load.load_id
    return data


def _enrich_as_json(call: Call, db: Session) -> dict:
    """Same as _enrich but serializes datetimes for JSON/SSE transport."""
    data = _enrich(call, db)
    data["transcript_full"] = call.transcript_full
    # Convert datetimes to ISO strings for JSON serialization
    for key in ("call_start", "call_end", "created_at", "updated_at"):
        if isinstance(data.get(key), datetime):
            data[key] = data[key].isoformat()
    return data


@router.get("/live")
def get_live_calls(
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    """Return live and recent calls: in_progress OR started within the last 30 minutes."""
    cutoff = datetime.utcnow() - timedelta(minutes=30)
    calls = (
        db.query(Call)
        .filter(
            (Call.outcome == CallOutcome.in_progress) |
            (Call.call_start >= cutoff)
        )
        .order_by(Call.call_start.desc())
        .limit(50)
        .all()
    )
    result = []
    for call in calls:
        data = _enrich(call, db)
        data["transcript_full"] = call.transcript_full
        result.append(data)
    return result


@router.get("/live/stream")
async def stream_live_calls(
    request: Request,
    _: str = Depends(require_dashboard_token),
):
    """SSE stream of live call updates. Sends a snapshot every 2 seconds.

    Each event is a JSON array of calls that are in_progress or started
    within the last 30 minutes. Connect with:
        EventSource('/api/calls/live/stream', {headers: {'X-Dashboard-Token': '...'}})
    """
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            db = SessionLocal()
            try:
                cutoff = datetime.utcnow() - timedelta(minutes=30)
                calls = (
                    db.query(Call)
                    .filter(
                        (Call.outcome == CallOutcome.in_progress) |
                        (Call.call_start >= cutoff)
                    )
                    .order_by(Call.call_start.desc())
                    .limit(20)
                    .all()
                )
                payload = [_enrich_as_json(c, db) for c in calls]
                yield f"data: {json.dumps(payload)}\n\n"
            except Exception:
                yield "data: []\n\n"
            finally:
                db.close()
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("", response_model=CallListResponse)
def list_calls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    outcome: Optional[str] = None,
    sentiment: Optional[str] = None,
    direction: Optional[str] = None,
    carrier_id: Optional[str] = None,
    load_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    query = db.query(Call)

    if outcome:
        try:
            query = query.filter(Call.outcome == CallOutcome(outcome))
        except ValueError:
            raise HTTPException(400, f"Invalid outcome: {outcome}")
    if sentiment:
        try:
            query = query.filter(Call.sentiment == CallSentiment(sentiment))
        except ValueError:
            raise HTTPException(400, f"Invalid sentiment: {sentiment}")
    if direction:
        try:
            query = query.filter(Call.direction == CallDirection(direction))
        except ValueError:
            raise HTTPException(400, f"Invalid direction: {direction}")
    if carrier_id:
        query = query.filter(Call.carrier_id == carrier_id)
    if load_id:
        query = query.filter(Call.load_id == load_id)

    total = query.count()
    calls = query.order_by(Call.call_start.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for call in calls:
        data = _enrich(call, db)
        items.append(CallResponse(**data))

    return CallListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{call_id}", response_model=CallDetailResponse)
def get_call(
    call_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(404, f"Call {call_id} not found")

    data = _enrich(call, db)
    data["transcript_full"] = call.transcript_full
    data["extracted_data"] = call.extracted_data

    negs = db.query(Negotiation).filter(Negotiation.call_id == call.id).order_by(Negotiation.round_number).all()
    data["negotiations"] = [NegotiationRound.model_validate(n) for n in negs]

    return CallDetailResponse(**data)
