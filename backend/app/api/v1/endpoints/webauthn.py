"""WebAuthn/FIDO2 registration and authentication endpoints."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.core.config import settings
from app.core.redis_client import get_redis
from app.core.security import create_access_token, create_refresh_token, get_current_active_user
from app.models import User, SecurityLog, SecurityEventType, TrustedDevice
from app.schemas import (
    WebAuthnRegisterBeginRequest, WebAuthnRegisterCompleteRequest,
    WebAuthnLoginBeginRequest, WebAuthnLoginCompleteRequest,
    WebAuthnCredentialResponse, TokenResponse, UserResponse,
)
from app.services.webauthn_service import webauthn_service

router = APIRouter()
logger = structlog.get_logger()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Registration ───────────────────────────────────────────

@router.post("/register/begin")
async def webauthn_register_begin(
    payload: WebAuthnRegisterBeginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate WebAuthn registration options for a user."""
    result = await db.execute(select(User).where(User.id == payload.user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    options = await webauthn_service.begin_registration(user, db)
    return options


@router.post("/register/complete", response_model=WebAuthnCredentialResponse)
async def webauthn_register_complete(
    payload: WebAuthnRegisterCompleteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Complete WebAuthn registration and store public key credential."""
    result = await db.execute(select(User).where(User.id == payload.user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        credential = await webauthn_service.complete_registration(
            user, payload.credential, payload.device_name, db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Mark user as verified
    user.is_verified = True

    db.add(SecurityLog(
        user_id=user.id,
        event_type=SecurityEventType.BIOMETRIC_REGISTERED,
        ip_address=get_client_ip(request),
        details={"device_name": payload.device_name},
    ))
    await db.commit()
    await db.refresh(credential)
    return credential


# ── Authentication ─────────────────────────────────────────

@router.post("/login/begin")
async def webauthn_login_begin(
    payload: WebAuthnLoginBeginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate WebAuthn authentication options."""
    result = await db.execute(
        select(User).where(User.username == payload.username.lower(), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        options = await webauthn_service.begin_authentication(user, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return options


@router.post("/login/complete", response_model=TokenResponse)
async def webauthn_login_complete(
    payload: WebAuthnLoginCompleteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Complete WebAuthn authentication and issue JWT tokens."""
    result = await db.execute(
        select(User).where(User.username == payload.username.lower(), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        await webauthn_service.complete_authentication(user, payload.credential, db)
    except ValueError as e:
        db.add(SecurityLog(
            user_id=user.id,
            event_type=SecurityEventType.LOGIN_FAILED,
            ip_address=get_client_ip(request),
            details={"reason": str(e)},
        ))
        await db.commit()
        raise HTTPException(status_code=401, detail=str(e))

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    # Create session
    session_id = str(uuid.uuid4())
    redis = get_redis()
    await redis.setex(f"session:{session_id}", settings.SESSION_TIMEOUT_MINUTES * 60, user.id)

    access_token = create_access_token(user.id, session_id)
    refresh_token = create_refresh_token(user.id, session_id)

    # Trust device if fingerprint provided
    if payload.device_fingerprint:
        existing = await db.execute(
            select(TrustedDevice).where(
                TrustedDevice.user_id == user.id,
                TrustedDevice.device_fingerprint == payload.device_fingerprint,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(TrustedDevice(
                user_id=user.id,
                device_fingerprint=payload.device_fingerprint,
                device_name=payload.device_name or "Unknown Device",
                user_agent=request.headers.get("User-Agent"),
                ip_address=get_client_ip(request),
                last_seen=datetime.now(timezone.utc),
            ))

    db.add(SecurityLog(
        user_id=user.id,
        event_type=SecurityEventType.LOGIN_SUCCESS,
        ip_address=get_client_ip(request),
        details={"session_id": session_id},
    ))
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


# ── Credential Management ──────────────────────────────────

@router.get("/credentials", response_model=list[WebAuthnCredentialResponse])
async def list_credentials(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models import WebAuthnCredential
    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.user_id == current_user.id,
            WebAuthnCredential.is_active == True,
        )
    )
    return result.scalars().all()


@router.delete("/credentials/{credential_id}", status_code=204)
async def remove_credential(
    credential_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models import WebAuthnCredential
    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.id == credential_id,
            WebAuthnCredential.user_id == current_user.id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    cred.is_active = False
    db.add(SecurityLog(
        user_id=current_user.id,
        event_type=SecurityEventType.BIOMETRIC_REMOVED,
        ip_address=get_client_ip(request),
        details={"device_name": cred.device_name},
    ))
    await db.commit()
