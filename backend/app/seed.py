"""
Seed script for HappyFDE database.
Run with: cd backend && uv run python -m app.seed
"""
import uuid
import random
from datetime import datetime, timedelta
from app.database import SessionLocal, engine
from app.models import (
    Shipper, Load, Carrier, CarrierLoadHistory,
    Call, Negotiation, Quote
)
from app.models.load import LoadStatus
from app.models.carrier import CarrierStatus, CarrierSource
from app.models.call import CallDirection, CallOutcome, CallSentiment
from app.models.negotiation import NegotiationResponse
from app.models.quote import QuoteStatus
from app.database import Base

# Seed with fixed random for reproducibility
random.seed(42)

TODAY = datetime(2026, 4, 12, 12, 0, 0)


def clear_db(db):
    """Clear all tables in correct order to respect FK constraints."""
    db.query(Negotiation).delete()
    db.query(Quote).delete()
    db.query(CarrierLoadHistory).delete()
    db.query(Call).delete()
    db.query(Load).delete()
    db.query(Carrier).delete()
    db.query(Shipper).delete()
    db.commit()


def seed_shippers(db):
    shippers = [
        Shipper(
            id=str(uuid.uuid4()),
            name="Walmart Distribution",
            contact_name="James Miller",
            contact_email="james.miller@walmart-dist.com",
            contact_phone="479-555-0101",
            address="702 SW 8th St, Bentonville, AR 72716",
            is_active=True,
        ),
        Shipper(
            id=str(uuid.uuid4()),
            name="Home Depot Supply",
            contact_name="Sandra Chen",
            contact_email="sandra.chen@homedepot.com",
            contact_phone="770-555-0202",
            address="2455 Paces Ferry Rd NW, Atlanta, GA 30339",
            is_active=True,
        ),
        Shipper(
            id=str(uuid.uuid4()),
            name="AutoZone Parts",
            contact_name="Robert Davis",
            contact_email="robert.davis@autozone.com",
            contact_phone="901-555-0303",
            address="123 South Front St, Memphis, TN 38103",
            is_active=True,
        ),
        Shipper(
            id=str(uuid.uuid4()),
            name="Sysco Foods",
            contact_name="Maria Gonzalez",
            contact_email="maria.gonzalez@sysco.com",
            contact_phone="713-555-0404",
            address="1390 Enclave Pkwy, Houston, TX 77077",
            is_active=True,
        ),
    ]
    db.add_all(shippers)
    db.commit()
    return {s.name: s for s in shippers}


def make_load(load_id, shipper, origin, destination, miles, equipment, commodity, weight, status, pickup_offset_days, num_pieces=1, notes=None, ref_id=None, dimensions=None):
    # Rate logic by equipment
    rate_ranges = {
        "Dry Van": (1.65, 2.40),
        "Reefer": (2.10, 3.20),
        "Flatbed": (2.00, 3.00),
        "Step Deck": (2.20, 3.10),
        "Tanker": (2.50, 3.50),
    }
    lo, hi = rate_ranges.get(equipment, (1.50, 2.50))
    per_mile = round(random.uniform(lo, hi), 4)
    loadboard_rate = round(per_mile * miles, 2)
    max_rate = round(loadboard_rate * 1.15, 2)
    min_rate = round(loadboard_rate * 0.85, 2)

    pickup_dt = TODAY + timedelta(days=pickup_offset_days)
    delivery_dt = pickup_dt + timedelta(hours=int(miles / 55))  # ~55 mph average

    return Load(
        id=str(uuid.uuid4()),
        load_id=load_id,
        shipper_id=shipper.id,
        origin=origin,
        destination=destination,
        pickup_datetime=pickup_dt,
        delivery_datetime=delivery_dt,
        equipment_type=equipment,
        loadboard_rate=loadboard_rate,
        max_rate=max_rate,
        min_rate=min_rate,
        weight=weight,
        commodity_type=commodity,
        num_of_pieces=num_pieces,
        miles=miles,
        notes=notes,
        reference_id=ref_id or f"REF-{load_id}",
        dimensions=dimensions,
        status=status,
    )


