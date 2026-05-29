from sqlalchemy import String, Boolean, DateTime, Date, Time, Numeric, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date, time, timezone
from decimal import Decimal
from typing import Optional
import uuid
from app.core.database import Base


class ControlledSubstanceLog(Base):
    __tablename__ = "controlled_substance_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    drug_name: Mapped[str] = mapped_column(String(200), nullable=False)
    drug_schedule: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    beginning_count: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    ending_count: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    expected_count: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    discrepancy: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("0"))
    discrepancy_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    dispensed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
