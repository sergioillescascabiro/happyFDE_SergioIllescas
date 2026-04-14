import os
import sys

sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.carrier import Carrier
from app.services.fmcsa import verify_carrier


def main():
    db = SessionLocal()
    try:
        carriers = db.query(Carrier).all()
        print(f"Syncing {len(carriers)} carriers with real FMCSA data...")

        for c in carriers:
            print(f"Verifying MC#{c.mc_number} ({c.legal_name})...", end="", flush=True)
            try:
                result = verify_carrier(c.mc_number, db)
                if result.get("legal_name") and "lookup failed" not in result["legal_name"]:
                    print(f" SUCCESS: {result['legal_name']}")
                else:
                    print(" FAILED (Not found in FMCSA)")
            except Exception as e:
                print(f" ERROR: {str(e)}")

        db.commit()
        print("\nSync complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
