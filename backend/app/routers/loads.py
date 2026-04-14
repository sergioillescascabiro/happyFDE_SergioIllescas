from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
import uuid
from datetime import datetime, timezone

from app.database import get_db
from app.middleware.auth import require_dashboard_token
from app.models.load import Load, LoadStatus
from app.models.carrier import Carrier, CarrierLoadHistory
from app.models.call import Call
from app.schemas.load import (
    LoadCreate, LoadUpdate, LoadResponse, LoadListResponse,
    LoadDetailResponse, CarrierSummary, LoadStatusEnum
)

router = APIRouter(prefix="/api/loads", tags=["loads"])

def _to_response(load: Load) -> LoadResponse:
    return LoadResponse.from_orm_with_computed(load)

@router.get("", response_model=LoadListResponse)
def list_loads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    equipment_type: Optional[str] = None,
    shipper_id: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    query = db.query(Load)
    if status:
        try:
            query = query.filter(Load.status == LoadStatus(status))
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")
    if equipment_type:
        query = query.filter(Load.equipment_type == equipment_type)
    if shipper_id:
        query = query.filter(Load.shipper_id == shipper_id)
    if origin:
        query = query.filter(Load.origin.ilike(f"%{origin}%"))
    if destination:
        query = query.filter(Load.destination.ilike(f"%{destination}%"))
    if search:
        query = query.filter(
            Load.load_id.ilike(f"%{search}%") |
            Load.origin.ilike(f"%{search}%") |
            Load.destination.ilike(f"%{search}%") |
            Load.commodity_type.ilike(f"%{search}%")
        )

    total = query.count()
    loads = query.order_by(Load.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    import math
    return LoadListResponse(
        items=[_to_response(l) for l in loads],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )

@router.get("/{load_id}", response_model=LoadDetailResponse)
def get_load(
    load_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    load = db.query(Load).filter((Load.load_id == load_id) | (Load.id == load_id)).first()
    if not load:
        raise HTTPException(404, f"Load {load_id} not found")

    origin_state = load.origin.split(",")[-1].strip() if "," in load.origin else ""
    dest_state = load.destination.split(",")[-1].strip() if "," in load.destination else ""
    
    history = (
        db.query(CarrierLoadHistory, Carrier)
        .join(Carrier, CarrierLoadHistory.carrier_id == Carrier.id)
        .filter(CarrierLoadHistory.equipment_type == load.equipment_type)
        .filter(CarrierLoadHistory.origin_region == origin_state)
        .filter(CarrierLoadHistory.destination_region == dest_state)
        .order_by(CarrierLoadHistory.similar_match_count.desc())
        .limit(5)
        .all()
    )

    rec_carriers = [
        CarrierSummary(
            id=c.id,
            mc_number=c.mc_number,
            legal_name=c.legal_name,
            status=c.status.value,
            similar_match_count=h.similar_match_count,
        ) for h, c in history
    ]

    base = LoadResponse.from_orm_with_computed(load)
    return LoadDetailResponse(**base.model_dump(), recommended_carriers=rec_carriers)

@router.post("", response_model=LoadResponse, status_code=201)
def create_load(
    payload: LoadCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    existing = db.query(Load).filter(Load.load_id == payload.load_id).first()
    if existing:
        raise HTTPException(409, f"Load ID {payload.load_id} already exists")

    max_rate = round(payload.quoted_rate * 0.85, 2)
    min_rate = round(payload.loadboard_rate * 0.85, 2)

    load_data = payload.model_dump(exclude={"quoted_rate"})
    load = Load(
        id=str(uuid.uuid4()),
        **load_data,
        max_rate=max_rate,
        min_rate=min_rate,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(load)

    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e.orig))

    from app.models.quote import Quote, QuoteStatus
    quote = Quote(
        id=str(uuid.uuid4()),
        shipper_id=load.shipper_id,
        load_id=load.id,
        origin=load.origin,
        destination=load.destination,
        equipment_type=load.equipment_type,
        market_rate=round(load.loadboard_rate, 2),
        quoted_rate=round(payload.quoted_rate, 2),
        status=QuoteStatus.pending,
    )
    db.add(quote)
    try:
        db.flush()
        load.quote_id = quote.id
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e.orig))
    db.refresh(load)
    return _to_response(load)

@router.patch("/{load_id}", response_model=LoadResponse)
def update_load(
    load_id: str,
    payload: LoadUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    load = db.query(Load).filter(Load.load_id == load_id).first()
    if not load:
        raise HTTPException(404, f"Load {load_id} not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(load, field, value)

    if update_data.get("status") in [LoadStatusEnum.covered, "covered"]:
        if load.quote_id and load.booked_rate is None:
            load.booked_rate = load.loadboard_rate
            load.is_ai_booked = False
            from app.models.quote import Quote
            quote = db.query(Quote).filter(Quote.id == load.quote_id).first()
            if quote and quote.quoted_rate:
                load.margin_pct = round((quote.quoted_rate - load.booked_rate) / quote.quoted_rate * 100, 2)

    load.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(load)
    return _to_response(load)

@router.post("/refresh-status")
def refresh_load_statuses(
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    from app.services.load_service import refresh_delivered_status
    updated = refresh_delivered_status(db)
    return {"updated": updated, "message": f"{updated} load(s) updated"}

@router.get("/{load_id}/carriers", response_model=List[CarrierSummary])
def get_load_carriers(
    load_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    load = db.query(Load).filter(Load.load_id == load_id).first()
    if not load:
        raise HTTPException(404, f"Load {load_id} not found")

    origin_state = load.origin.split(",")[-1].strip() if "," in load.origin else ""
    dest_state = load.destination.split(",")[-1].strip() if "," in load.destination else ""
    
    history = (
        db.query(CarrierLoadHistory, Carrier)
        .join(Carrier, CarrierLoadHistory.carrier_id == Carrier.id)
        .filter(CarrierLoadHistory.equipment_type == load.equipment_type)
        .filter(CarrierLoadHistory.origin_region == origin_state)
        .filter(CarrierLoadHistory.destination_region == dest_state)
        .order_by(CarrierLoadHistory.similar_match_count.desc())
        .all()
    )
    return [
        CarrierSummary(
            id=c.id,
            mc_number=c.mc_number,
            legal_name=c.legal_name,
            status=c.status.value,
            similar_match_count=h.similar_match_count,
        )
        for h, c in history
    ]

@router.get("/{load_id}/calls")
def get_load_calls(
    load_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    load = db.query(Load).filter(Load.load_id == load_id).first()
    if not load:
        raise HTTPException(404, f"Load {load_id} not found")

    calls = db.query(Call).filter(Call.load_id == load.id).order_by(Call.call_start.desc()).all()
    return [
        {
            "id": c.id,
            "mc_number": c.mc_number,
            "direction": c.direction.value,
            "outcome": c.outcome.value,
            "sentiment": c.sentiment.value if c.sentiment else None,
            "call_start": c.call_start,
            "call_end": c.call_end,
            "duration_seconds": c.duration_seconds,
            "phone_number": c.phone_number,
            "use_case": c.use_case,
        }
        for c in calls
    ]