def seed_loads(db, shippers):
    walmart = shippers["Walmart Distribution"]
    homedepot = shippers["Home Depot Supply"]
    autozone = shippers["AutoZone Parts"]
    sysco = shippers["Sysco Foods"]

    loads_data = [
        # Available loads (20)
        ("202883", walmart,   "Lincolnshire, IL",        "Ashville, OH",           410,  "Flatbed",  "Coils",              44000, LoadStatus.available, 3),
        ("202884", walmart,   "Sterling Heights, MI",    "Columbus, IN",           280,  "Dry Van",  "Auto Parts",         32000, LoadStatus.available, 5),
        ("202885", homedepot, "Chicago, IL",             "Atlanta, GA",            780,  "Dry Van",  "Electronics",        38000, LoadStatus.available, 2),
        ("202886", sysco,     "Los Angeles, CA",         "Dallas, TX",             1435, "Reefer",   "Fresh Produce",      42000, LoadStatus.available, 1),
        ("202887", walmart,   "Newark, NJ",              "Miami, FL",              1280, "Dry Van",  "Furniture",          28000, LoadStatus.available, 4),
        ("202888", homedepot, "Seattle, WA",             "Denver, CO",             1320, "Flatbed",  "Building Materials", 45000, LoadStatus.available, 6),
        ("202889", sysco,     "Houston, TX",             "Memphis, TN",            580,  "Dry Van",  "Paper Products",     35000, LoadStatus.available, 3),
        ("202890", sysco,     "Detroit, MI",             "Nashville, TN",          530,  "Reefer",   "Frozen Food",        40000, LoadStatus.available, 7),
        ("202891", homedepot, "Phoenix, AZ",             "Portland, OR",           1420, "Flatbed",  "Machinery",          43000, LoadStatus.available, 8),
        ("202892", walmart,   "Boston, MA",              "Charlotte, NC",          840,  "Dry Van",  "Textiles",           25000, LoadStatus.available, 2),
        ("202893", autozone,  "Baytown, TX",             "Robert, LA",             304,  "Tanker",   "Chemicals",          48000, LoadStatus.available, 5),
        ("202894", walmart,   "Magnolia, AR",            "Houston, TX",            318,  "Dry Van",  "Paper Products",     30000, LoadStatus.available, 9),
        ("202895", homedepot, "Villa Rica, GA",          "Hutchins, TX",           751,  "Flatbed",  "Iron Fittings",      44000, LoadStatus.available, 4),
        ("202896", sysco,     "Minneapolis, MN",         "Kansas City, MO",        440,  "Reefer",   "Pharmaceuticals",    15000, LoadStatus.available, 6),
        ("202897", homedepot, "San Francisco, CA",       "Salt Lake City, UT",     735,  "Flatbed",  "Machinery",          41000, LoadStatus.available, 10),
        ("202898", autozone,  "Memphis, TN",             "Nashville, TN",          210,  "Dry Van",  "Auto Parts",         22000, LoadStatus.available, 7),
        ("202899", walmart,   "Columbus, OH",            "Pittsburgh, PA",         185,  "Dry Van",  "Consumer Goods",     29000, LoadStatus.available, 11),
        ("202900", sysco,     "Dallas, TX",              "Oklahoma City, OK",      205,  "Reefer",   "Dairy Products",     38000, LoadStatus.available, 3),
        ("202901", homedepot, "Charlotte, NC",           "Baltimore, MD",          410,  "Flatbed",  "Steel Beams",        46000, LoadStatus.available, 12),
        ("202902", autozone,  "Portland, OR",            "Sacramento, CA",         580,  "Dry Van",  "Electronic Parts",   24000, LoadStatus.available, 8),
        # Covered loads (5)
        ("202903", walmart,   "Louisville, KY",          "Indianapolis, IN",       115,  "Dry Van",  "Packaged Goods",     27000, LoadStatus.covered,   -2),
        ("202904", sysco,     "New Orleans, LA",         "Birmingham, AL",         345,  "Reefer",   "Seafood",            20000, LoadStatus.covered,   -1),
        ("202905", homedepot, "Albuquerque, NM",         "El Paso, TX",            265,  "Flatbed",  "Construction Equip", 48000, LoadStatus.covered,   -3),
        ("202906", autozone,  "Cleveland, OH",           "Cincinnati, OH",         245,  "Dry Van",  "Auto Parts",         31000, LoadStatus.covered,   -1),
        ("202907", walmart,   "Las Vegas, NV",           "Los Angeles, CA",        270,  "Dry Van",  "Consumer Goods",     26000, LoadStatus.covered,   -2),
        # Pending loads (3)
        ("202908", sysco,     "Tampa, FL",               "Jacksonville, FL",       200,  "Reefer",   "Fresh Produce",      36000, LoadStatus.pending,   1),
        ("202909", homedepot, "Kansas City, MO",         "St. Louis, MO",          250,  "Dry Van",  "Home Improvement",   28000, LoadStatus.pending,   2),
        ("202910", walmart,   "Denver, CO",              "Salt Lake City, UT",     370,  "Flatbed",  "Lumber",             43000, LoadStatus.pending,   1),
        # Cancelled loads (2)
        ("202911", autozone,  "Richmond, VA",            "Washington, DC",         110,  "Dry Van",  "Auto Parts",         19000, LoadStatus.cancelled, -5),
        ("202912", sysco,     "Fresno, CA",              "San Diego, CA",          330,  "Reefer",   "Perishables",        41000, LoadStatus.cancelled, -3),
    ]

    loads = []
    for row in loads_data:
        l = make_load(*row)
        loads.append(l)

    db.add_all(loads)
    db.commit()
    return {l.load_id: l for l in loads}


