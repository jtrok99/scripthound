from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.audit import log_event
from app.models.dispensing import DispensingRecord
from app.models.prescription import PrescriptionRecord
from app.models.inventory import InventoryRecord
from app.models.controlled_substance import ControlledSubstanceLog
from app.api.v1.auth import get_current_user
from app.models.user import User
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, time
import csv
import io
import uuid

router = APIRouter()


def parse_date(val: str) -> date | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            continue
    return None


def parse_decimal(val: str) -> Decimal | None:
    try:
        return Decimal(val.strip()) if val.strip() else None
    except InvalidOperation:
        return None


def parse_bool(val: str) -> bool | None:
    if not val.strip():
        return None
    return val.strip().lower() in ("true", "1", "yes", "t")


@router.post("/dispensing")
async def ingest_dispensing(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))

    required = {"record_date", "patient_id", "dispensing_vet_id", "drug_name", "quantity_dispensed", "unit", "cost_of_goods", "retail_price"}
    accepted, rejected = 0, []

    for i, row in enumerate(reader, start=2):
        missing = required - set(row.keys())
        if missing:
            rejected.append({"row": i, "reason": f"Missing required columns: {missing}"})
            continue

        record_date = parse_date(row.get("record_date", ""))
        if not record_date:
            rejected.append({"row": i, "reason": "Invalid record_date"})
            continue

        qty = parse_decimal(row.get("quantity_dispensed", ""))
        cogs = parse_decimal(row.get("cost_of_goods", ""))
        retail = parse_decimal(row.get("retail_price", ""))
        if qty is None or cogs is None or retail is None:
            rejected.append({"row": i, "reason": "Invalid numeric value"})
            continue

        rec = DispensingRecord(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            record_date=record_date,
            patient_id=row.get("patient_id", "").strip(),
            patient_name=row.get("patient_name", "").strip() or None,
            species=row.get("species", "").strip() or None,
            client_id=row.get("client_id", row.get("patient_id", "")).strip(),
            dispensing_vet_id=row.get("dispensing_vet_id", "").strip(),
            drug_name=row.get("drug_name", "").strip(),
            ndc_code=row.get("ndc_code", "").strip() or None,
            drug_schedule=row.get("drug_schedule", "").strip() or None,
            drug_category=row.get("drug_category", "").strip() or None,
            quantity_dispensed=qty,
            unit=row.get("unit", "").strip(),
            days_supply=int(row["days_supply"]) if row.get("days_supply", "").strip() else None,
            cost_of_goods=cogs,
            retail_price=retail,
            filled_in_house=parse_bool(row.get("filled_in_house", "true")) if row.get("filled_in_house") else True,
            expiration_date=parse_date(row.get("expiration_date", "")),
            lot_number=row.get("lot_number", "").strip() or None,
            chronic_condition=row.get("chronic_condition", "").strip() or None,
        )
        db.add(rec)
        accepted += 1

    await db.commit()
    await log_event(db, "ingest_dispensing", user_id=current_user.id, tenant_id=current_user.tenant_id, details=f"{accepted} rows accepted")
    return {"rows_accepted": accepted, "rows_rejected": rejected}


