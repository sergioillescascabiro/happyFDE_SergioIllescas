import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class QuoteStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"

class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    shipper_id: Mapped[str] = mapped_column(String, ForeignKey("shippers.id"))
    origin: Mapped[str] = mapped_column(String)
    destination: Mapped[str] = mapped_column(String)
    equipment_type: Mapped[str] = mapped_column(String)
    market_rate: Mapped[float] = mapped_column(Float)
    quoted_rate: Mapped[float] = mapped_column(Float)
    status: Mapped[QuoteStatus] = mapped_column(SAEnum(QuoteStatus), default=QuoteStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    shipper: Mapped["Shipper"] = relationship("Shipper", backref="quotes")
