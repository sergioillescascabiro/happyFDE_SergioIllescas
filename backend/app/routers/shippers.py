from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_dashboard_token
from app.models.shipper import Shipper
from app.models.load import Load, LoadStatus
from app.models.call import Call, CallOutcome
from app.schemas.shipper import ShipperResponse, ShipperKPIs

router = APIRouter(prefix="/api/shippers", tags=["shippers"])


@router.get("", response_model=list[ShipperResponse])
def list_shippers(
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    return db.query(Shipper).filter(Shipper.is_active == True).order_by(Shipper.name).all()


@router.get("/{shipper_id}", response_model=ShipperResponse)
def get_shipper(
    shipper_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    shipper = db.query(Shipper).filter(Shipper.id == shipper_id).first()
    if not shipper:
        raise HTTPException(404, f"Shipper {shipper_id} not found")
    return shipper


@router.get("/{shipper_id}/kpis", response_model=ShipperKPIs)
def get_shipper_kpis(
    shipper_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    shipper = db.query(Shipper).filter(Shipper.id == shipper_id).first()
    if not shipper:
        raise HTTPException(404, f"Shipper {shipper_id} not found")

    loads = db.query(Load).filter(Load.shipper_id == shipper_id).all()
    load_ids = [l.id for l in loads]

    calls = db.query(Call).filter(Call.shipper_id == shipper_id).all() if load_ids else []
    booked = sum(1 for c in calls if c.outcome == CallOutcome.booked)
    total_calls = len(calls)

    cargo_value = sum(l.loadboard_rate * l.miles for l in loads)

    return ShipperKPIs(
        shipper_id=shipper_id,
        shipper_name=shipper.name,
        total_loads=len(loads),
        available_loads=sum(1 for l in loads if l.status == LoadStatus.available),
        covered_loads=sum(1 for l in loads if l.status == LoadStatus.covered),
        pending_loads=sum(1 for l in loads if l.status == LoadStatus.pending),
        cancelled_loads=sum(1 for l in loads if l.status == LoadStatus.cancelled),
        total_calls=total_calls,
        booked_calls=booked,
        conversion_rate=round(booked / total_calls * 100, 1) if total_calls > 0 else 0.0,
        total_cargo_value=round(cargo_value, 2),
    )
