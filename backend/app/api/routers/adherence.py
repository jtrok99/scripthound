from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.adherence.refill_tracker import calculate_overdue_refills
from app.api.v1.auth import get_current_user
from app.models.user import User
import csv
import io

router = APIRouter()


@router.get("/dashboard")
async def adherence_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_overdue_refills(db, current_user.tenant_id)
    return {
        "overdue_count": data["overdue_count"],
        "missed_monthly_revenue": data["missed_monthly_revenue"],
        "chronic_patients_monitored": data["chronic_patients_monitored"],
        "average_days_overdue": data["average_days_overdue"],
        "species_breakdown": data["species_breakdown"],
    }


@router.get("/overdue-refills")
async def overdue_refills(
    species: str | None = Query(None),
    chronic_condition: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_overdue_refills(db, current_user.tenant_id)
    items = data["outreach_list"]
    if species:
        items = [i for i in items if i.get("species") == species]
    if chronic_condition:
        items = [i for i in items if i.get("chronic_condition") == chronic_condition]
    return {"total": len(items), "items": items}


@router.get("/outreach-list")
async def outreach_list_csv(
    format: str = Query("json"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_overdue_refills(db, current_user.tenant_id)
    items = data["outreach_list"]

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "patient_name", "species", "drug_name", "chronic_condition",
            "days_overdue", "missed_revenue", "client_id", "priority",
        ])
        writer.writeheader()
        for item in items:
            writer.writerow({k: item.get(k, "") for k in writer.fieldnames})
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=outreach_list.csv"},
        )

    return {"total": len(items), "items": items}


@router.post("/calculate")
async def trigger_adherence_calculation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_overdue_refills(db, current_user.tenant_id)
    return {
        "status": "completed",
        "overdue_count": data["overdue_count"],
        "missed_revenue": data["missed_monthly_revenue"],
    }
