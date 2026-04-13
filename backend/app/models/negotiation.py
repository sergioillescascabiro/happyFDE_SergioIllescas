import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class NegotiationResponse(str, enum.Enum):
    accept = "accept"
    reject = "reject"
    counter = "counter"

class Negotiation(Base):
    __tablename__ = "negotiations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    call_id: Mapped[str] = mapped_column(String, ForeignKey("calls.id"))
    load_id: Mapped[str] = mapped_column(String, ForeignKey("loads.id"))
    round_number: Mapped[int] = mapped_column(Integer)
    carrier_offer: Mapped[float] = mapped_column(Float)
    carrier_offer_per_mile: Mapped[float] = mapped_column(Float)
    system_response: Mapped[NegotiationResponse] = mapped_column(SAEnum(NegotiationResponse))
    counter_offer: Mapped[float | None] = mapped_column(Float, nullable=True)
    counter_offer_per_mile: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    call: Mapped["Call"] = relationship("Call", backref="negotiations")
    load: Mapped["Load"] = relationship("Load", backref="negotiations")
