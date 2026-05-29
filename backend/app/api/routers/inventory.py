from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.inventory.cogs_analyzer import calculate_cogs, calculate_reorder_needs
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/dashboard")
async def inventory_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_cogs(db, current_user.tenant_id)
    reorder = await calculate_reorder_needs(db, current_user.tenant_id)
    return {
        "cogs_pct": data["overall_cogs_pct"],
        "cogs_status": data["status"],
        "expiration_alert_counts": data["expiration_alert_counts"],
        "estimated_waste_cost": data["estimated_waste_cost"],
        "reorder_items_count": len(reorder),
    }


@router.get("/expiration-alerts")
async def expiration_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_cogs(db, current_user.tenant_id)
    return {"items": data["expiration_alerts"]}


@router.get("/cogs-by-drug")
async def cogs_by_drug(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_cogs(db, current_user.tenant_id)
    return {"top10": data["top10_by_cogs_pct"]}


@router.get("/markup-opportunities")
async def markup_opportunities(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_cogs(db, current_user.tenant_id)
    return {"items": data["markup_opportunities"]}


@router.get("/reorder-list")
async def reorder_list(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await calculate_reorder_needs(db, current_user.tenant_id)
    return {"items": items}


@router.post("/calculate")
async def trigger_inventory_calculation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await calculate_cogs(db, current_user.tenant_id)
    reorder = await calculate_reorder_needs(db, current_user.tenant_id)
    return {
        "status": "completed",
        "cogs_pct": data["overall_cogs_pct"],
        "expiration_alerts": len(data["expiration_alerts"]),
        "reorder_items": len(reorder),
    }
