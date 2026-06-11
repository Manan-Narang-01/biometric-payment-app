"""Transaction endpoints: transfer and QR payment."""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User
from app.schemas import (
    TransferRequest, QRPaymentRequest,
    TransactionResponse, TransactionListResponse,
)
from app.services.wallet_service import wallet_service

router = APIRouter()


def get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


@router.post("/transfer", response_model=TransactionResponse)
async def transfer(
    payload: TransferRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        tx = await wallet_service.transfer(
            current_user,
            payload.receiver_username,
            payload.amount,
            payload.description,
            db,
            get_ip(request),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return tx


@router.post("/qr-pay", response_model=TransactionResponse)
async def qr_pay(
    payload: QRPaymentRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        tx = await wallet_service.process_qr_payment(
            current_user, payload.qr_data, payload.amount, db, get_ip(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return tx


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tx_type: str = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    transactions, total = await wallet_service.get_transactions(
        current_user, db, page, page_size, tx_type
    )
    return TransactionListResponse(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, or_
    from app.models import Transaction, Wallet
    wallet = await wallet_service.get_wallet(current_user, db)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    from sqlalchemy import select
    from app.models import Transaction
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            or_(
                Transaction.sender_wallet_id == wallet.id,
                Transaction.receiver_wallet_id == wallet.id,
            ),
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx
