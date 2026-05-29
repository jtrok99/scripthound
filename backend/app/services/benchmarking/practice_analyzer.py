from sqlalchemy.ext.asyncio import AsyncSession
from app.services.scripts.capture_analyzer import calculate_capture_rate
from app.services.inventory.cogs_analyzer import calculate_cogs
from app.services.dea.reconciliation import calculate_reconciliation
from app.services.adherence.refill_tracker import calculate_overdue_refills
from app.models.dispensing import DispensingRecord
from sqlalchemy import select
from collections import defaultdict
import statistics


BENCHMARKS = {
    "script_capture_rate": {"target_low": 70.0, "target_high": 80.0, "unit": "%"},
    "cogs_pct": {"target_low": 18.0, "target_high": 25.0, "unit": "%"},
    "cs_discrepancy_rate": {"target_low": 0.0, "target_high": 0.0, "unit": "count"},
    "chronic_adherence_rate": {"target_low": 85.0, "target_high": 100.0, "unit": "%"},
    "avg_days_overdue": {"target_low": 0.0, "target_high": 5.0, "unit": "days"},
}


def _status(actual: float, low: float, high: float, lower_is_better: bool = False) -> str:
    if lower_is_better:
        if actual <= high:
            return "green"
        elif actual <= high * 1.5:
            return "amber"
        return "red"
    else:
        if actual >= low:
            return "green"
        elif actual >= low * 0.85:
            return "amber"
        return "red"


async def calculate_practice_scorecard(db: AsyncSession, tenant_id: str) -> dict:
    capture = await calculate_capture_rate(db, tenant_id)
    cogs = await calculate_cogs(db, tenant_id)
    discrepancies = await calculate_reconciliation(db, tenant_id)
    adherence = await calculate_overdue_refills(db, tenant_id)

    # KPI 1: Script capture rate
    actual_capture = capture["capture_rate"]
    capture_gap = max(0.0, 70.0 - actual_capture)
    monthly_leakage = capture["monthly_leakage"]
    capture_dollar_impact = monthly_leakage * (capture_gap / max(actual_capture, 1))

    # KPI 2: COGS
    actual_cogs = cogs["overall_cogs_pct"]
    cogs_gap = max(0.0, actual_cogs - 25.0)
    cogs_dollar_impact = cogs["total_retail"] * (cogs_gap / 100) if cogs_gap > 0 else 0.0

    # KPI 3: CS discrepancy rate
    disc_count = len(discrepancies)
    disc_dollar_impact = disc_count * 150.0  # avg $150 investigation cost per discrepancy

    # KPI 4: Chronic adherence
    chronic_monitored = adherence["chronic_patients_monitored"]
    overdue_chronic = adherence.get("chronic_patients_overdue", 0)
    chronic_adherence = round((chronic_monitored - overdue_chronic) / chronic_monitored * 100, 1) if chronic_monitored > 0 else 100.0
    chronic_gap = max(0.0, 85.0 - chronic_adherence)
    chronic_dollar_impact = sum(o["missed_revenue"] for o in adherence["outreach_list"] if o["is_chronic"])

    # KPI 5: Avg days overdue
    avg_days = adherence["average_days_overdue"]
    days_dollar_impact = adherence["missed_monthly_revenue"] * (min(avg_days, 30) / 30)

    scorecard = {
        "kpis": [
            {
                "name": "Script Capture Rate",
                "key": "script_capture_rate",
                "actual": actual_capture,
                "target_low": 70.0,
                "target_high": 80.0,
                "unit": "%",
                "status": _status(actual_capture, 70.0, 80.0),
                "dollar_impact": round(capture_dollar_impact, 2),
                "description": "% of prescriptions filled in-house vs external pharmacies",
            },
            {
                "name": "COGS Percentage",
                "key": "cogs_pct",
                "actual": actual_cogs,
                "target_low": 18.0,
                "target_high": 25.0,
                "unit": "%",
                "status": _status(100 - actual_cogs, 75.0, 82.0),
                "dollar_impact": round(cogs_dollar_impact, 2),
                "description": "Cost of goods as % of revenue — lower is better",
            },
            {
                "name": "Controlled Substance Discrepancies",
                "key": "cs_discrepancy_rate",
                "actual": float(disc_count),
                "target_low": 0.0,
                "target_high": 0.0,
                "unit": "count",
                "status": "green" if disc_count == 0 else ("amber" if disc_count <= 2 else "red"),
                "dollar_impact": round(disc_dollar_impact, 2),
                "description": "Number of controlled substance count discrepancies",
            },
            {
                "name": "Chronic Medication Adherence",
                "key": "chronic_adherence_rate",
                "actual": chronic_adherence,
                "target_low": 85.0,
                "target_high": 100.0,
                "unit": "%",
                "status": _status(chronic_adherence, 85.0, 100.0),
                "dollar_impact": round(chronic_dollar_impact, 2),
                "description": "% of chronic patients current on refills",
            },
            {
                "name": "Avg Days Overdue (Chronic)",
                "key": "avg_days_overdue",
                "actual": avg_days,
                "target_low": 0.0,
                "target_high": 5.0,
                "unit": "days",
                "status": _status(avg_days, 0.0, 5.0, lower_is_better=True),
                "dollar_impact": round(days_dollar_impact, 2),
                "description": "Average days past expected refill date",
            },
        ],
        "total_monthly_opportunity": round(
            capture_dollar_impact + cogs_dollar_impact + disc_dollar_impact + chronic_dollar_impact + days_dollar_impact, 2
        ),
    }

    return scorecard
