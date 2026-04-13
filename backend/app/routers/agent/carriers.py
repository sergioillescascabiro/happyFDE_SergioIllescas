from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.middleware.auth import require_agent_key
from app.services.fmcsa import verify_carrier

router = APIRouter(prefix="/api/agent/carriers", tags=["agent-carriers"])


class CarrierVerifyRequest(BaseModel):
    mc_number: str


class CarrierVerificationResponse(BaseModel):
    id: str
    mc_number: str
    dot_number: Optional[str] = None
    legal_name: str
    phone: Optional[str] = None
    physical_address: Optional[str] = None
    is_authorized: bool
    safety_rating: Optional[str] = None
    status: str
    verification_date: Optional[datetime] = None
    source: str
    message: str


@router.post("/verify", response_model=CarrierVerificationResponse)
def verify_carrier_endpoint(
    payload: CarrierVerifyRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_agent_key),
):
    """Verify a carrier by MC number via FMCSA (real or mock)."""
    mc = payload.mc_number.strip()
    if not mc:
        raise HTTPException(status_code=422, detail="mc_number must not be empty")

    result = verify_carrier(mc, db)

    if result["is_authorized"]:
        message = (
            f"{result['legal_name']} (MC#{mc}) is authorized to operate. "
            f"Safety rating: {result.get('safety_rating') or 'N/A'}."
        )
    else:
        message = (
            f"{result['legal_name']} (MC#{mc}) is NOT authorized to operate. "
            f"This carrier cannot be booked."
        )

    return CarrierVerificationResponse(**result, message=message)
