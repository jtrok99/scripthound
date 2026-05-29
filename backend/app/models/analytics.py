from sqlalchemy import String, DateTime, Date, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date, timezone
from typing import Any, Optional
import uuid
from app.core.database import Base


class AnalyticsResult(Base):
    __tablename__ = "analytics_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False)
    measurement_date: Mapped[date] = mapped_column(Date, nullable=False)
    result_data: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