def seed_carriers(db):
    carriers_data = [
        ("98765",   "98765",  "HR Transportation",      None,                    "(312) 555-0111", "Chicago, IL",          True,  "Satisfactory", CarrierStatus.active,     CarrierSource.tms_import),
        ("97531",   "97531",  "PP Trucking INC",         None,                    "(713) 555-0222", "Houston, TX",          True,  "Satisfactory", CarrierStatus.active,     CarrierSource.tms_import),
        ("56789",   "56789",  "HappyTruckers INC",       "HappyTruck",            "(404) 555-0333", "Atlanta, GA",          True,  "Satisfactory", CarrierStatus.active,     CarrierSource.fmcsa),
        ("13579",   "13579",  "RoboTruckers LLC",        None,                    "(214) 555-0444", "Dallas, TX",           True,  "Satisfactory", CarrierStatus.active,     CarrierSource.tms_import),
        ("1431409", "1431409","Kaskad LLC",              None,                    "(773) 555-0555", "Chicago, IL",          True,  "Satisfactory", CarrierStatus.active,     CarrierSource.fmcsa),
        ("1497140", "1497140","Kat Logistics LLC",       None,                    "(312) 555-0666", "Oak Park, IL",         False, None,           CarrierStatus.in_review,  CarrierSource.tms_import),
        ("1523171", "1523171","Transportes Xela",        None,                    "(626) 555-0777", "El Monte, CA",         True,  "Satisfactory", CarrierStatus.active,     CarrierSource.fmcsa),
        ("234567",  "234567", "Midwest Express",         "MWX",                   "(312) 555-0888", "Joliet, IL",           True,  "Satisfactory", CarrierStatus.active,     CarrierSource.tms_import),
        ("345678",  "345678", "SunBelt Carriers",        None,                    "(602) 555-0999", "Phoenix, AZ",          True,  "Conditional",  CarrierStatus.active,     CarrierSource.fmcsa),
        ("456789",  "456789", "Eagle Transport Co",      None,                    "(313) 555-1010", "Detroit, MI",          False, "Unsatisfactory",CarrierStatus.suspended, CarrierSource.manual),
        ("567890",  "567890", "Pacific Coast Freight",   "PCF",                   "(503) 555-1111", "Portland, OR",         True,  "Satisfactory", CarrierStatus.active,     CarrierSource.tms_import),
        ("678901",  "678901", "Great Plains Trucking",   None,                    "(402) 555-1212", "Omaha, NE",            True,  "Satisfactory", CarrierStatus.active,     CarrierSource.fmcsa),
        ("789012",  "789012", "Coastal Logistics",       "CoastalLog",            "(904) 555-1313", "Jacksonville, FL",     True,  "Satisfactory", CarrierStatus.active,     CarrierSource.tms_import),
        ("890123",  "890123", "Mountain West Carriers",  None,                    "(303) 555-1414", "Denver, CO",           True,  "Satisfactory", CarrierStatus.active,     CarrierSource.fmcsa),
        ("901234",  "901234", "Northeast Express",       None,                    "(617) 555-1515", "Boston, MA",           True,  "Satisfactory", CarrierStatus.active,     CarrierSource.tms_import),
        ("112233",  "112233", "Gulf Coast Transport",    None,                    "(504) 555-1616", "New Orleans, LA",      True,  "Satisfactory", CarrierStatus.active,     CarrierSource.fmcsa),
        ("223344",  "223344", "Lone Star Freight",       "LSF",                   "(210) 555-1717", "San Antonio, TX",      True,  "Conditional",  CarrierStatus.active,     CarrierSource.tms_import),
        ("334455",  "334455", "Appalachian Haulers",     None,                    "(423) 555-1818", "Knoxville, TN",        True,  "Satisfactory", CarrierStatus.inactive,   CarrierSource.manual),
    ]

    carriers = []
    for mc, dot, legal, dba, phone, addr, is_auth, safety, status, source in carriers_data:
        c = Carrier(
            id=str(uuid.uuid4()),
            mc_number=mc,
            dot_number=dot,
            legal_name=legal,
            dba_name=dba,
            phone=phone,
            physical_address=addr,
            is_authorized=is_auth,
            safety_rating=safety,
            status=status,
            source=source,
            verification_date=TODAY - timedelta(days=random.randint(10, 180)),
        )
        carriers.append(c)

    db.add_all(carriers)
    db.commit()
    return {c.mc_number: c for c in carriers}


