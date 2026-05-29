from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.prescription import PrescriptionRecord
from app.services.scripts.capture_analyzer import calculate_capture_rate
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/dashboard")
async def scripts_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id
    data = await calculate_capture_rate(db, tenant_id)
    return {
        "capture_rate": data["capture_rate"],
        "monthly_leakage": data["monthly_leakage"],
        "prescriptions_written": data["prescriptions_written"],
        "prescriptions_captured": data["prescriptions_captured"],
        "six_month_trend": data["six_month_trend"],
    }


@router.get("/leakage-by-category")
async def leakage_by_category(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_capture_rate(db, current_user.tenant_id)
    return {"leakage_by_category": data["leakage_by_category"]}


@router.get("/leakage-by-pharmacy")
async def leakage_by_pharmacy(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_capture_rate(db, current_user.tenant_id)
    return {"leakage_by_pharmacy": data["leakage_by_pharmacy"]}


@router.get("/trend")
async def capture_trend(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_capture_rate(db, current_user.tenant_id)
    return {"trend": data["six_month_trend"]}


@router.get("/prescriptions")
async def list_prescriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(PrescriptionRecord).where(PrescriptionRecord.tenant_id == tenant_id)
        .order_by(PrescriptionRecord.date_written.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    records = result.scalars().all()
    count_result = await db.execute(
        select(func.count()).select_from(PrescriptionRecord).where(PrescriptionRecord.tenant_id == tenant_id)
    )
    total = count_result.scalar() or 0
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "prescription_id": r.prescription_id,
                "patient_name": r.patient_name,
                "drug_name": r.drug_name,
                "date_written": str(r.date_written),
                "filled_in_house": r.filled_in_house,
                "filled_pharmacy": r.filled_pharmacy,
                "retail_price_estimate": float(r.retail_price_estimate) if r.retail_price_estimate else None,
            }
            for r in records
        ],
    }


@router.post("/calculate")
async def trigger_script_calculation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_capture_rate(db, current_user.tenant_id)
    return {"status": "completed", "capture_rate": data["capture_rate"], "monthly_leakage": data["monthly_leakage"]}
