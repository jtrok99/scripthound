from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.prescription import PrescriptionRecord
from collections import defaultdict
from datetime import date


async def calculate_capture_rate(db: AsyncSession, tenant_id: str) -> dict:
    result = await db.execute(
        select(PrescriptionRecord).where(
            PrescriptionRecord.tenant_id == tenant_id,
            PrescriptionRecord.filled_in_house.isnot(None),
        )
    )
    records = result.scalars().all()

    if not records:
        return {
            "capture_rate": 0.0,
            "monthly_leakage": 0.0,
            "prescriptions_written": 0,
            "prescriptions_captured": 0,
            "leakage_by_category": {},
            "leakage_by_pharmacy": {},
            "six_month_trend": [],
        }

    total = len(records)
    captured = sum(1 for r in records if r.filled_in_house)
    capture_rate = round(captured / total * 100, 1) if total > 0 else 0.0

    external = [r for r in records if not r.filled_in_house]
    monthly_leakage = float(sum(r.retail_price_estimate or 0 for r in external))

    leakage_by_category: dict[str, float] = defaultdict(float)
    for r in external:
        cat = r.drug_category or "Other"
        leakage_by_category[cat] += float(r.retail_price_estimate or 0)

    leakage_by_pharmacy: dict[str, float] = defaultdict(float)
    for r in external:
        pharmacy = r.filled_pharmacy or "Other"
        leakage_by_pharmacy[pharmacy] += float(r.retail_price_estimate or 0)

    # 6-month trend
    monthly_stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "captured": 0})
    for r in records:
        key = f"{r.date_written.year}-{r.date_written.month:02d}"
        monthly_stats[key]["total"] += 1
        if r.filled_in_house:
            monthly_stats[key]["captured"] += 1

    trend = []
    for month in sorted(monthly_stats.keys())[-6:]:
        d = monthly_stats[month]
        rate = round(d["captured"] / d["total"] * 100, 1) if d["total"] > 0 else 0.0
        trend.append({"month": month, "capture_rate": rate, "total": d["total"], "captured": d["captured"]})

    # All prescriptions with all known
    all_result = await db.execute(
        select(PrescriptionRecord).where(PrescriptionRecord.tenant_id == tenant_id)
    )
    all_records = all_result.scalars().all()

    return {
        "capture_rate": capture_rate,
        "monthly_leakage": round(monthly_leakage, 2),
        "prescriptions_written": len(all_records),
        "prescriptions_captured": captured,
        "leakage_by_category": dict(leakage_by_category),
        "leakage_by_pharmacy": dict(leakage_by_pharmacy),
        "six_month_trend": trend,
    }
