from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime

from app.database import get_db
from app.middleware.auth import require_agent_key
from app.models.load import Load, LoadStatus

router = APIRouter(prefix="/api/agent/loads", tags=["agent-loads"])


class AgentLoadResponse(BaseModel):
    id: str
    load_id: str
    origin: str
    destination: str
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str
    weight: float
    commodity_type: str
    miles: float
    num_of_pieces: int
    dimensions: Optional[str] = None
    notes: Optional[str] = None
    reference_id: Optional[str] = None
    loadboard_rate: float   # total quoted price (NEVER per-mile)
    per_mile_rate: float    # computed: loadboard_rate / miles

    model_config = {"from_attributes": True}


def _to_agent_load(load: Load) -> AgentLoadResponse:
    # Round to nearest $25 — industry standard, avoids agent saying "$1,345.08"
    loadboard_rate = round(load.loadboard_rate / 25) * 25
    per_mile = round(loadboard_rate / load.miles, 2) if load.miles > 0 else 0.0
    return AgentLoadResponse(
        id=load.id,
        load_id=load.load_id,
        origin=load.origin,
        destination=load.destination,
        pickup_datetime=load.pickup_datetime,
        delivery_datetime=load.delivery_datetime,
        equipment_type=load.equipment_type,
        weight=load.weight,
        commodity_type=load.commodity_type,
        miles=load.miles,
        num_of_pieces=load.num_of_pieces,
        dimensions=load.dimensions,
        notes=load.notes,
        reference_id=load.reference_id,
        loadboard_rate=float(loadboard_rate),
        per_mile_rate=per_mile,
    )


@router.get("/search", response_model=AgentLoadResponse)
def search_loads(
    reference_id: Optional[str] = Query(None),
    origin: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    equipment_type: Optional[str] = Query(None),
    pickup_date_from: Optional[date] = Query(None),
    pickup_date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """Find the best available load.

    Two modes (mutually exclusive — reference_id takes priority):
    - By reference: pass reference_id to look up a specific posting.
    - By lane: pass origin / destination / equipment_type for a fuzzy search;
      returns the single best match (earliest pickup date).
    """
    query = db.query(Load).filter(Load.status == LoadStatus.available)

    if reference_id:
        normalized = reference_id if reference_id.upper().startswith("REF-") else f"REF-{reference_id}"
        query = query.filter(Load.reference_id == normalized)
    else:
        if origin:
            query = query.filter(Load.origin.ilike(f"%{origin}%"))
        if destination:
            query = query.filter(Load.destination.ilike(f"%{destination}%"))
        if equipment_type:
            query = query.filter(Load.equipment_type.ilike(equipment_type))
        if pickup_date_from:
            dt_from = datetime.combine(pickup_date_from, datetime.min.time())
            query = query.filter(Load.pickup_datetime >= dt_from)
        if pickup_date_to:
            dt_to = datetime.combine(pickup_date_to, datetime.max.time())
            query = query.filter(Load.pickup_datetime <= dt_to)

    best = query.order_by(Load.pickup_datetime.asc()).first()

    if not best:
        raise HTTPException(
            status_code=404,
            detail="No available loads match those criteria right now.",
        )

    return _to_agent_load(best)
