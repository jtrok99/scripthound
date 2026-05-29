from sqlalchemy import String, Boolean, DateTime, Date, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional
import uuid
from app.core.database import Base


class PrescriptionRecord(Base):
    __tablename__ = "prescription_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    prescription_id: Mapped[str] = mapped_column(String(50), nullable=False)
    patient_id: Mapped[str] = mapped_column(String(50), nullable=False)
    patient_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    species: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    client_id: Mapped[str] = mapped_column(String(50), nullable=False)
    prescribing_vet_id: Mapped[str] = mapped_column(String(50), nullable=False)
    drug_name: Mapped[str] = mapped_column(String(200), nullable=False)
    drug_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quantity_prescribed: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    retail_price_estimate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    date_written: Mapped[date] = mapped_column(Date, nullable=False)
    filled_in_house: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    filled_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    filled_pharmacy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
