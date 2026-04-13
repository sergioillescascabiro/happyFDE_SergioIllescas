from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.middleware.auth import require_dashboard_token
from app.models.carrier import Carrier
from app.schemas.carrier import CarrierResponse, CarrierListResponse

router = APIRouter(prefix="/api/carriers", tags=["carriers"])


@router.get("", response_model=CarrierListResponse)
def list_carriers(
    status: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    query = db.query(Carrier)
    if status:
        query = query.filter(Carrier.status == status)
    if source:
        query = query.filter(Carrier.source == source)
    if search:
        query = query.filter(
            Carrier.legal_name.ilike(f"%{search}%") |
            Carrier.mc_number.ilike(f"%{search}%")
        )
    carriers = query.order_by(Carrier.legal_name).all()
    return CarrierListResponse(items=carriers, total=len(carriers))


@router.get("/{mc_number}", response_model=CarrierResponse)
def get_carrier(
    mc_number: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    carrier = db.query(Carrier).filter(Carrier.mc_number == mc_number).first()
    if not carrier:
        raise HTTPException(404, f"Carrier with MC {mc_number} not found")
    return carrier
