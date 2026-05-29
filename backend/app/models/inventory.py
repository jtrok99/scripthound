from sqlalchemy import String, DateTime, Date, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional
import uuid
from app.core.database import Base


class InventoryRecord(Base):
    __tablename__ = "inventory_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    drug_name: Mapped[str] = mapped_column(String(200), nullable=False)
    ndc_code: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    drug_schedule: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    drug_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    current_stock: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    reorder_point: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3), nullable=True)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    retail_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    supplier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_ordered: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
