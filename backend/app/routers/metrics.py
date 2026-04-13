from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.middleware.auth import require_dashboard_token
from app.services.metrics import (
    get_overview_metrics, get_calls_over_time, get_top_lanes,
    get_equipment_distribution, get_negotiation_analysis, get_sentiment_distribution
)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/overview")
def overview(
    shipper_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    return get_overview_metrics(db, shipper_id)


@router.get("/calls-over-time")
def calls_over_time(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    return get_calls_over_time(db, days)


@router.get("/top-lanes")
def top_lanes(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    return get_top_lanes(db, limit)


@router.get("/equipment-distribution")
def equipment_distribution(
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    return get_equipment_distribution(db)


@router.get("/negotiation-analysis")
def negotiation_analysis(
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    return get_negotiation_analysis(db)


@router.get("/sentiment")
def sentiment(
    db: Session = Depends(get_db),
    _: str = Depends(require_dashboard_token),
):
    return get_sentiment_distribution(db)
