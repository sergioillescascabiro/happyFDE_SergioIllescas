from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from app.models.load import Load, LoadStatus
from app.models.call import Call, CallOutcome, CallSentiment
from app.models.negotiation import Negotiation


def get_overview_metrics(db: Session, shipper_id: str = None) -> dict:
    loads_q = db.query(Load)
    calls_q = db.query(Call)
    if shipper_id:
        loads_q = loads_q.filter(Load.shipper_id == shipper_id)
        calls_q = calls_q.filter(Call.shipper_id == shipper_id)

    loads = loads_q.all()
    calls = calls_q.all()

    total_loads = len(loads)
    active_loads = sum(1 for l in loads if l.status in (LoadStatus.pending, LoadStatus.covered))
    cargo_value = sum(l.loadboard_rate * l.miles for l in loads)

    total_calls = len(calls)
    booked_calls = sum(1 for c in calls if c.outcome == CallOutcome.booked)
    conversion_rate = round(booked_calls / total_calls * 100, 1) if total_calls > 0 else 0.0

    return {
        "total_loads": total_loads,
        "active_loads": active_loads,
        "cargo_value": round(cargo_value, 2),
        "conversion_rate": conversion_rate,
        "total_calls": total_calls,
        "booked_calls": booked_calls,
    }


def get_calls_over_time(db: Session, days: int = 30) -> list:
    since = datetime.utcnow() - timedelta(days=days)
    calls = db.query(Call).filter(Call.call_start >= since).all()

    daily: dict = {}
    for call in calls:
        day = call.call_start.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "total": 0, "booked": 0, "no_agreement": 0}
        daily[day]["total"] += 1
        if call.outcome == CallOutcome.booked:
            daily[day]["booked"] += 1
        elif call.outcome == CallOutcome.no_agreement:
            daily[day]["no_agreement"] += 1

    return sorted(daily.values(), key=lambda x: x["date"])


def get_top_lanes(db: Session, limit: int = 10) -> list:
    loads = db.query(Load).all()
    lanes: dict = {}
    for l in loads:
        key = f"{l.origin} → {l.destination}"
        if key not in lanes:
            lanes[key] = {"lane": key, "origin": l.origin, "destination": l.destination, "count": 0, "avg_rate": 0, "rates": []}
        lanes[key]["count"] += 1
        lanes[key]["rates"].append(l.loadboard_rate)

    result = []
    for v in lanes.values():
        v["avg_rate"] = round(sum(v["rates"]) / len(v["rates"]), 2)
        del v["rates"]
        result.append(v)

    return sorted(result, key=lambda x: x["count"], reverse=True)[:limit]


def get_equipment_distribution(db: Session) -> list:
    loads = db.query(Load).all()
    dist: dict = {}
    for l in loads:
        dist[l.equipment_type] = dist.get(l.equipment_type, 0) + 1
    total = len(loads)
    return [
        {"equipment_type": k, "count": v, "percentage": round(v / total * 100, 1)}
        for k, v in sorted(dist.items(), key=lambda x: -x[1])
    ]


def get_negotiation_analysis(db: Session) -> dict:
    negs = db.query(Negotiation).all()
    if not negs:
        return {"avg_rounds": 0, "avg_discount_pct": 0, "accept_rate": 0, "counter_rate": 0, "reject_rate": 0}

    from app.models.load import Load
    accept = sum(1 for n in negs if n.system_response.value == "accept")
    counter = sum(1 for n in negs if n.system_response.value == "counter")
    reject = sum(1 for n in negs if n.system_response.value == "reject")
    total = len(negs)

    # Group by call_id to get rounds per call
    call_rounds: dict = {}
    for n in negs:
        call_rounds.setdefault(n.call_id, []).append(n)
    avg_rounds = round(sum(len(v) for v in call_rounds.values()) / len(call_rounds), 2)

    return {
        "avg_rounds": avg_rounds,
        "accept_rate": round(accept / total * 100, 1),
        "counter_rate": round(counter / total * 100, 1),
        "reject_rate": round(reject / total * 100, 1),
        "total_negotiations": total,
    }


def get_sentiment_distribution(db: Session) -> dict:
    calls = db.query(Call).filter(Call.sentiment != None).all()
    dist = {"positive": 0, "neutral": 0, "negative": 0}
    for c in calls:
        if c.sentiment:
            dist[c.sentiment.value] = dist.get(c.sentiment.value, 0) + 1
    total = sum(dist.values())
    return {
        k: {"count": v, "percentage": round(v / total * 100, 1) if total > 0 else 0}
        for k, v in dist.items()
    }


def get_financial_metrics(db: Session) -> dict:
    """Executive-level financial metrics."""
    from app.models.quote import Quote, QuoteStatus

    # All accepted quotes = revenue
    accepted_quotes = db.query(Quote).filter(Quote.status == QuoteStatus.accepted).all()
    total_revenue = round(sum(q.quoted_rate for q in accepted_quotes), 2)

    # Covered and delivered loads with booked_rate set = carrier costs
    covered_loads = (
        db.query(Load)
        .filter(Load.status.in_([LoadStatus.covered, LoadStatus.delivered]))
        .filter(Load.booked_rate != None)
        .all()
    )
    total_carrier_cost = round(sum(l.booked_rate for l in covered_loads), 2)
    net_margin = round(total_revenue - total_carrier_cost, 2)

    # Average spread %: average margin_pct across loads that have it
    loads_with_margin = [l for l in covered_loads if l.margin_pct is not None]
    avg_spread_pct = (
        round(sum(l.margin_pct for l in loads_with_margin) / len(loads_with_margin), 2)
        if loads_with_margin else 0.0
    )

    # Automation rate: % of covered loads booked by AI
    total_covered = len(covered_loads)
    ai_booked = sum(1 for l in covered_loads if l.is_ai_booked)
    automation_rate = round(ai_booked / total_covered * 100, 1) if total_covered > 0 else 0.0

    # Time-to-cover efficiency: avg hours from created_at to updated_at for covered/delivered loads
    time_to_cover_hours = []
    for l in covered_loads:
        if l.created_at and l.updated_at and l.updated_at > l.created_at:
            diff = (l.updated_at - l.created_at).total_seconds() / 3600
            time_to_cover_hours.append(diff)
    avg_time_to_cover_hours = (
        round(sum(time_to_cover_hours) / len(time_to_cover_hours), 2)
        if time_to_cover_hours else 0.0
    )

    return {
        "total_revenue": total_revenue,
        "total_carrier_cost": total_carrier_cost,
        "net_margin": net_margin,
        "avg_spread_pct": avg_spread_pct,
        "automation_rate": automation_rate,
        "avg_time_to_cover_hours": avg_time_to_cover_hours,
        "covered_load_count": total_covered,
        "ai_booked_count": ai_booked,
    }
