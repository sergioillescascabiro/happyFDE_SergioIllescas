from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class QuoteResponse(BaseModel):
    id: str
    shipper_id: str
    origin: str
    destination: str
    equipment_type: str
    market_rate: float
    quoted_rate: float
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