def seed_carrier_load_history(db, carriers, loads):
    """Link carriers as 'recommended' for loads based on region/equipment matching."""
    history_entries = []

    # Map loads to carriers by equipment type and region
    equipment_carrier_map = {
        "Flatbed":  ["98765", "1431409", "234567", "345678", "890123"],
        "Dry Van":  ["97531", "13579",   "56789",  "901234", "112233"],
        "Reefer":   ["97531", "56789",   "789012", "112233", "223344"],
        "Tanker":   ["1523171", "112233", "223344", "97531", "13579"],
        "Step Deck":["98765",  "1431409","234567", "345678"],
    }

    for load_id, load in loads.items():
        equip = load.equipment_type
        carrier_mcs = equipment_carrier_map.get(equip, ["98765", "97531"])[:4]
        for mc in carrier_mcs:
            if mc not in carriers:
                continue
            carrier = carriers[mc]
            origin_region = load.origin.split(",")[-1].strip() if "," in load.origin else load.origin[:2]
            dest_region = load.destination.split(",")[-1].strip() if "," in load.destination else load.destination[:2]
            h = CarrierLoadHistory(
                id=str(uuid.uuid4()),
                carrier_id=carrier.id,
                load_id=load.id,
                origin_region=origin_region,
                destination_region=dest_region,
                equipment_type=equip,
                similar_match_count=random.randint(2, 15),
                last_service_date=TODAY - timedelta(days=random.randint(5, 120)),
            )
            history_entries.append(h)

    db.add_all(history_entries)
    db.commit()


