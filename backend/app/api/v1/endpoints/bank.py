"""Bank account endpoints — protected by biometric re-auth."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, BankAccount
from app.schemas import BankAccountRequest, BankAccountResponse

router = APIRouter()


@router.get("/", response_model=list[BankAccountResponse])
async def list_bank_accounts(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BankAccount)
        .where(BankAccount.user_id == current_user.id)
        .order_by(BankAccount.is_primary.desc(), BankAccount.created_at)
    )
    return result.scalars().all()


@router.post("/", response_model=BankAccountResponse, status_code=201)
async def add_bank_account(
    payload: BankAccountRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # If this is set as primary, clear existing primary
    if payload.is_primary:
        result = await db.execute(
            select(BankAccount).where(
                BankAccount.user_id == current_user.id,
                BankAccount.is_primary == True,
            )
        )
        for acc in result.scalars().all():
            acc.is_primary = False

    account = BankAccount(
        user_id=current_user.id,
        account_holder_name=payload.account_holder_name,
        account_number=payload.account_number,
        ifsc_code=payload.ifsc_code,
        bank_name=payload.bank_name,
        account_type=payload.account_type,
        is_primary=payload.is_primary,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
async def delete_bank_account(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()
