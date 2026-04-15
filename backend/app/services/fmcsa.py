"""FMCSA carrier verification service.

Real API: GET https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}?webKey={key}

Cache logic: if carrier.verification_date is within 24h, skip re-verification.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.carrier import Carrier, CarrierSource, CarrierStatus


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
        carrier_data = data.get("content", {})
        if isinstance(carrier_data, list):
            carrier_data = carrier_data[0] if carrier_data else {}
        carrier_obj = carrier_data.get("carrier", carrier_data)
        return carrier_obj
    except:
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
    """Verify a carrier by MC number against the real FMCSA API.

    1. Check DB cache (24h TTL).
    2. Call real FMCSA API.
    3. Upsert carrier in DB.
    4. Return standardized carrier dict.
    """
    carrier = db.query(Carrier).filter(Carrier.mc_number == mc_number).first()

    # Mock mode: skip real API — MC ending in '0' is unauthorized, others authorized
    if settings.FMCSA_MOCK:
        is_authorized = not mc_number.endswith("0")
        if carrier:
            carrier.is_authorized = is_authorized
            carrier.verification_date = datetime.now(timezone.utc)
            db.commit()
            db.refresh(carrier)
            return _carrier_to_dict(carrier)
        carrier = Carrier(
            mc_number=mc_number,
            legal_name=f"Mock Carrier MC#{mc_number}",
            is_authorized=is_authorized,
            status=CarrierStatus.active if is_authorized else CarrierStatus.in_review,
            source=CarrierSource.fmcsa,
            verification_date=datetime.now(timezone.utc),
        )
        db.add(carrier)
        db.commit()
        db.refresh(carrier)
        return _carrier_to_dict(carrier)

    # Cache hit: verification_date within last 24 hours (DB stores naive UTC)
    if carrier and carrier.verification_date:
        now_naive = datetime.utcnow()
        age = now_naive - carrier.verification_date
        if age < timedelta(hours=24):
            return _carrier_to_dict(carrier)

    # Fetch from real FMCSA API
    raw = _call_fmcsa_api(mc_number)
    
    if raw is None:
        if carrier:
            return _carrier_to_dict(carrier)
        carrier = Carrier(
            mc_number=mc_number,
            legal_name=f"MC#{mc_number} (FMCSA lookup failed)",
            is_authorized=False,
            status=CarrierStatus.inactive,
            source=CarrierSource.fmcsa,
            verification_date=datetime.now(timezone.utc),
        )
        db.add(carrier)
        db.commit()
        db.refresh(carrier)
        return _carrier_to_dict(carrier)

    allowed_to_operate = raw.get("allowedToOperate", "N")
    physical_address = _build_physical_address(raw)
    is_authorized = allowed_to_operate == "Y"

    if carrier:
        carrier.legal_name = raw.get("legalName", carrier.legal_name)
        carrier.dot_number = raw.get("dotNumber", carrier.dot_number)
        carrier.is_authorized = is_authorized
        carrier.safety_rating = raw.get("safetyRating", carrier.safety_rating)
        carrier.physical_address = physical_address or carrier.physical_address
        carrier.phone = raw.get("telephone", carrier.phone)
        carrier.verification_date = datetime.now(timezone.utc)
        carrier.source = CarrierSource.fmcsa
        carrier.raw_fmcsa_data = raw
    else:
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
            verification_date=datetime.now(timezone.utc),
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

