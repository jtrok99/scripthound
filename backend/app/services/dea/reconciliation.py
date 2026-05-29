from decimal import Decimal
from datetime import date, time
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.controlled_substance import ControlledSubstanceLog
from app.models.dispensing import DispensingRecord


async def calculate_reconciliation(db: AsyncSession, tenant_id: str) -> list[dict]:
    result = await db.execute(
        select(ControlledSubstanceLog).where(ControlledSubstanceLog.tenant_id == tenant_id)
    )
    records = result.scalars().all()

    flagged = []
    for rec in records:
        discrepancy = abs(float(rec.expected_count) - float(rec.ending_count))
        flag = discrepancy > 0.01

        if flag:
            severity = "CRITICAL" if rec.drug_schedule == "Schedule II" else "HIGH"
            flagged.append({
                "id": rec.id,
                "drug_name": rec.drug_name,
                "drug_schedule": rec.drug_schedule,
                "transaction_date": str(rec.transaction_date),
                "beginning_count": float(rec.beginning_count),
                "ending_count": float(rec.ending_count),
                "expected_count": float(rec.expected_count),
                "discrepancy": round(float(rec.expected_count) - float(rec.ending_count), 3),
                "discrepancy_flag": flag,
                "severity": severity,
                "dispensed_by": rec.dispensed_by,
            })

    return flagged


async def detect_diversion_risk(db: AsyncSession, tenant_id: str) -> list[dict]:
    result = await db.execute(
        select(DispensingRecord).where(
            DispensingRecord.tenant_id == tenant_id,
            DispensingRecord.drug_schedule.isnot(None),
            DispensingRecord.drug_schedule != "None",
        )
    )
    records = result.scalars().all()

    flags = []

    # After-hours dispensing
    for rec in records:
        if rec.transaction_time is not None:
            t = rec.transaction_time if isinstance(rec.transaction_time, time) else None
            if t and (t.hour < 7 or t.hour >= 19):
                flags.append({
                    "event_type": "after_hours",
                    "drug_name": rec.drug_name,
                    "dispensed_by": rec.dispensing_vet_id,
                    "date": str(rec.record_date),
                    "time": str(t),
                    "quantity": float(rec.quantity_dispensed),
                    "severity_score": 7,
                    "description": f"Controlled substance dispensed outside business hours at {t}",
                })

    # Volume anomaly per drug
    from collections import defaultdict
    import statistics

    drug_quantities: dict[str, list[float]] = defaultdict(list)
    for rec in records:
        drug_quantities[rec.drug_name].append(float(rec.quantity_dispensed))

    for rec in records:
        quantities = drug_quantities[rec.drug_name]
        if len(quantities) < 3:
            continue
        avg = statistics.mean(quantities)
        if avg > 0 and float(rec.quantity_dispensed) > avg * 3:
            flags.append({
                "event_type": "volume_anomaly",
                "drug_name": rec.drug_name,
                "dispensed_by": rec.dispensing_vet_id,
                "date": str(rec.record_date),
                "time": str(rec.transaction_time) if rec.transaction_time else None,
                "quantity": float(rec.quantity_dispensed),
                "average_quantity": round(avg, 3),
                "severity_score": 8,
                "description": f"Quantity {float(rec.quantity_dispensed):.1f} is {float(rec.quantity_dispensed)/avg:.1f}x the average of {avg:.1f}",
            })

    # Vet frequency anomaly — monthly count vs 6-month average
    from datetime import datetime, timezone
    import calendar

    vet_drug_monthly: dict[tuple, list[int]] = defaultdict(list)
    vet_drug_counts: dict[tuple, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for rec in records:
        key = (rec.dispensing_vet_id, rec.drug_name)
        month_key = f"{rec.record_date.year}-{rec.record_date.month:02d}"
        vet_drug_counts[key][month_key] += 1

    for key, monthly in vet_drug_counts.items():
        values = list(monthly.values())
        if len(values) < 3:
            continue
        avg = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0
        latest_month = sorted(monthly.keys())[-1]
        latest_count = monthly[latest_month]
        if stdev > 0 and (latest_count - avg) > 2 * stdev:
            flags.append({
                "event_type": "frequency_anomaly",
                "drug_name": key[1],
                "dispensed_by": key[0],
                "date": latest_month,
                "time": None,
                "quantity": latest_count,
                "severity_score": 6,
                "description": f"Vet {key[0]} dispensed {key[1]} {latest_count}x this month vs {avg:.1f}x average",
            })

    return flags
