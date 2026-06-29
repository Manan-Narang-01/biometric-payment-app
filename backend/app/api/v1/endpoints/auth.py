"""Auth endpoints: register, token refresh, logout."""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.core.config import settings
from app.core.redis_client import get_redis
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, get_current_active_user
)
from app.models import User, UserSession, SecurityLog, SecurityEventType
from app.schemas import UserRegisterRequest, UserResponse, TokenResponse, RefreshTokenRequest
from app.services.wallet_service import wallet_service

router = APIRouter()
logger = structlog.get_logger()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account (no password — biometric only)."""
    # Check uniqueness
    result = await db.execute(
        select(User).where(
            (User.username == payload.username) | (User.email == payload.email)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        display_name=payload.display_name,
    )
    db.add(user)
    await db.flush()

    # Auto-create wallet
    await wallet_service.create_wallet(user, db)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token from body or HttpOnly cookie."""
    token = payload.refresh_token or request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    token_data = decode_token(token)
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # Check refresh token not revoked
    redis = get_redis()
    jti = token_data.get("jti")
    if await redis.exists(f"revoked:refresh:{jti}"):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    user_id = token_data["sub"]
    old_session_id = token_data["session_id"]

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Revoke old refresh token
    ttl = int(token_data["exp"] - datetime.now(timezone.utc).timestamp())
    if ttl > 0:
        await redis.setex(f"revoked:refresh:{jti}", ttl, "1")

    # ── Security Fix: Invalidate old session BEFORE creating new one ──
    # Without this, the old session remains alive in Redis until it
    # naturally expires.  If the refresh token was stolen, the attacker
    # retains a valid session even after the real user refreshes.
    await redis.delete(f"session:{old_session_id}")

    # Issue new tokens with a fresh session
    new_session_id = str(uuid.uuid4())
    access_token = create_access_token(user.id, new_session_id)
    new_refresh_token = create_refresh_token(user.id, new_session_id)

    await redis.setex(
        f"session:{new_session_id}",
        settings.SESSION_TIMEOUT_MINUTES * 60,
        user.id,
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user),
):
    """Invalidate current session and revoke refresh token."""
    redis = get_redis()

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token_data = decode_token(auth_header[7:])
        session_id = token_data.get("session_id")
        if session_id:
            await redis.delete(f"session:{session_id}")

    refresh_cookie = request.cookies.get("refresh_token")
    if refresh_cookie:
        try:
            rt_data = decode_token(refresh_cookie)
            jti = rt_data.get("jti")
            if jti:
                ttl = int(rt_data["exp"] - datetime.now(timezone.utc).timestamp())
                if ttl > 0:
                    await redis.setex(f"revoked:refresh:{jti}", ttl, "1")
        except HTTPException:
            pass  # token already expired — nothing left to revoke

    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
