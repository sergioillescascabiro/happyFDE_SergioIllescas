import uuid
from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, Text, Integer, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class LoadStatus(str, enum.Enum):
    available = "available"
    pending = "pending"
    covered = "covered"
    cancelled = "cancelled"

class Load(Base):
    __tablename__ = "loads"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    load_id: Mapped[str] = mapped_column(String, unique=True)
    shipper_id: Mapped[str] = mapped_column(String, ForeignKey("shippers.id"))
    origin: Mapped[str] = mapped_column(String)
    destination: Mapped[str] = mapped_column(String)
    origin_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    destination_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    destination_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    pickup_datetime: Mapped[datetime] = mapped_column(DateTime)
    delivery_datetime: Mapped[datetime] = mapped_column(DateTime)
    equipment_type: Mapped[str] = mapped_column(String)
    loadboard_rate: Mapped[float] = mapped_column(Float)
    max_rate: Mapped[float] = mapped_column(Float)
    min_rate: Mapped[float] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[float] = mapped_column(Float)
    commodity_type: Mapped[str] = mapped_column(String)
    num_of_pieces: Mapped[int] = mapped_column(Integer, default=1)
    miles: Mapped[float] = mapped_column(Float)
    dimensions: Mapped[str | None] = mapped_column(String, nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[LoadStatus] = mapped_column(SAEnum(LoadStatus), default=LoadStatus.available)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    shipper: Mapped["Shipper"] = relationship("Shipper", backref="loads")
