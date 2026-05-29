from sqlalchemy import String, Boolean, DateTime, Date, Time, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date, time, timezone
from decimal import Decimal
from typing import Optional
import uuid
from app.core.database import Base


class DispensingRecord(Base):
    __tablename__ = "dispensing_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    patient_id: Mapped[str] = mapped_column(String(50), nullable=False)
    patient_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    species: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    client_id: Mapped[str] = mapped_column(String(50), nullable=False)
    dispensing_vet_id: Mapped[str] = mapped_column(String(50), nullable=False)
    drug_name: Mapped[str] = mapped_column(String(200), nullable=False)
    ndc_code: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    drug_schedule: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    drug_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quantity_dispensed: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    days_supply: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_of_goods: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    retail_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    filled_in_house: Mapped[bool] = mapped_column(Boolean, default=True)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    lot_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    chronic_condition: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    transaction_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
