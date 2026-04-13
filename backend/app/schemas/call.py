from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class NegotiationRound(BaseModel):
    id: str
    round_number: int
    carrier_offer: float
    carrier_offer_per_mile: float
    system_response: str
    counter_offer: Optional[float] = None
    counter_offer_per_mile: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CallResponse(BaseModel):
    id: str
    carrier_id: Optional[str] = None
    load_id: Optional[str] = None
    shipper_id: Optional[str] = None
    mc_number: str
    direction: str
    call_start: datetime
    call_end: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    outcome: str
    sentiment: Optional[str] = None
    transcript_summary: Optional[str] = None
    transferred_to_rep: bool
    happyrobot_call_id: Optional[str] = None
    phone_number: Optional[str] = None
    use_case: str
    created_at: datetime
    updated_at: datetime
    # Enrichment
    carrier_name: Optional[str] = None
    load_load_id: Optional[str] = None

    model_config = {"from_attributes": True}


class CallDetailResponse(CallResponse):
    transcript_full: Optional[Any] = None
    extracted_data: Optional[Any] = None
    negotiations: list[NegotiationRound] = []


class CallListResponse(BaseModel):
    items: list[CallResponse]
    total: int
    page: int
    page_size: int
    pages: int
