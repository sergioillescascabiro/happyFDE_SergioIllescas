import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Shipper(Base):
    __tablename__ = "shippers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True)
    shipper_type: Mapped[str | None] = mapped_column(String, nullable=True) # e.g. Retail, Manufacturing
    contact_name: Mapped[str] = mapped_column(String)
    contact_email: Mapped[str] = mapped_column(String)
    contact_phone: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
