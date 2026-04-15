from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Shipper, Load, Carrier, Call, Negotiation, Quote
from app.models.load import LoadStatus

def get_test_db():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

def test_seed_counts():
    db = get_test_db()
    try:
        assert db.query(Shipper).count() >= 4, "Expected 4 shippers"
        assert db.query(Load).count() >= 30, "Expected 30+ loads"
        assert db.query(Quote).count() >= 30, "Expected 30+ quotes (one per load)"
        assert db.query(Carrier).count() >= 15, "Expected 15+ carriers"
        assert db.query(Call).count() >= 40, "Expected 40+ calls"
        assert db.query(Negotiation).count() >= 20, "Expected 20+ negotiations"
        assert db.query(Quote).count() >= 8, "Expected 8+ quotes"
    finally:
        db.close()

def test_load_statuses():
    db = get_test_db()
    try:
        available = db.query(Load).filter(Load.status == LoadStatus.available).count()
        covered = db.query(Load).filter(Load.status == LoadStatus.covered).count()
        delivered = db.query(Load).filter(Load.status == LoadStatus.delivered).count()
        pending = db.query(Load).filter(Load.status == LoadStatus.pending).count()
        cancelled = db.query(Load).filter(Load.status == LoadStatus.cancelled).count()
        # Allow for multiple E2E test runs covering loads between seed rebuilds
        assert available >= 8, f"Expected 8+ available loads, got {available}"
        # covered loads may transition to delivered if their delivery_datetime has passed
        assert covered + delivered >= 5, f"Expected 5+ covered/delivered loads, got covered={covered} delivered={delivered}"
        assert pending >= 2, f"Expected 2+ pending loads, got {pending}"
        assert cancelled >= 1, f"Expected 1+ cancelled loads, got {cancelled}"
    finally:
        db.close()

def test_no_rate_leakage_model():
    """Ensure max_rate and min_rate are present in DB model (they should be stored, just not exposed in API)."""
    db = get_test_db()
    try:
        load = db.query(Load).first()
        assert load is not None
        assert load.max_rate >= load.loadboard_rate, "max_rate should be >= loadboard_rate"
        assert load.min_rate < load.loadboard_rate, "min_rate should be < loadboard_rate"
    finally:
        db.close()