def seed_calls_and_negotiations(db, carriers, loads):
    """Create 40-50 historical calls with realistic outcomes and negotiation data."""
    load_list = list(loads.values())
    carrier_list = list(carriers.values())
    authorized_carriers = [c for c in carrier_list if c.is_authorized and c.status == CarrierStatus.active]

    # Call distribution per spec:
    # ~15 booked, ~10 no_agreement, ~8 rejected, ~5 cancelled, ~5 carrier_not_authorized, ~5 transferred/in_progress

    call_templates = (
        [(CallOutcome.booked, CallSentiment.positive)] * 15 +
        [(CallOutcome.no_agreement, CallSentiment.neutral)] * 10 +
        [(CallOutcome.rejected, CallSentiment.negative)] * 8 +
        [(CallOutcome.cancelled, CallSentiment.neutral)] * 5 +
        [(CallOutcome.carrier_not_authorized, CallSentiment.negative)] * 5 +
        [(CallOutcome.transferred, CallSentiment.neutral)] * 3 +
        [(CallOutcome.in_progress, CallSentiment.neutral)] * 2
    )
    random.shuffle(call_templates)

    all_calls = []
    all_negotiations = []

    # Full transcripts for first 5 calls
    sample_transcripts = [
        [
            {"role": "assistant", "message": "Thank you for calling Acme Logistics, this is our automated carrier booking system. Can I get your MC number?", "timestamp": "00:00:05"},
            {"role": "caller",    "message": "Sure, it's MC 98765.", "timestamp": "00:00:12"},
            {"role": "assistant", "message": "Thank you. I found your record — HR Transportation. What load are you calling about?", "timestamp": "00:00:20"},
            {"role": "caller",    "message": "I'm looking at load 202883, the flatbed from Lincolnshire to Ashville.", "timestamp": "00:00:30"},
            {"role": "assistant", "message": "Load 202883 is available. The listed rate is around $820. What's your offer?", "timestamp": "00:00:42"},
            {"role": "caller",    "message": "I can do it for $750.", "timestamp": "00:00:48"},
            {"role": "tool_call", "message": "negotiate_load(load_id='202883', carrier_offer=750.00)", "timestamp": "00:00:49"},
            {"role": "assistant", "message": "I can meet you at $790. Does that work?", "timestamp": "00:00:55"},
            {"role": "caller",    "message": "Yeah, that works. Let's do it.", "timestamp": "00:01:02"},
            {"role": "assistant", "message": "Great, load 202883 is booked. You'll receive a rate confirmation shortly.", "timestamp": "00:01:10"},
        ],
        [
            {"role": "assistant", "message": "Acme Logistics carrier line. Please provide your MC number.", "timestamp": "00:00:03"},
            {"role": "caller",    "message": "MC 97531.", "timestamp": "00:00:08"},
            {"role": "assistant", "message": "PP Trucking INC verified. Which lane are you looking at today?", "timestamp": "00:00:15"},
            {"role": "caller",    "message": "Do you have anything going to Nashville from Detroit area?", "timestamp": "00:00:24"},
            {"role": "tool_call", "message": "search_loads(origin='Detroit, MI', destination='Nashville, TN')", "timestamp": "00:00:25"},
            {"role": "assistant", "message": "Yes, I have load 202890 — Detroit to Nashville, 530 miles, reefer, frozen food, $42000 lbs. Pickup in 7 days.", "timestamp": "00:00:35"},
            {"role": "caller",    "message": "What's the rate?", "timestamp": "00:00:40"},
            {"role": "assistant", "message": "Listed at $1,113. What can you offer?", "timestamp": "00:00:47"},
            {"role": "caller",    "message": "I need at least $1,200 for that run.", "timestamp": "00:00:55"},
            {"role": "assistant", "message": "I'm unable to meet that rate on this load. Our best is $1,113. Would you like to explore other loads?", "timestamp": "00:01:05"},
            {"role": "caller",    "message": "No thanks, I'll pass.", "timestamp": "00:01:10"},
        ],
        [
            {"role": "assistant", "message": "Acme Logistics, how can I help you?", "timestamp": "00:00:04"},
            {"role": "caller",    "message": "MC 1431409, Kaskad LLC. I want to check on a load.", "timestamp": "00:00:12"},
            {"role": "tool_call", "message": "verify_carrier(mc_number='1431409')", "timestamp": "00:00:13"},
            {"role": "assistant", "message": "Kaskad LLC verified. What lane are you interested in?", "timestamp": "00:00:20"},
            {"role": "caller",    "message": "Chicago to Atlanta, dry van.", "timestamp": "00:00:27"},
            {"role": "assistant", "message": "I have load 202885, Chicago to Atlanta, 780 miles, dry van. What's your rate?", "timestamp": "00:00:38"},
            {"role": "caller",    "message": "$1,400.", "timestamp": "00:00:44"},
            {"role": "tool_call", "message": "negotiate_load(load_id='202885', carrier_offer=1400.00)", "timestamp": "00:00:45"},
            {"role": "assistant", "message": "Accepted. Load 202885 is yours at $1,400. Confirmation incoming.", "timestamp": "00:00:52"},
        ],
        [
            {"role": "assistant", "message": "Acme Logistics carrier services. MC number please.", "timestamp": "00:00:05"},
            {"role": "caller",    "message": "456789.", "timestamp": "00:00:09"},
            {"role": "tool_call", "message": "verify_carrier(mc_number='456789')", "timestamp": "00:00:10"},
            {"role": "assistant", "message": "I'm sorry, Eagle Transport Co's authority is currently suspended. We're unable to process bookings at this time. Please contact us to resolve your compliance status.", "timestamp": "00:00:20"},
            {"role": "caller",    "message": "What? That can't be right.", "timestamp": "00:00:28"},
            {"role": "assistant", "message": "Our records show your authority was suspended. I'd recommend contacting FMCSA directly to verify your status.", "timestamp": "00:00:38"},
        ],
        [
            {"role": "assistant", "message": "Acme Logistics, this is our booking system. MC number?", "timestamp": "00:00:04"},
            {"role": "caller",    "message": "MC 13579, RoboTruckers.", "timestamp": "00:00:10"},
            {"role": "assistant", "message": "RoboTruckers LLC, verified. What can I help with?", "timestamp": "00:00:17"},
            {"role": "caller",    "message": "Looking for flatbed loads out of Villa Rica Georgia.", "timestamp": "00:00:26"},
            {"role": "tool_call", "message": "search_loads(origin='Villa Rica, GA', equipment_type='Flatbed')", "timestamp": "00:00:27"},
            {"role": "assistant", "message": "I have load 202895, Villa Rica GA to Hutchins TX, 751 miles, flatbed, iron fittings. Pickup in 4 days.", "timestamp": "00:00:38"},
            {"role": "caller",    "message": "What's the rate on that?", "timestamp": "00:00:44"},
            {"role": "assistant", "message": "Listed at $1,879. Would you like to make an offer?", "timestamp": "00:00:51"},
            {"role": "caller",    "message": "I can do $1,700.", "timestamp": "00:00:57"},
            {"role": "tool_call", "message": "negotiate_load(load_id='202895', carrier_offer=1700.00)", "timestamp": "00:00:58"},
            {"role": "assistant", "message": "Counter at $1,820. Can you meet that?", "timestamp": "00:01:05"},
            {"role": "caller",    "message": "Split the difference at $1,760?", "timestamp": "00:01:12"},
            {"role": "assistant", "message": "Deal at $1,760. Load 202895 is booked.", "timestamp": "00:01:19"},
        ],
    ]

    for i, (outcome, sentiment) in enumerate(call_templates):
        # Select carrier
        if outcome == CallOutcome.carrier_not_authorized:
            carrier = carriers.get("456789") or carrier_list[-1]  # Eagle Transport (suspended)
        else:
            carrier = random.choice(authorized_carriers)

        # Select load
        load = random.choice(load_list)

        # Timing
        call_start = TODAY - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        duration = random.randint(45, 420)
        call_end = call_start + timedelta(seconds=duration) if outcome != CallOutcome.in_progress else None

        # Summaries by outcome
        summaries = {
            CallOutcome.booked: f"Carrier {carrier.legal_name} booked load {load.load_id} from {load.origin} to {load.destination}.",
            CallOutcome.no_agreement: f"Carrier {carrier.legal_name} could not agree on rate for load {load.load_id}. Call ended without booking.",
            CallOutcome.rejected: f"Load {load.load_id} rejected. Equipment mismatch or carrier preference.",
            CallOutcome.cancelled: f"Carrier disconnected before completing booking for load {load.load_id}.",
            CallOutcome.carrier_not_authorized: f"Carrier {carrier.mc_number} has suspended authority. Call terminated.",
            CallOutcome.transferred: f"Complex case transferred to human rep for load {load.load_id}.",
            CallOutcome.in_progress: f"Call in progress. Carrier discussing load {load.load_id}.",
        }

        call = Call(
            id=str(uuid.uuid4()),
            carrier_id=carrier.id,
            load_id=load.id,
            shipper_id=load.shipper_id,
            mc_number=carrier.mc_number,
            direction=CallDirection.inbound,
            call_start=call_start,
            call_end=call_end,
            duration_seconds=duration if call_end else None,
            outcome=outcome,
            sentiment=sentiment,
            transcript_summary=summaries.get(outcome, ""),
            transcript_full=sample_transcripts[i] if i < len(sample_transcripts) else None,
            transferred_to_rep=(outcome == CallOutcome.transferred),
            happyrobot_call_id=f"HR-{random.randint(10000, 99999)}",
            phone_number=carrier.phone,
        )
        all_calls.append(call)

        # Add negotiations for booked and no_agreement calls
        if outcome in (CallOutcome.booked, CallOutcome.no_agreement) and load.miles > 0:
            rounds = random.randint(1, 3)
            loadboard = load.loadboard_rate
            carrier_start = loadboard * random.uniform(0.80, 0.92)

            for rnd in range(1, rounds + 1):
                carrier_offer = round(carrier_start * (1 + 0.03 * rnd), 2)
                carrier_offer_per_mile = round(carrier_offer / load.miles, 4)

                if rnd < rounds:
                    sys_response = NegotiationResponse.counter
                    counter = round(loadboard * random.uniform(0.95, 1.05), 2)
                    counter_per_mile = round(counter / load.miles, 4)
                elif outcome == CallOutcome.booked:
                    sys_response = NegotiationResponse.accept
                    counter = None
                    counter_per_mile = None
                else:
                    sys_response = NegotiationResponse.reject
                    counter = None
                    counter_per_mile = None

                neg = Negotiation(
                    id=str(uuid.uuid4()),
                    call_id=call.id,
                    load_id=load.id,
                    round_number=rnd,
                    carrier_offer=carrier_offer,
                    carrier_offer_per_mile=carrier_offer_per_mile,
                    system_response=sys_response,
                    counter_offer=counter,
                    counter_offer_per_mile=counter_per_mile,
                    notes=f"Round {rnd} negotiation",
                    created_at=call_start + timedelta(minutes=rnd * 2),
                )
                all_negotiations.append(neg)

    db.add_all(all_calls)
    db.commit()
    db.add_all(all_negotiations)
    db.commit()


