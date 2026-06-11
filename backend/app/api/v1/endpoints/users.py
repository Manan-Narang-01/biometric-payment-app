"""Users endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User
from app.schemas import UserResponse, UserUpdateRequest

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.avatar_color is not None:
        current_user.avatar_color = payload.avatar_color
    if payload.phone_number is not None:
        # Check uniqueness
        existing = await db.execute(
            select(User).where(User.phone_number == payload.phone_number, User.id != current_user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Phone number already in use")
        current_user.phone_number = payload.phone_number or None
    if payload.upi_id is not None:
        existing = await db.execute(
            select(User).where(User.upi_id == payload.upi_id, User.id != current_user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="UPI ID already in use")
        current_user.upi_id = payload.upi_id or None
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/search")
async def search_users(
    q: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    pattern = f"%{q}%"
    result = await db.execute(
        select(User.username, User.display_name, User.phone_number, User.upi_id).where(
            or_(
                User.username.ilike(pattern),
                User.phone_number.ilike(pattern),
                User.upi_id.ilike(pattern),
            ),
            User.is_active == True,
            User.id != current_user.id,
        ).limit(10)
    )
    rows = result.all()
    return [
        {
            "username": r.username,
            "display_name": r.display_name,
            "phone_number": r.phone_number,
            "upi_id": r.upi_id,
        }
        for r in rows
    ]
