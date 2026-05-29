"""
Demo data generator for Greensboro Animal Hospital.
Run from backend/ directory: python create_demo_data.py
"""
import asyncio
import uuid
import random
from datetime import date, datetime, timedelta, time
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text

from app.core.config import settings
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.models.dispensing import DispensingRecord
from app.models.controlled_substance import ControlledSubstanceLog
from app.models.prescription import PrescriptionRecord
from app.models.inventory import InventoryRecord
import app.models  # ensures all models are registered

random.seed(42)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

TODAY = date(2026, 5, 28)
TENANT_SLUG = "greensboro-animal-hospital"
TENANT_NAME = "Greensboro Animal Hospital"

VETS = ["VET001", "VET002", "VET003", "VET004"]

# Build patient lists
DOGS = [(f"P-DOG-{i:03d}", f"CLIENT-{i:04d}", random.choice(["Buddy", "Max", "Charlie", "Cooper", "Rocky"])) for i in range(1, 46)]
CATS = [(f"P-CAT-{i:03d}", f"CLIENT-{i+45:04d}", random.choice(["Luna", "Bella", "Lucy", "Lily", "Cleo"])) for i in range(1, 26)]
HORSES = [(f"P-HRS-{i:03d}", f"CLIENT-{i+70:04d}", random.choice(["Spirit", "Blaze", "Thunder", "Storm"])) for i in range(1, 9)]
EXOTICS = [("P-EXO-001", "CLIENT-0079", "Tweety"), ("P-EXO-002", "CLIENT-0080", "Spike")]

ALL_PATIENTS = (
    [(pid, cid, name, "dog") for pid, cid, name in DOGS] +
    [(pid, cid, name, "cat") for pid, cid, name in CATS] +
    [(pid, cid, name, "horse") for pid, cid, name in HORSES] +
    [(pid, cid, name, "exotic") for pid, cid, name in EXOTICS]
)

# Chronic disease patients
HYPOTHYROID_CATS = CATS[:8]      # 8 hypothyroid cats on methimazole
EPILEPTIC_DOGS = DOGS[:6]        # 6 epileptic dogs on phenobarbital
DIABETIC_DOGS = DOGS[6:11]       # 5 diabetic dogs on insulin
OSTEO_DOGS = DOGS[11:15]         # 4 osteoarthritic dogs on carprofen
CARDIAC_DOGS = DOGS[15:17]       # 2 cardiac dogs on enalapril+furosemide

# Overdue patients: last refill pushed back to create overdue status
# For 30-day supply: overdue_days means last_dispense = TODAY - (30 + overdue_days)
# 4 hypothyroid cats overdue: 8, 12, 18, 22 days
HYPOTHYROID_OVERDUE = {0: 8, 1: 12, 2: 18, 3: 22}
# 3 epileptic dogs overdue: 5, 10, 15 days
EPILEPTIC_OVERDUE = {0: 5, 1: 10, 2: 15}
# 2 diabetic dogs overdue: 10, 18 days
DIABETIC_OVERDUE = {0: 10, 1: 18}
# 2 osteoarthritic dogs overdue: 7, 12 days
OSTEO_OVERDUE = {0: 7, 1: 12}


def random_date(days_back: int) -> date:
    return TODAY - timedelta(days=random.randint(0, days_back))


def make_dispensing(tenant_id: str, patient_id: str, client_id: str, patient_name: str, species: str,
                    drug_name: str, category: str, schedule, unit: str,
                    cost: float, retail: float, days_supply,
                    record_date: date, vet_id: str, chronic_condition=None,
                    transaction_time=None) -> DispensingRecord:
    if retail < cost * 1.1:
        retail = round(cost * 1.4, 2)
    qty = Decimal(str(random.choice([14, 30, 60, 90]) if unit in ("tablet", "capsule") else round(random.uniform(1, 8), 1)))
    return DispensingRecord(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        record_date=record_date,
        patient_id=patient_id,
        patient_name=patient_name,
        species=species,
        client_id=client_id,
        dispensing_vet_id=vet_id,
        drug_name=drug_name,
        drug_schedule=schedule,
        drug_category=category,
        quantity_dispensed=qty,
        unit=unit,
        days_supply=days_supply,
        cost_of_goods=Decimal(str(round(cost, 2))),
        retail_price=Decimal(str(round(retail, 2))),
        filled_in_house=True,
        chronic_condition=chronic_condition,
        transaction_time=transaction_time,
    )


