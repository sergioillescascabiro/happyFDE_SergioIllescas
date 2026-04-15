from pydantic import BaseModel, computed_field, model_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class LoadStatusEnum(str, Enum):
    available = "available"
    pending = "pending"
    covered = "covered"
    cancelled = "cancelled"
    delivered = "delivered"


class LoadBase(BaseModel):
    load_id: str
    shipper_id: str
    origin: str
    destination: str
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str
    loadboard_rate: float
    notes: Optional[str] = None
    weight: float
    commodity_type: str
    num_of_pieces: int = 1
    miles: float
    dimensions: Optional[str] = None
    reference_id: Optional[str] = None
    status: LoadStatusEnum


class LoadCreate(LoadBase):
    quoted_rate: float  # what broker charges shipper — system derives max_rate from this


class LoadUpdate(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    pickup_datetime: Optional[datetime] = None
    delivery_datetime: Optional[datetime] = None
    equipment_type: Optional[str] = None
    loadboard_rate: Optional[float] = None
    notes: Optional[str] = None
    weight: Optional[float] = None
    commodity_type: Optional[str] = None
    status: Optional[LoadStatusEnum] = None


class CarrierSummary(BaseModel):
    id: str
    mc_number: str
    legal_name: str
    status: str
    similar_match_count: int

    model_config = {"from_attributes": True}


class LoadResponse(BaseModel):
    id: str
    load_id: str
    shipper_id: str
    shipper_name: Optional[str] = None
    shipper_type: Optional[str] = None
    origin: str
    destination: str
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str
    loadboard_rate: float
    notes: Optional[str] = None
    weight: float
    commodity_type: str
    num_of_pieces: int
    miles: float
    dimensions: Optional[str] = None
    reference_id: Optional[str] = None
    status: LoadStatusEnum
    created_at: datetime
    updated_at: datetime
    # Computed fields — NEVER include max_rate or min_rate
    total_rate: float = 0.0
    per_mile_rate: float = 0.0
    # Financial tracking fields (broker-visible)
    booked_rate: Optional[float] = None
    margin_pct: Optional[float] = None
    is_ai_booked: bool = False
    quote_id: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_computed(cls, load):
        data = {
            "id": load.id,
            "load_id": load.load_id,
            "shipper_id": load.shipper_id,
            "shipper_name": load.shipper.name if load.shipper else None,
            "shipper_type": load.shipper.shipper_type if load.shipper else None,
            "origin": load.origin,
            "destination": load.destination,
            "origin_lat": load.origin_lat,
            "origin_lng": load.origin_lng,
            "destination_lat": load.destination_lat,
            "destination_lng": load.destination_lng,
            "pickup_datetime": load.pickup_datetime,
            "delivery_datetime": load.delivery_datetime,
            "equipment_type": load.equipment_type,
            "loadboard_rate": load.loadboard_rate,
            "notes": load.notes,
            "weight": load.weight,
            "commodity_type": load.commodity_type,
            "num_of_pieces": load.num_of_pieces,
            "miles": load.miles,
            "dimensions": load.dimensions,
            "reference_id": load.reference_id,
            "status": load.status,
            "created_at": load.created_at,
            "updated_at": load.updated_at,
            "total_rate": round(load.loadboard_rate, 2),
            "per_mile_rate": round(load.loadboard_rate / load.miles, 4) if load.miles > 0 else 0.0,
            "booked_rate": load.booked_rate,
            "margin_pct": load.margin_pct,
            "is_ai_booked": load.is_ai_booked,
            "quote_id": load.quote_id,
        }
        return cls(**data)


class LoadListResponse(BaseModel):
    items: List[LoadResponse]
    total: int
    page: int
    page_size: int
    pages: int


class LoadDetailResponse(LoadResponse):
    recommended_carriers: List[CarrierSummary] = []
