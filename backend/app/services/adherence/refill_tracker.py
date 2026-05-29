from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.dispensing import DispensingRecord
from collections import defaultdict
from datetime import date

CHRONIC_CONDITIONS = {"hypothyroidism", "epilepsy", "diabetes", "osteoarthritis", "cardiac"}


async def calculate_overdue_refills(db: AsyncSession, tenant_id: str) -> dict:
    today = date.today()

    result = await db.execute(
        select(DispensingRecord).where(
            DispensingRecord.tenant_id == tenant_id,
            DispensingRecord.days_supply.isnot(None),
        )
    )
    records = result.scalars().all()

    # Latest dispense per patient-drug pair
    latest: dict[tuple, DispensingRecord] = {}
    for r in records:
        key = (r.patient_id, r.drug_name)
        if key not in latest or r.record_date > latest[key].record_date:
            latest[key] = r

    overdue_list = []
    total_missed_revenue = 0.0
    chronic_patients_all: set[str] = set()
    chronic_patients_overdue: set[str] = set()

    from datetime import timedelta

    for (patient_id, drug_name), rec in latest.items():
        is_chronic = bool(rec.chronic_condition and rec.chronic_condition in CHRONIC_CONDITIONS)
        if is_chronic:
            chronic_patients_all.add(patient_id)

        expected_refill = rec.record_date + timedelta(days=rec.days_supply)
        days_overdue = (today - expected_refill).days

        if days_overdue <= 0:
            continue

        if is_chronic:
            chronic_patients_overdue.add(patient_id)

        missed_revenue = float(rec.retail_price)
        total_missed_revenue += missed_revenue

        overdue_list.append({
            "patient_id": patient_id,
            "patient_name": rec.patient_name or patient_id,
            "species": rec.species or "unknown",
            "drug_name": drug_name,
            "chronic_condition": rec.chronic_condition,
            "is_chronic": is_chronic,
            "last_dispense_date": str(rec.record_date),
            "expected_refill_date": str(expected_refill),
            "days_overdue": days_overdue,
            "missed_revenue": round(missed_revenue, 2),
            "client_id": rec.client_id,
            "priority": "HIGH" if is_chronic else "NORMAL",
        })

    overdue_list.sort(key=lambda x: (-int(x["is_chronic"]), -x["days_overdue"]))

    days_overdue_values = [o["days_overdue"] for o in overdue_list if o["is_chronic"]]
    avg_days = round(sum(days_overdue_values) / len(days_overdue_values), 1) if days_overdue_values else 0.0

    species_counts: dict[str, int] = defaultdict(int)
    for o in overdue_list:
        species_counts[o["species"]] += 1

    return {
        "overdue_count": len(overdue_list),
        "missed_monthly_revenue": round(total_missed_revenue, 2),
        "chronic_patients_monitored": len(chronic_patients_all),
        "chronic_patients_overdue": len(chronic_patients_overdue),
        "average_days_overdue": avg_days,
        "species_breakdown": dict(species_counts),
        "outreach_list": overdue_list,
    }
