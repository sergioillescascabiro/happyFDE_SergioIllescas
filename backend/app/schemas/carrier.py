from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CarrierResponse(BaseModel):
    id: str
    mc_number: str
    dot_number: Optional[str] = None
    legal_name: str
    dba_name: Optional[str] = None
    phone: Optional[str] = None
    physical_address: Optional[str] = None
    is_authorized: bool
    safety_rating: Optional[str] = None
    status: str
    source: str
    verification_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CarrierListResponse(BaseModel):
    items: list[CarrierResponse]
    total: int
