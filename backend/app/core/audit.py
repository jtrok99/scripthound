from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
import uuid


async def log_event(
    db: AsyncSession,
    action: str,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    success: bool = True,
    details: Optional[str] = None,
):
    entry = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        success=success,
        details=details,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.commit()
