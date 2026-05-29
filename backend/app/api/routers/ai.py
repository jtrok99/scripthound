from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.core.config import settings
from app.core.audit import log_event
from app.api.v1.auth import get_current_user
from app.models.user import User
import anthropic

router = APIRouter()


class KPISummaryRequest(BaseModel):
    capture_rate: float
    monthly_leakage: float
    cogs_pct: float
    discrepancy_count: int
    overdue_count: int
    missed_revenue: float
    chronic_adherence_rate: float
    avg_days_overdue: float
    practice_name: str = "Your Practice"


@router.post("/monthly-summary")
async def generate_monthly_summary(
    request: KPISummaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "your-anthropic-key-here":
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")

    prompt = f"""You are a veterinary pharmacy performance analyst. Generate a concise 3-paragraph plain English monthly pharmacy performance summary for {request.practice_name} based on these KPIs:

- Script Capture Rate: {request.capture_rate}% (target: 70-80%)
- Monthly Script Leakage Revenue: ${request.monthly_leakage:,.2f}
- COGS Percentage: {request.cogs_pct}% (target: 18-25%)
- Controlled Substance Discrepancies: {request.discrepancy_count} (target: 0)
- Overdue Refills: {request.overdue_count} patients
- Missed Monthly Refill Revenue: ${request.missed_revenue:,.2f}
- Chronic Medication Adherence: {request.chronic_adherence_rate}% (target: 85%)
- Average Days Overdue: {request.avg_days_overdue} days (target: <5)

Write exactly 3 paragraphs:
Paragraph 1: What went well this month (focus on strengths relative to benchmarks)
Paragraph 2: What needs immediate attention (focus on the most critical issues)
Paragraph 3: Top 3 recommended actions for next month with specific, actionable steps

Keep the tone professional but approachable. Use specific numbers from the KPIs."""

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )

    summary = message.content[0].text

    await log_event(
        db,
        action="ai_monthly_summary",
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        resource_type="ai_summary",
        success=True,
    )

    return {"summary": summary}
