"""Load lifecycle service — status transitions and financial calculations."""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.load import Load, LoadStatus


def refresh_delivered_status(db: Session) -> int:
    """Mark covered loads as delivered if their delivery_datetime has passed.

    Returns the count of loads updated.
    """
    now = datetime.utcnow()
    covered_loads = (
        db.query(Load)
        .filter(Load.status == LoadStatus.covered)
        .filter(Load.delivery_datetime <= now)
        .all()
    )
    updated = 0
    for load in covered_loads:
        load.status = LoadStatus.delivered
        updated += 1
    if updated:
        db.commit()
    return updated
