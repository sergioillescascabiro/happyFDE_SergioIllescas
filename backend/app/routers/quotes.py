from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.middleware.auth import require_dashboard_token
from app.models.quote import Quote
from app.schemas.quote import QuoteResponse

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


@router.get("", response_model=list[QuoteResponse])
def list_quotes(
    shipper_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    query = db.query(Quote)
    if shipper_id:
        query = query.filter(Quote.shipper_id == shipper_id)
    if status:
        query = query.filter(Quote.status == status)
    return query.order_by(Quote.created_at.desc()).all()