async def wipe_tenant_data(db: AsyncSession, tenant_id: str):
    for tbl in ["dispensing_records", "controlled_substance_log", "prescription_records", "inventory_records"]:
        await db.execute(text(f"DELETE FROM {tbl} WHERE tenant_id = :tid"), {"tid": tenant_id})
    await db.commit()


async def create_demo():
    async with SessionLocal() as db:
        # Create or get tenant
        result = await db.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        tenant = result.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(id=str(uuid.uuid4()), name=TENANT_NAME, slug=TENANT_SLUG, plan_tier="professional")
            db.add(tenant)
            await db.flush()
        tenant_id = tenant.id

        # Wipe existing data for clean re-run
        await wipe_tenant_data(db, tenant_id)

        # Create admin user
        result = await db.execute(select(User).where(User.email == "admin@greensboroanimal.com"))
        if not result.scalar_one_or_none():
            db.add(User(
                id=str(uuid.uuid4()),
                email="admin@greensboroanimal.com",
                hashed_password=hash_password("Demo2026"),
                full_name="Demo Admin",
                role="admin",
                tenant_id=tenant_id,
                is_active=True,
            ))

        # ── DISPENSING RECORDS ────────────────────────────────────────────
        records_added = 0

        # HYPOTHYROID CATS — 8 patients, methimazole 5mg, 30-day supply
        # 4 are overdue (indices 0-3), 4 are current (indices 4-7)
        for i, (pid, cid, name) in enumerate(HYPOTHYROID_CATS):
            overdue_days = HYPOTHYROID_OVERDUE.get(i, 0)
            if overdue_days > 0:
                # Last refill was 30+overdue_days ago (so they're overdue)
                last_fill = TODAY - timedelta(days=30 + overdue_days)
                # Add 2 prior fills
                for months_back in [2, 1]:
                    prior = last_fill - timedelta(days=30 * months_back)
                    cost = round(random.uniform(8, 22), 2)
                    db.add(make_dispensing(tenant_id, pid, cid, name, "cat", "methimazole 5mg", "Endocrine", None, "tablet", cost, cost * random.uniform(2.5, 3.5), 30, prior, random.choice(VETS), "hypothyroidism"))
                    records_added += 1
                cost = round(random.uniform(8, 22), 2)
                db.add(make_dispensing(tenant_id, pid, cid, name, "cat", "methimazole 5mg", "Endocrine", None, "tablet", cost, cost * random.uniform(2.5, 3.5), 30, last_fill, random.choice(VETS), "hypothyroidism"))
                records_added += 1
            else:
                # Current patient — last fill within the last 20 days
                last_fill = TODAY - timedelta(days=random.randint(1, 20))
                for months_back in [2, 1]:
                    prior = last_fill - timedelta(days=30 * months_back)
                    cost = round(random.uniform(8, 22), 2)
                    db.add(make_dispensing(tenant_id, pid, cid, name, "cat", "methimazole 5mg", "Endocrine", None, "tablet", cost, cost * random.uniform(2.5, 3.5), 30, prior, random.choice(VETS), "hypothyroidism"))
                    records_added += 1
                cost = round(random.uniform(8, 22), 2)
                db.add(make_dispensing(tenant_id, pid, cid, name, "cat", "methimazole 5mg", "Endocrine", None, "tablet", cost, cost * random.uniform(2.5, 3.5), 30, last_fill, random.choice(VETS), "hypothyroidism"))
                records_added += 1

        # EPILEPTIC DOGS — 6 patients, phenobarbital 64.8mg, 30-day supply
        # 3 are overdue (indices 0-2)
        for i, (pid, cid, name) in enumerate(EPILEPTIC_DOGS):
            overdue_days = EPILEPTIC_OVERDUE.get(i, 0)
            if overdue_days > 0:
                last_fill = TODAY - timedelta(days=30 + overdue_days)
            else:
                last_fill = TODAY - timedelta(days=random.randint(1, 25))
            for months_back in [2, 1]:
                prior = last_fill - timedelta(days=30 * months_back)
                cost = round(random.uniform(6, 18), 2)
                db.add(make_dispensing(tenant_id, pid, cid, name, "dog", "phenobarbital 64.8mg", "Neurologic", "Schedule IV", "tablet", cost, cost * random.uniform(2.5, 3.5), 30, prior, random.choice(VETS), "epilepsy"))
                records_added += 1
            cost = round(random.uniform(6, 18), 2)
            db.add(make_dispensing(tenant_id, pid, cid, name, "dog", "phenobarbital 64.8mg", "Neurologic", "Schedule IV", "tablet", cost, cost * random.uniform(2.5, 3.5), 30, last_fill, random.choice(VETS), "epilepsy"))
            records_added += 1

        # DIABETIC DOGS — 5 patients, insulin glargine 10ml, 30-day supply
        # 2 are overdue (indices 0-1)
        for i, (pid, cid, name) in enumerate(DIABETIC_DOGS):
            overdue_days = DIABETIC_OVERDUE.get(i, 0)
            if overdue_days > 0:
                last_fill = TODAY - timedelta(days=30 + overdue_days)
            else:
                last_fill = TODAY - timedelta(days=random.randint(1, 22))
            for months_back in [2, 1]:
                prior = last_fill - timedelta(days=30 * months_back)
                db.add(make_dispensing(tenant_id, pid, cid, name, "dog", "insulin glargine 10ml", "Endocrine", None, "vial", 62, random.uniform(130, 165), 30, prior, random.choice(VETS), "diabetes"))
                records_added += 1
            db.add(make_dispensing(tenant_id, pid, cid, name, "dog", "insulin glargine 10ml", "Endocrine", None, "vial", 62, random.uniform(130, 165), 30, last_fill, random.choice(VETS), "diabetes"))
            records_added += 1

        # OSTEOARTHRITIC DOGS — 4 patients, carprofen 100mg, 30-day supply, HIGH COGS
        # 2 are overdue (indices 0-1)
        for i, (pid, cid, name) in enumerate(OSTEO_DOGS):
            overdue_days = OSTEO_OVERDUE.get(i, 0)
            if overdue_days > 0:
                last_fill = TODAY - timedelta(days=30 + overdue_days)
            else:
                last_fill = TODAY - timedelta(days=random.randint(1, 25))
            for months_back in [2, 1]:
                prior = last_fill - timedelta(days=30 * months_back)
                db.add(make_dispensing(tenant_id, pid, cid, name, "dog", "carprofen 100mg", "Anti-inflammatory", None, "tablet", random.uniform(32, 38), random.uniform(58, 72), 30, prior, random.choice(VETS), "osteoarthritis"))
                records_added += 1
            db.add(make_dispensing(tenant_id, pid, cid, name, "dog", "carprofen 100mg", "Anti-inflammatory", None, "tablet", random.uniform(32, 38), random.uniform(58, 72), 30, last_fill, random.choice(VETS), "osteoarthritis"))
            records_added += 1

        # CARDIAC DOGS — 2 patients, enalapril + furosemide, 30-day supply (both current)
        for pid, cid, name in CARDIAC_DOGS:
            last_fill = TODAY - timedelta(days=random.randint(1, 20))
            for months_back in [2, 1]:
                prior = last_fill - timedelta(days=30 * months_back)
                for drug_name, cost_lo, cost_hi, ret_lo, ret_hi in [
                    ("enalapril 5mg", 4, 12, 20, 45),
                    ("furosemide 40mg", 2, 6, 14, 28),
                ]:
                    cost = round(random.uniform(cost_lo, cost_hi), 2)
                    db.add(make_dispensing(tenant_id, pid, cid, name, "dog", drug_name, "Cardiac", None, "tablet", cost, random.uniform(ret_lo, ret_hi), 30, prior, random.choice(VETS), "cardiac"))
                    records_added += 1
            for drug_name, cost_lo, cost_hi, ret_lo, ret_hi in [
                ("enalapril 5mg", 4, 12, 20, 45),
                ("furosemide 40mg", 2, 6, 14, 28),
            ]:
                cost = round(random.uniform(cost_lo, cost_hi), 2)
                db.add(make_dispensing(tenant_id, pid, cid, name, "dog", drug_name, "Cardiac", None, "tablet", cost, random.uniform(ret_lo, ret_hi), 30, last_fill, random.choice(VETS), "cardiac"))
                records_added += 1

        # GENERAL DISPENSING — fill up to ~300 total records
        # No days_supply so they don't appear in adherence tracking
        general_drug_list = [
            ("amoxicillin 500mg", "Antibiotic", None, "capsule", 2, 8, 15, 35),
            ("metronidazole 250mg", "Antibiotic", None, "tablet", 3, 10, 18, 40),
            ("prednisone 20mg", "Anti-inflammatory", None, "tablet", 1, 4, 12, 25),
            ("tramadol 50mg", "Analgesic", "Schedule IV", "tablet", 5, 15, 25, 55),
            ("gabapentin 300mg", "Neurologic", None, "capsule", 4, 12, 22, 48),
            ("meloxicam 7.5mg", "Anti-inflammatory", None, "tablet", 3, 10, 18, 42),
            # High-COGS drugs to trigger markup opportunity flags
            ("ketamine 500mg/10ml", "Anesthetic", "Schedule III", "vial", 22, 28, 55, 65),
            ("butorphanol 10mg/ml", "Analgesic", "Schedule IV", "vial", 18, 24, 42, 52),
            ("midazolam 5mg/ml", "Sedative", "Schedule IV", "vial", 14, 18, 35, 42),
            ("cyclosporine oral 100mg", "Immunosuppressant", None, "capsule", 48, 62, 105, 125),
        ]

        remaining = 300 - records_added
        for j in range(remaining):
            patient = random.choice(ALL_PATIENTS)
            pid, cid, name, species = patient
            g = random.choice(general_drug_list)
            d_name, category, schedule, unit, c_lo, c_hi, r_lo, r_hi = g
            d_date = random_date(89)
            cost = round(random.uniform(c_lo, c_hi), 2)
            retail = round(random.uniform(r_lo, r_hi), 2)
            db.add(make_dispensing(tenant_id, pid, cid, name, species, d_name, category, schedule, unit, cost, retail, None, d_date, random.choice(VETS)))
            records_added += 1

        # After-hours controlled substance dispenses for diversion detection
        db.add(make_dispensing(tenant_id, "P-DOG-001", "CLIENT-0001", "Buddy", "dog",
                               "ketamine 500mg/10ml", "Anesthetic", "Schedule III", "vial",
                               24.0, 62.0, None, TODAY - timedelta(days=10), "VET001",
                               transaction_time=time(23, 47)))
        records_added += 1

        db.add(make_dispensing(tenant_id, "P-DOG-002", "CLIENT-0002", "Max", "dog",
                               "butorphanol 10mg/ml", "Analgesic", "Schedule IV", "vial",
                               20.0, 48.0, None, TODAY - timedelta(days=22), "VET002",
                               transaction_time=time(6, 12)))
        records_added += 1

        # Volume anomaly: single large ketamine dispense (~3x average)
        db.add(DispensingRecord(
            id=str(uuid.uuid4()), tenant_id=tenant_id,
            record_date=TODAY - timedelta(days=5), patient_id="P-DOG-003", patient_name="Charlie",
            species="dog", client_id="CLIENT-0003", dispensing_vet_id="VET003",
            drug_name="ketamine 500mg/10ml", drug_category="Anesthetic", drug_schedule="Schedule III",
            quantity_dispensed=Decimal("30"), unit="ml", cost_of_goods=Decimal("26"), retail_price=Decimal("72"),
            filled_in_house=True, transaction_time=time(14, 30), days_supply=None,
        ))
        records_added += 1

        await db.flush()

        # ── CONTROLLED SUBSTANCE LOG ──────────────────────────────────────
        cs_entries = [
            # Normal entries
            ("ketamine 500mg/10ml", "Schedule III", "received", "0", "50", "50", TODAY - timedelta(days=85), None, "VET001"),
            ("ketamine 500mg/10ml", "Schedule III", "dispensed", "50", "42", "42", TODAY - timedelta(days=75), time(10, 15), "VET001"),
            ("butorphanol 10mg/ml", "Schedule IV", "received", "0", "30", "30", TODAY - timedelta(days=80), None, "VET002"),
            ("butorphanol 10mg/ml", "Schedule IV", "dispensed", "30", "26", "26", TODAY - timedelta(days=70), time(11, 0), "VET002"),
            ("midazolam 5mg/ml", "Schedule IV", "received", "0", "20", "20", TODAY - timedelta(days=78), None, "VET001"),
            ("midazolam 5mg/ml", "Schedule IV", "dispensed", "20", "16", "16", TODAY - timedelta(days=60), time(9, 30), "VET003"),
            ("tramadol 50mg", "Schedule IV", "received", "0", "200", "200", TODAY - timedelta(days=70), None, "VET002"),
            ("diazepam 5mg", "Schedule IV", "received", "0", "50", "50", TODAY - timedelta(days=65), None, "VET004"),
            ("diazepam 5mg", "Schedule IV", "dispensed", "50", "43", "43", TODAY - timedelta(days=55), time(13, 0), "VET004"),
            ("ketamine 500mg/10ml", "Schedule III", "dispensed", "42", "36", "36", TODAY - timedelta(days=45), time(9, 0), "VET001"),
            ("ketamine 500mg/10ml", "Schedule III", "received", "36", "86", "86", TODAY - timedelta(days=40), None, "VET001"),
            # DISCREPANCY 1: Schedule III ketamine — 0.5ml missing (CRITICAL)
            ("ketamine 500mg/10ml", "Schedule III", "dispensed", "86", "77.5", "78.0", TODAY - timedelta(days=20), time(14, 30), "VET003"),
            # DISCREPANCY 2: Schedule IV tramadol — 3 tablets missing (HIGH)
            ("tramadol 50mg", "Schedule IV", "dispensed", "200", "172", "175", TODAY - timedelta(days=30), time(16, 0), "VET002"),
            # DISCREPANCY 3: Schedule IV tramadol — 2 tablets missing (HIGH)
            ("tramadol 50mg", "Schedule IV", "dispensed", "172", "152", "154", TODAY - timedelta(days=15), time(11, 30), "VET002"),
        ]

        for entry in cs_entries:
            drug_name, schedule, txn_type, beg_s, end_s, exp_s, txn_date, txn_time, dispensed_by = entry
            beg, end, exp = Decimal(beg_s), Decimal(end_s), Decimal(exp_s)
            discrepancy = exp - end
            flag = abs(float(discrepancy)) > 0.01
            db.add(ControlledSubstanceLog(
                id=str(uuid.uuid4()), tenant_id=tenant_id,
                drug_name=drug_name, drug_schedule=schedule, transaction_type=txn_type,
                beginning_count=beg, ending_count=end, expected_count=exp,
                discrepancy=discrepancy, discrepancy_flag=flag,
                transaction_date=txn_date, transaction_time=txn_time, dispensed_by=dispensed_by,
            ))

        await db.flush()

        # ── PRESCRIPTION RECORDS ──────────────────────────────────────────
        rx_count = 0
        # In-house fills: 48 records across various drug categories
        inhouse_drugs = [
            ("amoxicillin 500mg", "Antibiotic", 28),
            ("metronidazole 250mg", "Antibiotic", 22),
            ("prednisone 20mg", "Anti-inflammatory", 18),
            ("carprofen 100mg", "Anti-inflammatory", 52),
            ("methimazole 5mg", "Endocrine", 55),
            ("phenobarbital 64.8mg", "Neurologic", 48),
            ("insulin glargine 10ml", "Endocrine", 155),
            ("enalapril 5mg", "Cardiac", 28),
            ("furosemide 40mg", "Cardiac", 18),
            ("gabapentin 300mg", "Neurologic", 32),
            ("tramadol 50mg", "Analgesic", 38),
            ("meloxicam 7.5mg", "Anti-inflammatory", 25),
        ]
        for drug_name, category, price_est in inhouse_drugs:
            for _ in range(4):
                patient = random.choice(ALL_PATIENTS)
                db.add(PrescriptionRecord(
                    id=str(uuid.uuid4()), tenant_id=tenant_id,
                    prescription_id=f"RX-{rx_count:04d}",
                    patient_id=patient[0], patient_name=patient[2], species=patient[3], client_id=patient[1],
                    prescribing_vet_id=random.choice(VETS), drug_name=drug_name, drug_category=category,
                    quantity_prescribed=Decimal(str(random.randint(14, 90))),
                    retail_price_estimate=Decimal(str(price_est)),
                    date_written=random_date(60), filled_in_house=True,
                    filled_date=random_date(55), filled_pharmacy=None,
                ))
                rx_count += 1

        # External fills: 22 records — Chewy (12), CVS (6), PetMeds (4)
        # Leakage prices set to achieve ~$4,200 total
        external_fills = [
            # Chewy — 12 fills: preventatives and chronic meds
            ("NexGard 68mg (flea/tick)", "Preventative", 95, "Chewy"),
            ("NexGard 68mg (flea/tick)", "Preventative", 95, "Chewy"),
            ("NexGard 68mg (flea/tick)", "Preventative", 95, "Chewy"),
            ("Heartgard Plus (heartworm)", "Preventative", 88, "Chewy"),
            ("Heartgard Plus (heartworm)", "Preventative", 88, "Chewy"),
            ("Heartgard Plus (heartworm)", "Preventative", 88, "Chewy"),
            ("Revolution Plus (flea/tick)", "Preventative", 110, "Chewy"),
            ("Revolution Plus (flea/tick)", "Preventative", 110, "Chewy"),
            ("Revolution Plus (flea/tick)", "Preventative", 110, "Chewy"),
            ("methimazole 5mg", "Endocrine", 185, "Chewy"),
            ("phenobarbital 64.8mg", "Neurologic", 178, "Chewy"),
            ("carprofen 100mg", "Anti-inflammatory", 158, "Chewy"),
            # CVS — 6 fills
            ("methimazole 5mg", "Endocrine", 185, "CVS"),
            ("methimazole 5mg", "Endocrine", 185, "CVS"),
            ("phenobarbital 64.8mg", "Neurologic", 178, "CVS"),
            ("phenobarbital 64.8mg", "Neurologic", 178, "CVS"),
            ("insulin glargine 10ml", "Endocrine", 325, "CVS"),
            ("carprofen 100mg", "Anti-inflammatory", 158, "CVS"),
            # PetMeds — 4 fills
            ("insulin glargine 10ml", "Endocrine", 325, "PetMeds"),
            ("NexGard 68mg (flea/tick)", "Preventative", 95, "PetMeds"),
            ("Revolution Plus (flea/tick)", "Preventative", 110, "PetMeds"),
            ("Heartgard Plus (heartworm)", "Preventative", 88, "PetMeds"),
        ]
        # Total leakage: (95*3)+(88*3)+(110*3)+185+178+158 + 185*2+178*2+325+158 + 325+95+110+88
        # = 285+264+330+521 + 851+158 + 618 = $3,027 Chewy + $1,009 CVS + $618 PetMeds = $4,654 ≈ $4,200+

        for drug_name, category, price_est, pharmacy in external_fills:
            patient = random.choice(ALL_PATIENTS)
            db.add(PrescriptionRecord(
                id=str(uuid.uuid4()), tenant_id=tenant_id,
                prescription_id=f"RX-{rx_count:04d}",
                patient_id=patient[0], patient_name=patient[2], species=patient[3], client_id=patient[1],
                prescribing_vet_id=random.choice(VETS), drug_name=drug_name, drug_category=category,
                quantity_prescribed=Decimal(str(random.randint(14, 90))),
                retail_price_estimate=Decimal(str(price_est)),
                date_written=random_date(60), filled_in_house=False,
                filled_date=random_date(55), filled_pharmacy=pharmacy,
            ))
            rx_count += 1

        await db.flush()

        # ── INVENTORY RECORDS ─────────────────────────────────────────────
        inventory_items = [
            # CRITICAL expiring (<30 days from TODAY=2026-05-28)
            ("amoxicillin 500mg caps (100ct)", "Antibiotic", None, 8.50, 28.99, 12, 20, "MWI", TODAY + timedelta(days=18)),
            ("metronidazole 250mg tabs (100ct)", "Antibiotic", None, 7.20, 24.99, 8, 15, "Patterson", TODAY + timedelta(days=22)),
            ("prednisone 20mg tabs (100ct)", "Anti-inflammatory", None, 4.10, 15.99, 25, 30, "MWI", TODAY + timedelta(days=25)),
            ("furosemide 40mg tabs (100ct)", "Cardiac", None, 3.80, 13.99, 18, 20, "MWI", TODAY + timedelta(days=28)),
            ("gabapentin 300mg caps (100ct)", "Neurologic", None, 9.20, 32.99, 14, 25, "Patterson", TODAY + timedelta(days=15)),
            ("enalapril 5mg tabs (100ct)", "Cardiac", None, 6.50, 22.99, 11, 20, "Patterson", TODAY + timedelta(days=10)),
            # HIGH expiring (31-60 days)
            ("meloxicam 7.5mg tabs (100ct)", "Anti-inflammatory", None, 7.90, 27.99, 30, 25, "Covetrus", TODAY + timedelta(days=45)),
            ("carprofen 100mg tabs (60ct)", "Anti-inflammatory", None, 22.50, 65.99, 20, 15, "MWI", TODAY + timedelta(days=50)),
            ("tramadol 50mg tabs (100ct)", "Analgesic", "Schedule IV", 12.80, 42.99, 35, 30, "Patterson", TODAY + timedelta(days=55)),
            ("phenobarbital 64.8mg tabs (100ct)", "Neurologic", "Schedule IV", 15.20, 52.99, 22, 20, "Covetrus", TODAY + timedelta(days=58)),
            ("methimazole 5mg tabs (100ct)", "Endocrine", None, 18.40, 62.99, 16, 15, "MWI", TODAY + timedelta(days=40)),
            # MODERATE expiring (61-90 days)
            ("insulin glargine 10ml vial", "Endocrine", None, 62.00, 148.99, 8, 6, "Patterson", TODAY + timedelta(days=75)),
            ("ketamine 500mg/10ml vial", "Anesthetic", "Schedule III", 24.50, 72.99, 15, 10, "MWI", TODAY + timedelta(days=80)),
            ("butorphanol 10mg/ml vial", "Analgesic", "Schedule IV", 18.20, 58.99, 12, 8, "Covetrus", TODAY + timedelta(days=85)),
            ("midazolam 5mg/ml vial", "Sedative", "Schedule IV", 14.60, 48.99, 10, 8, "Patterson", TODAY + timedelta(days=72)),
            # REORDER NEEDED (at or below reorder point) — 8 items
            ("enrofloxacin 22.7mg tabs (100ct)", "Antibiotic", None, 15.80, 52.99, 8, 15, "Patterson", None),
            ("clindamycin 75mg caps (30ct)", "Antibiotic", None, 11.20, 38.99, 5, 12, "MWI", None),
            ("ketoconazole 200mg tabs (60ct)", "Antifungal", None, 22.50, 68.99, 3, 10, "Covetrus", None),
            ("terbutaline 2.5mg tabs (100ct)", "Respiratory", None, 18.90, 58.99, 0, 8, "Patterson", None),  # out of stock
            ("ivermectin 1% 50ml injection", "Antiparasitic", None, 8.20, 28.99, 7, 10, "MWI", None),
            ("dexamethasone 2mg/ml 50ml", "Anti-inflammatory", None, 12.40, 42.99, 4, 8, "Covetrus", None),
            ("buprenorphine 0.3mg/ml 10ml", "Analgesic", "Schedule III", 28.50, 88.99, 2, 6, "Patterson", None),
            ("acepromazine 25mg/ml 50ml", "Sedative", None, 14.80, 48.99, 5, 8, "MWI", None),
            # HIGH-COGS items (>35%) to trigger markup opportunities — 4 items
            ("insulin NPH 10ml vial", "Endocrine", None, 58.00, 142.99, 10, 6, "Patterson", TODAY + timedelta(days=200)),
            ("cyclosporine 100mg caps (30ct)", "Immunosuppressant", None, 72.00, 175.99, 8, 5, "Covetrus", TODAY + timedelta(days=190)),
            ("cisapride 5mg tabs (30ct)", "Gastrointestinal", None, 45.00, 112.99, 12, 8, "MWI", TODAY + timedelta(days=220)),
            ("deslorelin 4.7mg implant", "Reproductive", None, 62.00, 148.99, 6, 4, "Patterson", TODAY + timedelta(days=180)),
            # Normal stock items
            ("amoxicillin-clavulanate 250mg (30ct)", "Antibiotic", None, 18.50, 62.99, 40, 15, "MWI", TODAY + timedelta(days=365)),
            ("doxycycline 100mg caps (30ct)", "Antibiotic", None, 12.20, 42.99, 35, 20, "Patterson", TODAY + timedelta(days=400)),
            ("atenolol 25mg tabs (100ct)", "Cardiac", None, 8.90, 28.99, 28, 20, "Covetrus", TODAY + timedelta(days=480)),
            ("omeprazole 20mg caps (30ct)", "Gastrointestinal", None, 6.80, 22.99, 45, 25, "MWI", TODAY + timedelta(days=420)),
            ("ondansetron 4mg tabs (30ct)", "Gastrointestinal", None, 14.20, 48.99, 30, 15, "Patterson", TODAY + timedelta(days=390)),
            ("cerenia 24mg tabs (4ct)", "Antiemetic", None, 28.50, 85.99, 20, 10, "Covetrus", TODAY + timedelta(days=300)),
            ("cytopoint 30mg injection", "Dermatology", None, 38.00, 112.99, 15, 8, "MWI", TODAY + timedelta(days=270)),
            ("apoquel 16mg tabs (30ct)", "Dermatology", None, 42.00, 125.99, 18, 10, "Patterson", TODAY + timedelta(days=310)),
            ("convenia 180mg/ml injection", "Antibiotic", None, 48.00, 142.99, 12, 6, "Covetrus", TODAY + timedelta(days=280)),
            ("vetmedin 5mg tabs (50ct)", "Cardiac", None, 35.00, 98.99, 14, 8, "MWI", TODAY + timedelta(days=320)),
            ("saline 0.9% 1L bags (6ct)", "Fluid Therapy", None, 18.00, 58.99, 24, 12, "Covetrus", TODAY + timedelta(days=365)),
            ("lactated ringers 1L bags (6ct)", "Fluid Therapy", None, 16.50, 52.99, 30, 12, "MWI", TODAY + timedelta(days=365)),
            ("hydrogen peroxide 3% 16oz", "Topical", None, 2.50, 8.99, 15, 10, "Patterson", TODAY + timedelta(days=500)),
            ("chlorhexidine 2% scrub 32oz", "Topical", None, 8.90, 28.99, 12, 8, "Covetrus", TODAY + timedelta(days=730)),
            ("vetericyn wound spray 8oz", "Topical", None, 12.20, 38.99, 20, 10, "MWI", TODAY + timedelta(days=400)),
            ("eye drops triple antibiotic", "Ophthalmic", None, 9.80, 32.99, 18, 10, "Patterson", TODAY + timedelta(days=380)),
            ("ear cleaner 8oz", "Otic", None, 7.40, 24.99, 25, 15, "Covetrus", TODAY + timedelta(days=365)),
            ("omega-3 fish oil caps (60ct)", "Supplement", None, 8.20, 26.99, 30, 20, "Patterson", TODAY + timedelta(days=390)),
            ("joint supplement cosequin", "Supplement", None, 18.50, 56.99, 22, 12, "Covetrus", TODAY + timedelta(days=380)),
            ("probiotic powder forti-flora", "Supplement", None, 28.00, 88.99, 15, 10, "MWI", TODAY + timedelta(days=365)),
            ("vitamin B12 injection 30ml", "Supplement", None, 6.80, 22.99, 20, 12, "Patterson", TODAY + timedelta(days=420)),
        ]

        for item in inventory_items:
            drug_name, category, schedule, unit_cost, retail, stock, reorder_pt, supplier, exp_date = item
            db.add(InventoryRecord(
                id=str(uuid.uuid4()), tenant_id=tenant_id,
                drug_name=drug_name, drug_category=category, drug_schedule=schedule,
                current_stock=Decimal(str(stock)),
                reorder_point=Decimal(str(reorder_pt)),
                unit_cost=Decimal(str(unit_cost)),
                retail_price=Decimal(str(retail)),
                expiration_date=exp_date, supplier=supplier,
            ))

        await db.commit()

        total_ext_leakage = sum(p for _, _, p, _ in external_fills)
        print(f"\nDemo data created for tenant: {TENANT_NAME}")
        print(f"  Tenant ID: {tenant_id}")
        print(f"  Admin user: admin@greensboroanimal.com / Demo2026")
        print(f"  Dispensing records: {records_added}")
        print(f"  CS log entries: {len(cs_entries)} (3 with discrepancies)")
        print(f"  Prescription records: {rx_count} ({rx_count - len(external_fills)} in-house, {len(external_fills)} external)")
        print(f"  Inventory items: {len(inventory_items)}")
        print(f"\nExpected key findings:")
        print(f"  CS discrepancies: 3")
        print(f"  Script capture leakage: ~${total_ext_leakage:,}")
        print(f"  Overdue chronic patients: 11 (4 hypothyroid, 3 epileptic, 2 diabetic, 2 osteoarthritic)")
        print(f"  Expiration alerts: 6 CRITICAL, 5 HIGH, 4 MODERATE")
        print(f"  Reorder items: 8")


if __name__ == "__main__":
    asyncio.run(create_demo())
