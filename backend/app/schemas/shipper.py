from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ShipperResponse(BaseModel):
    id: str
    name: str
    contact_name: str
    contact_email: str
    contact_phone: str
    address: str
    logo_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShipperKPIs(BaseModel):
    shipper_id: str
    shipper_name: str
    total_loads: int
    available_loads: int
    covered_loads: int
    pending_loads: int
    cancelled_loads: int
    total_calls: int
    booked_calls: int
    conversion_rate: float
    total_cargo_value: float
