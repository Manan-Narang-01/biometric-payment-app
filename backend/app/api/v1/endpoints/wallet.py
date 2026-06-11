"""Wallet endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User
from app.schemas import WalletResponse, GenerateQRRequest, QRCodeResponse, AnalyticsResponse
from app.services.wallet_service import wallet_service

router = APIRouter()


@router.get("/", response_model=WalletResponse)
async def get_wallet(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    wallet = await wallet_service.get_wallet(current_user, db)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet


@router.post("/qr", response_model=QRCodeResponse)
async def generate_qr(
    payload: GenerateQRRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await wallet_service.generate_qr_payment(
        current_user, payload.amount, payload.description, db
    )
    return result


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await wallet_service.get_analytics(current_user, db)
