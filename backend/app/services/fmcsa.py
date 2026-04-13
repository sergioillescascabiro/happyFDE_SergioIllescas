"""FMCSA carrier verification service.

Real API: GET https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}?webKey={key}
Mock mode: FMCSA_MOCK=true returns realistic fake data (for testing).
Default: FMCSA_MOCK=false (use real API with webKey from settings).

Cache logic: if carrier.verification_date is within 24h, skip re-verification.
"""
import hashlib
from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.carrier import Carrier, CarrierSource, CarrierStatus

# Realistic fake company data for mock mode
_MOCK_COMPANIES = [
    ("Swift Freight Solutions",    "TX", "Houston",       "75201", "(832) 555-0100"),
    ("Prairie Wind Trucking",      "KS", "Wichita",       "67202", "(316) 555-0200"),
    ("Great Lakes Haulers",        "MI", "Detroit",        "48201", "(313) 555-0300"),
    ("Blue Ridge Carriers",        "VA", "Roanoke",        "24011", "(540) 555-0400"),
    ("Lone Star Transport",        "TX", "Dallas",         "75201", "(214) 555-0500"),
    ("Pacific Gateway Freight",    "CA", "Los Angeles",   "90001", "(213) 555-0600"),
    ("Rocky Mountain Express",     "CO", "Denver",         "80201", "(303) 555-0700"),
    ("Atlantic Coast Logistics",   "NC", "Charlotte",     "28201", "(704) 555-0800"),
    ("Heartland Shipping Co",      "IL", "Chicago",       "60601", "(312) 555-0900"),
    ("Cascade Trucking LLC",       "WA", "Seattle",       "98101", "(206) 555-1000"),
    ("Southern Cross Carriers",    "GA", "Atlanta",       "30301", "(404) 555-1100"),
    ("Bayou State Freight",        "LA", "New Orleans",   "70112", "(504) 555-1200"),
    ("Desert Sun Transport",       "AZ", "Phoenix",       "85001", "(602) 555-1300"),
    ("Green Mountain Hauling",     "VT", "Burlington",    "05401", "(802) 555-1400"),
    ("Ozark Trail Trucking",       "MO", "St. Louis",     "63101", "(314) 555-1500"),
]

_SAFETY_RATINGS = ["Satisfactory", "Conditional", "Satisfactory"]


def _mock_fmcsa_data(mc_number: str) -> dict:
    """Generate deterministic fake FMCSA data seeded by mc_number."""
    seed = int(hashlib.md5(mc_number.encode()).hexdigest(), 16)
    idx = seed % len(_MOCK_COMPANIES)
    rating_idx = seed % len(_SAFETY_RATINGS)

    name, state, city, zip_code, phone = _MOCK_COMPANIES[idx]
    dot_num = str(1000000 + (seed % 9000000))

    # MC numbers ending in "0" are not authorized (for testing both paths)
    allowed = "N" if mc_number.endswith("0") else "Y"

    return {
        "legalName": name,
        "dotNumber": dot_num,
        "allowedToOperate": allowed,
        "safetyRating": _SAFETY_RATINGS[rating_idx],
        "phyStreet": f"{(seed % 999) + 1} Industrial Blvd",
        "phyCity": city,
        "phyState": state,
        "phyZipcode": zip_code,
        "telephone": phone,
    }


def _call_fmcsa_api(mc_number: str) -> Optional[dict]:
    """Call real FMCSA API. Returns parsed carrier dict or None if not found."""
    url = (
        f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}"
        f"?webKey={settings.FMCSA_API_KEY}"
    )
    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        # FMCSA API wraps the carrier in content.carrier
        carrier_data = data.get("content", {})
        if isinstance(carrier_data, list):
            carrier_data = carrier_data[0] if carrier_data else {}
        carrier_obj = carrier_data.get("carrier", carrier_data)
        return carrier_obj
    except httpx.HTTPStatusError:
        return None
    except Exception:
        return None


def _build_physical_address(raw: dict) -> str:
    parts = [
        raw.get("phyStreet", ""),
        raw.get("phyCity", ""),
        raw.get("phyState", ""),
        raw.get("phyZipcode", ""),
    ]
    return ", ".join(p for p in parts if p)


def verify_carrier(mc_number: str, db: Session) -> dict:
    """Verify a carrier by MC number.

    1. Check DB cache (24h TTL).
    2. If FMCSA_MOCK=True, use mock data.
    3. Otherwise call real FMCSA API.
    4. Upsert carrier in DB.
    5. Return standardized carrier dict.
    """
    carrier = db.query(Carrier).filter(Carrier.mc_number == mc_number).first()

    # Cache hit: verification_date within last 24 hours
    if carrier and carrier.verification_date:
        age = datetime.utcnow() - carrier.verification_date
        if age < timedelta(hours=24):
            return _carrier_to_dict(carrier)

    # Fetch from FMCSA (mock or real)
    if settings.FMCSA_MOCK:
        raw = _mock_fmcsa_data(mc_number)
    else:
        raw = _call_fmcsa_api(mc_number)
        if raw is None:
            # Carrier not found in FMCSA; return minimal record if we have one in DB
            if carrier:
                return _carrier_to_dict(carrier)
            # Create placeholder record
            carrier = Carrier(
                mc_number=mc_number,
                legal_name=f"MC#{mc_number} (FMCSA lookup failed)",
                is_authorized=False,
                status=CarrierStatus.inactive,
                source=CarrierSource.fmcsa,
                verification_date=datetime.utcnow(),
            )
            db.add(carrier)
            db.commit()
            db.refresh(carrier)
            return _carrier_to_dict(carrier)

    allowed_to_operate = raw.get("allowedToOperate", "N")
    physical_address = _build_physical_address(raw)

    is_authorized = allowed_to_operate == "Y"

    if carrier:
        # Update existing record
        carrier.legal_name = raw.get("legalName", carrier.legal_name)
        carrier.dot_number = raw.get("dotNumber", carrier.dot_number)
        carrier.is_authorized = is_authorized
        carrier.safety_rating = raw.get("safetyRating", carrier.safety_rating)
        carrier.physical_address = physical_address or carrier.physical_address
        carrier.phone = raw.get("telephone", carrier.phone)
        carrier.verification_date = datetime.utcnow()
        carrier.source = CarrierSource.fmcsa
        carrier.raw_fmcsa_data = raw
    else:
        # Create new record
        carrier = Carrier(
            mc_number=mc_number,
            dot_number=raw.get("dotNumber"),
            legal_name=raw.get("legalName", f"MC#{mc_number}"),
            phone=raw.get("telephone"),
            physical_address=physical_address,
            is_authorized=is_authorized,
            safety_rating=raw.get("safetyRating"),
            status=CarrierStatus.active if is_authorized else CarrierStatus.in_review,
            source=CarrierSource.fmcsa,
            verification_date=datetime.utcnow(),
            raw_fmcsa_data=raw,
        )
        db.add(carrier)

    db.commit()
    db.refresh(carrier)
    return _carrier_to_dict(carrier)


def _carrier_to_dict(carrier: Carrier) -> dict:
    return {
        "id": carrier.id,
        "mc_number": carrier.mc_number,
        "dot_number": carrier.dot_number,
        "legal_name": carrier.legal_name,
        "phone": carrier.phone,
        "physical_address": carrier.physical_address,
        "is_authorized": carrier.is_authorized,
        "safety_rating": carrier.safety_rating,
        "status": carrier.status.value if hasattr(carrier.status, "value") else carrier.status,
        "verification_date": carrier.verification_date,
        "source": carrier.source.value if hasattr(carrier.source, "value") else carrier.source,
    }
