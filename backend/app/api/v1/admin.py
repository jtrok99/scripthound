from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.api.v1.auth import get_current_user
import uuid

router = APIRouter()


def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin required")
    return current_user


class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    plan_tier: str = "starter"


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "user"
    tenant_id: str | None = None


@router.get("/tenants")
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    result = await db.execute(select(Tenant))
    tenants = result.scalars().all()
    return [{"id": t.id, "name": t.name, "slug": t.slug, "plan_tier": t.plan_tier, "is_active": t.is_active} for t in tenants]


@router.post("/tenants")
async def create_tenant(
    body: CreateTenantRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    tenant = Tenant(id=str(uuid.uuid4()), name=body.name, slug=body.slug, plan_tier=body.plan_tier)
    db.add(tenant)
    await db.commit()
    return {"id": tenant.id, "name": tenant.name, "slug": tenant.slug}


@router.post("/users")
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        tenant_id=body.tenant_id,
    )
    db.add(user)
    await db.commit()
    return {"id": user.id, "email": user.email, "role": user.role}


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "tenant_id": u.tenant_id} for u in users]
