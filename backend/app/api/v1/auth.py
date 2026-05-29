from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import verify_password, hash_password, create_access_token, create_refresh_token, decode_token
from app.core.audit import log_event
from app.models.user import User
import pyotp
import uuid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    mfa_required: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        await log_event(db, "login_failure", ip_address=ip, success=False, details=form_data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    access_token = create_access_token({"sub": user.id, "tenant_id": user.tenant_id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})

    await log_event(db, "login_success", user_id=user.id, tenant_id=user.tenant_id, ip_address=ip)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        mfa_required=user.mfa_enabled,
    )


@router.post("/refresh")
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    access_token = create_access_token({"sub": user.id, "tenant_id": user.tenant_id, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await log_event(db, "logout", user_id=current_user.id, tenant_id=current_user.tenant_id)
    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "tenant_id": current_user.tenant_id,
        "mfa_enabled": current_user.mfa_enabled,
    }


@router.post("/mfa/setup")
async def mfa_setup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    secret = pyotp.random_base32()
    current_user.totp_secret = secret
    await db.commit()
    totp = pyotp.TOTP(secret)
    return {"secret": secret, "provisioning_uri": totp.provisioning_uri(current_user.email, issuer_name="ScriptHound")}


@router.post("/mfa/verify")
async def mfa_verify(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="MFA not set up")
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_user.mfa_enabled = True
    await db.commit()
    return {"message": "MFA enabled"}


@router.post("/mfa/validate")
async def mfa_validate(code: str, current_user: User = Depends(get_current_user)):
    if not current_user.totp_secret or not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA not enabled")
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    return {"valid": True}
