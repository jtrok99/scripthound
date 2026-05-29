from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.benchmarking.practice_analyzer import calculate_practice_scorecard
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/scorecard")
async def practice_scorecard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await calculate_practice_scorecard(db, current_user.tenant_id)