@router.post("/prescriptions")
async def ingest_prescriptions(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    required = {"prescription_id", "patient_id", "client_id", "prescribing_vet_id", "drug_name", "quantity_prescribed", "date_written"}
    accepted, rejected = 0, []

    for i, row in enumerate(reader, start=2):
        missing = required - set(row.keys())
        if missing:
            rejected.append({"row": i, "reason": f"Missing: {missing}"})
            continue

        date_written = parse_date(row.get("date_written", ""))
        qty = parse_decimal(row.get("quantity_prescribed", ""))
        if not date_written or qty is None:
            rejected.append({"row": i, "reason": "Invalid date or quantity"})
            continue

        rec = PrescriptionRecord(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            prescription_id=row["prescription_id"].strip(),
            patient_id=row["patient_id"].strip(),
            patient_name=row.get("patient_name", "").strip() or None,
            species=row.get("species", "").strip() or None,
            client_id=row["client_id"].strip(),
            prescribing_vet_id=row["prescribing_vet_id"].strip(),
            drug_name=row["drug_name"].strip(),
            drug_category=row.get("drug_category", "").strip() or None,
            quantity_prescribed=qty,
            retail_price_estimate=parse_decimal(row.get("retail_price_estimate", "")),
            date_written=date_written,
            filled_in_house=parse_bool(row.get("filled_in_house", "")),
            filled_date=parse_date(row.get("filled_date", "")),
            filled_pharmacy=row.get("filled_pharmacy", "").strip() or None,
        )
        db.add(rec)
        accepted += 1

    await db.commit()
    await log_event(db, "ingest_prescriptions", user_id=current_user.id, tenant_id=current_user.tenant_id, details=f"{accepted} rows")
    return {"rows_accepted": accepted, "rows_rejected": rejected}


@router.post("/inventory")
async def ingest_inventory(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    required = {"drug_name", "current_stock", "unit_cost", "retail_price"}
    accepted, rejected = 0, []

    for i, row in enumerate(reader, start=2):
        missing = required - set(row.keys())
        if missing:
            rejected.append({"row": i, "reason": f"Missing: {missing}"})
            continue

        stock = parse_decimal(row.get("current_stock", ""))
        unit_cost = parse_decimal(row.get("unit_cost", ""))
        retail = parse_decimal(row.get("retail_price", ""))
        if stock is None or unit_cost is None or retail is None:
            rejected.append({"row": i, "reason": "Invalid numeric"})
            continue

        rec = InventoryRecord(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            drug_name=row["drug_name"].strip(),
            ndc_code=row.get("ndc_code", "").strip() or None,
            drug_schedule=row.get("drug_schedule", "").strip() or None,
            drug_category=row.get("drug_category", "").strip() or None,
            current_stock=stock,
            reorder_point=parse_decimal(row.get("reorder_point", "")),
            unit_cost=unit_cost,
            retail_price=retail,
            expiration_date=parse_date(row.get("expiration_date", "")),
            supplier=row.get("supplier", "").strip() or None,
            last_ordered=parse_date(row.get("last_ordered", "")),
        )
        db.add(rec)
        accepted += 1

    await db.commit()
    await log_event(db, "ingest_inventory", user_id=current_user.id, tenant_id=current_user.tenant_id, details=f"{accepted} rows")
    return {"rows_accepted": accepted, "rows_rejected": rejected}


@router.post("/controlled-substances")
async def ingest_controlled_substances(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    required = {"drug_name", "drug_schedule", "transaction_type", "beginning_count", "ending_count", "expected_count", "transaction_date"}
    accepted, rejected = 0, []

    for i, row in enumerate(reader, start=2):
        missing = required - set(row.keys())
        if missing:
            rejected.append({"row": i, "reason": f"Missing: {missing}"})
            continue

        txn_date = parse_date(row.get("transaction_date", ""))
        beg = parse_decimal(row.get("beginning_count", ""))
        end = parse_decimal(row.get("ending_count", ""))
        exp = parse_decimal(row.get("expected_count", ""))
        if not txn_date or beg is None or end is None or exp is None:
            rejected.append({"row": i, "reason": "Invalid date or count"})
            continue

        discrepancy = exp - end
        flag = abs(float(discrepancy)) > 0.01

        txn_time_str = row.get("transaction_time", "").strip()
        txn_time = None
        if txn_time_str:
            try:
                txn_time = datetime.strptime(txn_time_str, "%H:%M:%S").time()
            except ValueError:
                try:
                    txn_time = datetime.strptime(txn_time_str, "%H:%M").time()
                except ValueError:
                    pass

        rec = ControlledSubstanceLog(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            drug_name=row["drug_name"].strip(),
            drug_schedule=row["drug_schedule"].strip(),
            transaction_type=row["transaction_type"].strip(),
            beginning_count=beg,
            ending_count=end,
            expected_count=exp,
            discrepancy=discrepancy,
            discrepancy_flag=flag,
            transaction_date=txn_date,
            transaction_time=txn_time,
            dispensed_by=row.get("dispensed_by", "").strip() or None,
            notes=row.get("notes", "").strip() or None,
        )
        db.add(rec)
        accepted += 1

    await db.commit()
    await log_event(db, "ingest_controlled_substances", user_id=current_user.id, tenant_id=current_user.tenant_id, details=f"{accepted} rows")
    return {"rows_accepted": accepted, "rows_rejected": rejected}
