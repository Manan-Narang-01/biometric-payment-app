"""Security logs, trusted devices, and session management."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.redis_client import get_redis
from app.models import User, SecurityLog, TrustedDevice
from app.schemas import SecurityLogResponse

router = APIRouter()


@router.get("/logs", response_model=list[SecurityLogResponse])
async def get_security_logs(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SecurityLog)
        .where(SecurityLog.user_id == current_user.id)
        .order_by(SecurityLog.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/devices")
async def get_trusted_devices(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrustedDevice).where(
            TrustedDevice.user_id == current_user.id,
            TrustedDevice.is_active == True,
        ).order_by(TrustedDevice.last_seen.desc())
    )
    devices = result.scalars().all()
    return [
        {
            "id": d.id,
            "device_name": d.device_name,
            "ip_address": d.ip_address,
            "last_seen": d.last_seen,
            "created_at": d.created_at,
        }
        for d in devices
    ]


@router.delete("/devices/{device_id}", status_code=204)
async def remove_trusted_device(
    device_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrustedDevice).where(
            TrustedDevice.id == device_id,
            TrustedDevice.user_id == current_user.id,
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.is_active = False
    await db.commit()
