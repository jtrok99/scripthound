from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.controlled_substance import ControlledSubstanceLog
from app.services.dea.reconciliation import calculate_reconciliation, detect_diversion_risk
from app.api.v1.auth import get_current_user
from app.models.user import User
from datetime import date

router = APIRouter()


@router.get("/dashboard")
async def dea_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id
    discrepancies = await calculate_reconciliation(db, tenant_id)
    diversion_flags = await detect_diversion_risk(db, tenant_id)

    result = await db.execute(
        select(func.count()).select_from(ControlledSubstanceLog).where(
            ControlledSubstanceLog.tenant_id == tenant_id
        )
    )
    total_drugs = result.scalar() or 0

    today = date.today()
    last_disc = None
    disc_result = await db.execute(
        select(ControlledSubstanceLog).where(
            ControlledSubstanceLog.tenant_id == tenant_id,
            ControlledSubstanceLog.discrepancy_flag == True,
        ).order_by(ControlledSubstanceLog.transaction_date.desc()).limit(1)
    )
    last_disc_rec = disc_result.scalar_one_or_none()
    days_since = (today - last_disc_rec.transaction_date).days if last_disc_rec else None

    return {
        "total_drugs_tracked": total_drugs,
        "discrepancies_this_month": len(discrepancies),
        "diversion_risk_flags": len(diversion_flags),
        "days_since_last_discrepancy": days_since,
    }


@router.get("/discrepancies")
async def list_discrepancies(
    schedule: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id
    discrepancies = await calculate_reconciliation(db, tenant_id)

    if schedule:
        discrepancies = [d for d in discrepancies if d.get("drug_schedule") == schedule]
    if date_from:
        discrepancies = [d for d in discrepancies if d.get("transaction_date", "") >= str(date_from)]
    if date_to:
        discrepancies = [d for d in discrepancies if d.get("transaction_date", "") <= str(date_to)]

    start = (page - 1) * page_size
    return {
        "total": len(discrepancies),
        "page": page,
        "page_size": page_size,
        "items": discrepancies[start : start + page_size],
    }


@router.get("/diversion-flags")
async def list_diversion_flags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    flags = await detect_diversion_risk(db, current_user.tenant_id)
    flags.sort(key=lambda x: x.get("severity_score", 0), reverse=True)
    return {"total": len(flags), "items": flags}


@router.post("/calculate")
async def trigger_dea_calculation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id
    discrepancies = await calculate_reconciliation(db, tenant_id)
    flags = await detect_diversion_risk(db, tenant_id)
    return {
        "status": "completed",
        "discrepancies_found": len(discrepancies),
        "diversion_flags_found": len(flags),
    }
