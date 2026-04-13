import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, Text, JSON, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class CallDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"

class CallOutcome(str, enum.Enum):
    booked = "booked"
    rejected = "rejected"
    no_agreement = "no_agreement"
    cancelled = "cancelled"
    carrier_not_authorized = "carrier_not_authorized"
    no_loads_available = "no_loads_available"
    transferred = "transferred"
    in_progress = "in_progress"

class CallSentiment(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"

class Call(Base):
    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    carrier_id: Mapped[str | None] = mapped_column(String, ForeignKey("carriers.id"), nullable=True)
    load_id: Mapped[str | None] = mapped_column(String, ForeignKey("loads.id"), nullable=True)
    shipper_id: Mapped[str | None] = mapped_column(String, ForeignKey("shippers.id"), nullable=True)
    mc_number: Mapped[str] = mapped_column(String)
    direction: Mapped[CallDirection] = mapped_column(SAEnum(CallDirection))
    call_start: Mapped[datetime] = mapped_column(DateTime)
    call_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[CallOutcome] = mapped_column(SAEnum(CallOutcome))
    sentiment: Mapped[CallSentiment | None] = mapped_column(SAEnum(CallSentiment), nullable=True)
    transcript_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_full: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extracted_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    transferred_to_rep: Mapped[bool] = mapped_column(Boolean, default=False)
    happyrobot_call_id: Mapped[str | None] = mapped_column(String, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True)
    use_case: Mapped[str] = mapped_column(String, default="Inbound Carrier Sales")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    carrier: Mapped["Carrier"] = relationship("Carrier", backref="calls")
