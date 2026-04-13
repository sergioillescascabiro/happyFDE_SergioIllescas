import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, JSON, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class CarrierStatus(str, enum.Enum):
    active = "active"
    in_review = "in_review"
    suspended = "suspended"
    inactive = "inactive"

class CarrierSource(str, enum.Enum):
    fmcsa = "fmcsa"
    tms_import = "tms_import"
    manual = "manual"

class Carrier(Base):
    __tablename__ = "carriers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    mc_number: Mapped[str] = mapped_column(String, unique=True)
    dot_number: Mapped[str | None] = mapped_column(String, nullable=True)
    legal_name: Mapped[str] = mapped_column(String)
    dba_name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    physical_address: Mapped[str | None] = mapped_column(String, nullable=True)
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=True)
    safety_rating: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[CarrierStatus] = mapped_column(SAEnum(CarrierStatus), default=CarrierStatus.active)
    source: Mapped[CarrierSource] = mapped_column(SAEnum(CarrierSource))
    verification_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_fmcsa_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

class CarrierLoadHistory(Base):
    __tablename__ = "carrier_load_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    carrier_id: Mapped[str] = mapped_column(String, ForeignKey("carriers.id"))
    load_id: Mapped[str | None] = mapped_column(String, ForeignKey("loads.id"), nullable=True)
    origin_region: Mapped[str] = mapped_column(String)
    destination_region: Mapped[str] = mapped_column(String)
    equipment_type: Mapped[str] = mapped_column(String)
    similar_match_count: Mapped[int] = mapped_column(Integer, default=1)
    last_service_date: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    carrier: Mapped["Carrier"] = relationship("Carrier", backref="load_history")
