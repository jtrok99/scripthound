from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.dispensing import DispensingRecord
from app.models.inventory import InventoryRecord
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional


async def calculate_cogs(db: AsyncSession, tenant_id: str, month_date: Optional[date] = None) -> dict:
    today = date.today()
    target = month_date or today
    month_start = target.replace(day=1)
    if target.month == 12:
        month_end = target.replace(year=target.year + 1, month=1, day=1)
    else:
        month_end = target.replace(month=target.month + 1, day=1)

    result = await db.execute(
        select(DispensingRecord).where(
            DispensingRecord.tenant_id == tenant_id,
            DispensingRecord.record_date >= month_start,
            DispensingRecord.record_date < month_end,
        )
    )
    records = result.scalars().all()

    total_cogs = sum(float(r.cost_of_goods) for r in records)
    total_retail = sum(float(r.retail_price) for r in records)
    overall_cogs_pct = round(total_cogs / total_retail * 100, 1) if total_retail > 0 else 0.0

    status = "green" if overall_cogs_pct < 25 else ("amber" if overall_cogs_pct <= 30 else "red")

    # Per-drug COGS
    drug_cogs: dict[str, dict] = defaultdict(lambda: {"cogs": 0.0, "retail": 0.0, "count": 0})
    for r in records:
        drug_cogs[r.drug_name]["cogs"] += float(r.cost_of_goods)
        drug_cogs[r.drug_name]["retail"] += float(r.retail_price)
        drug_cogs[r.drug_name]["count"] += 1

    drug_list = []
    for drug, d in drug_cogs.items():
        pct = round(d["cogs"] / d["retail"] * 100, 1) if d["retail"] > 0 else 0.0
        drug_list.append({"drug_name": drug, "cogs_pct": pct, "total_cogs": round(d["cogs"], 2), "total_retail": round(d["retail"], 2)})

    top10_cogs = sorted(drug_list, key=lambda x: x["cogs_pct"], reverse=True)[:10]
    markup_opportunities = [d for d in drug_list if d["cogs_pct"] > 30]

    # Expiration alerts from inventory
    inv_result = await db.execute(
        select(InventoryRecord).where(InventoryRecord.tenant_id == tenant_id)
    )
    inv_records = inv_result.scalars().all()

    expiration_alerts = []
    total_waste_cost = 0.0
    for inv in inv_records:
        if inv.expiration_date is None:
            continue
        days_left = (inv.expiration_date - today).days
        if days_left <= 90:
            if days_left <= 30:
                severity = "CRITICAL"
            elif days_left <= 60:
                severity = "HIGH"
            else:
                severity = "MODERATE"
            waste_cost = float(inv.current_stock) * float(inv.unit_cost)
            total_waste_cost += waste_cost
            expiration_alerts.append({
                "drug_name": inv.drug_name,
                "expiration_date": str(inv.expiration_date),
                "days_until_expiration": days_left,
                "current_stock": float(inv.current_stock),
                "waste_cost": round(waste_cost, 2),
                "severity": severity,
            })

    expiration_alerts.sort(key=lambda x: x["days_until_expiration"])

    counts = {
        "critical": sum(1 for a in expiration_alerts if a["severity"] == "CRITICAL"),
        "high": sum(1 for a in expiration_alerts if a["severity"] == "HIGH"),
        "moderate": sum(1 for a in expiration_alerts if a["severity"] == "MODERATE"),
    }

    return {
        "overall_cogs_pct": overall_cogs_pct,
        "status": status,
        "total_cogs": round(total_cogs, 2),
        "total_retail": round(total_retail, 2),
        "top10_by_cogs_pct": top10_cogs,
        "markup_opportunities": markup_opportunities,
        "expiration_alerts": expiration_alerts,
        "expiration_alert_counts": counts,
        "estimated_waste_cost": round(total_waste_cost, 2),
    }


async def calculate_reorder_needs(db: AsyncSession, tenant_id: str) -> list[dict]:
    result = await db.execute(
        select(InventoryRecord).where(
            InventoryRecord.tenant_id == tenant_id,
            InventoryRecord.reorder_point.isnot(None),
        )
    )
    records = result.scalars().all()

    reorder_list = []
    for inv in records:
        if float(inv.current_stock) <= float(inv.reorder_point):
            gap = float(inv.reorder_point) - float(inv.current_stock)
            reorder_list.append({
                "drug_name": inv.drug_name,
                "current_stock": float(inv.current_stock),
                "reorder_point": float(inv.reorder_point),
                "gap": round(gap, 3),
                "supplier": inv.supplier,
                "unit_cost": float(inv.unit_cost),
                "urgency": "CRITICAL" if float(inv.current_stock) == 0 else "HIGH",
            })

    return sorted(reorder_list, key=lambda x: x["gap"], reverse=True)