def seed_quotes(db, shippers, loads):
    """8-10 quotes for various shippers."""
    load_list = list(loads.values())

    quotes = []
    for shipper in list(shippers.values()):
        for _ in range(2):
            load = random.choice(load_list)
            market = round(load.loadboard_rate * random.uniform(0.95, 1.10), 2)
            quoted = round(market * random.uniform(0.97, 1.03), 2)
            status = random.choice([QuoteStatus.pending, QuoteStatus.accepted, QuoteStatus.rejected,
                                     QuoteStatus.pending, QuoteStatus.accepted])
            q = Quote(
                id=str(uuid.uuid4()),
                shipper_id=shipper.id,
                origin=load.origin,
                destination=load.destination,
                equipment_type=load.equipment_type,
                market_rate=market,
                quoted_rate=quoted,
                status=status,
            )
            quotes.append(q)

    db.add_all(quotes)
    db.commit()


def main():
    db = SessionLocal()
    try:
        print("Clearing existing data...")
        clear_db(db)

        print("Seeding shippers...")
        shippers = seed_shippers(db)
        print(f"  Created {len(shippers)} shippers")

        print("Seeding loads...")
        loads = seed_loads(db, shippers)
        print(f"  Created {len(loads)} loads")

        print("Seeding carriers...")
        carriers = seed_carriers(db)
        print(f"  Created {len(carriers)} carriers")

        print("Seeding carrier load history...")
        seed_carrier_load_history(db, carriers, loads)
        print("  Done")

        print("Seeding calls and negotiations...")
        seed_calls_and_negotiations(db, carriers, loads)
        call_count = db.query(Call).count()
        neg_count = db.query(Negotiation).count()
        print(f"  Created {call_count} calls, {neg_count} negotiations")

        print("Seeding quotes...")
        seed_quotes(db, shippers, loads)
        quote_count = db.query(Quote).count()
        print(f"  Created {quote_count} quotes")

        print("\nSeed complete!")
        print(f"  Shippers:    {db.query(Shipper).count()}")
        print(f"  Loads:       {db.query(Load).count()}")
        print(f"  Carriers:    {db.query(Carrier).count()}")
        print(f"  CarrierHist: {db.query(CarrierLoadHistory).count()}")
        print(f"  Calls:       {db.query(Call).count()}")
        print(f"  Negs:        {db.query(Negotiation).count()}")
        print(f"  Quotes:      {db.query(Quote).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
