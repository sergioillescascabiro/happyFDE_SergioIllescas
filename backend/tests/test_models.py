from sqlalchemy import create_engine, text
from app.config import settings

def test_database_connection():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1

def test_tables_exist():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        for table in ["shippers", "loads", "carriers", "carrier_load_history", "calls", "negotiations", "quotes"]:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            assert result.fetchone() is not None, f"Table {table} missing"
