"""Wallet and transaction business logic."""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import structlog

from app.core.config import settings
from app.core.redis_client import get_redis
from app.models import (
    User, Wallet, Transaction, SecurityLog,
    TransactionType, TransactionStatus, SecurityEventType, AuditLog,
)

logger = structlog.get_logger()


def generate_wallet_address(user_id: str) -> str:
    """Deterministic wallet address from user_id."""
    h = hashlib.sha256(f"biopay:{user_id}".encode()).hexdigest()
    return f"BP{h[:16].upper()}"


def generate_reference_id() -> str:
    return f"TXN{uuid.uuid4().hex[:12].upper()}"


class WalletService:

    async def create_wallet(self, user: User, db: AsyncSession) -> Wallet:
        wallet = Wallet(
            user_id=user.id,
            wallet_address=generate_wallet_address(user.id),
            balance=Decimal("1000.00"),  # Demo seed balance
        )
        db.add(wallet)
        await db.flush()
        return wallet

    async def get_wallet(self, user: User, db: AsyncSession) -> Optional[Wallet]:
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == user.id)
        )
        return result.scalar_one_or_none()

    async def get_transactions(
        self,
        user: User,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        tx_type: Optional[str] = None,
    ) -> tuple[List[Transaction], int]:
        wallet = await self.get_wallet(user, db)
        if not wallet:
            return [], 0

        query = select(Transaction).where(
            or_(
                Transaction.sender_wallet_id == wallet.id,
                Transaction.receiver_wallet_id == wallet.id,
            )
        )
        if tx_type:
            query = query.where(Transaction.transaction_type == tx_type)

        count_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()

        query = query.order_by(Transaction.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return result.scalars().all(), total

    async def transfer(
        self,
        sender: User,
        receiver_username: str,
        amount: Decimal,
        description: Optional[str],
        db: AsyncSession,
        ip_address: Optional[str] = None,
    ) -> Transaction:
        # Load sender wallet
        sender_wallet = await self.get_wallet(sender, db)
        if not sender_wallet:
            raise ValueError("Sender wallet not found")
        if sender_wallet.is_frozen:
            raise ValueError("Your wallet is frozen")
        if sender_wallet.balance < amount:
            raise ValueError("Insufficient balance")

        # Load receiver
        result = await db.execute(
            select(User).where(User.username == receiver_username.lower(), User.is_active == True)
        )
        receiver = result.scalar_one_or_none()
        if not receiver:
            raise ValueError(f"User '{receiver_username}' not found")
        if receiver.id == sender.id:
            raise ValueError("Cannot send money to yourself")

        receiver_wallet = await self.get_wallet(receiver, db)
        if not receiver_wallet:
            raise ValueError("Receiver wallet not found")
        if receiver_wallet.is_frozen:
            raise ValueError("Receiver wallet is frozen")

        fee = round(amount * Decimal("0.001"), 2)  # 0.1% fee

        # Atomic balance update
        sender_wallet.balance -= (amount + fee)
        receiver_wallet.balance += amount

        tx = Transaction(
            sender_wallet_id=sender_wallet.id,
            receiver_wallet_id=receiver_wallet.id,
            amount=amount,
            fee=fee,
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.COMPLETED,
            description=description or f"Transfer to {receiver.display_name}",
            reference_id=generate_reference_id(),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(tx)

        # Audit log
        db.add(SecurityLog(
            user_id=sender.id,
            event_type=SecurityEventType.TRANSFER_COMPLETED,
            ip_address=ip_address,
            details={"amount": str(amount), "receiver": receiver_username, "reference": tx.reference_id},
        ))
        await db.flush()
        return tx

    async def generate_qr_payment(
        self,
        user: User,
        amount: Optional[Decimal],
        description: Optional[str],
        db: AsyncSession,
    ) -> dict:
        wallet = await self.get_wallet(user, db)
        if not wallet:
            raise ValueError("Wallet not found")

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        qr_payload = {
            "wallet_address": wallet.wallet_address,
            "username": user.username,
            "amount": str(amount) if amount else None,
            "description": description,
            "expires_at": expires_at.isoformat(),
            "nonce": uuid.uuid4().hex[:8],
        }
        qr_data = json.dumps(qr_payload)

        # Cache QR in Redis
        redis = get_redis()
        await redis.setex(f"qr:{wallet.wallet_address}:{qr_payload['nonce']}", 1800, qr_data)

        return {
            "qr_data": qr_data,
            "wallet_address": wallet.wallet_address,
            "amount": amount,
            "description": description,
            "expires_at": expires_at,
        }

    async def process_qr_payment(
        self,
        payer: User,
        qr_data: str,
        amount: Decimal,
        db: AsyncSession,
        ip_address: Optional[str] = None,
    ) -> Transaction:
        try:
            payload = json.loads(qr_data)
        except Exception:
            raise ValueError("Invalid QR code")

        expires_at = datetime.fromisoformat(payload["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            raise ValueError("QR code has expired")

        receiver_username = payload.get("username")
        qr_amount = Decimal(payload["amount"]) if payload.get("amount") else amount

        return await self.transfer(payer, receiver_username, qr_amount, payload.get("description"), db, ip_address)

    async def get_analytics(self, user: User, db: AsyncSession) -> dict:
        wallet = await self.get_wallet(user, db)
        if not wallet:
            return {}

        result = await db.execute(
            select(Transaction).where(
                or_(
                    Transaction.sender_wallet_id == wallet.id,
                    Transaction.receiver_wallet_id == wallet.id,
                ),
                Transaction.status == TransactionStatus.COMPLETED,
            ).order_by(Transaction.created_at.desc())
        )
        transactions = result.scalars().all()

        total_sent = sum(t.amount for t in transactions if t.sender_wallet_id == wallet.id)
        total_received = sum(t.amount for t in transactions if t.receiver_wallet_id == wallet.id)

        # Monthly aggregation (last 6 months)
        monthly: dict = {}
        for t in transactions:
            key = t.created_at.strftime("%Y-%m")
            if key not in monthly:
                monthly[key] = {"month": key, "sent": Decimal("0"), "received": Decimal("0")}
            if t.sender_wallet_id == wallet.id:
                monthly[key]["sent"] += t.amount
            else:
                monthly[key]["received"] += t.amount

        monthly_data = sorted(
            [{"month": k, "sent": float(v["sent"]), "received": float(v["received"])} for k, v in monthly.items()],
            key=lambda x: x["month"],
        )[-6:]

        type_counts: dict = {}
        for t in transactions:
            type_counts[t.transaction_type.value] = type_counts.get(t.transaction_type.value, 0) + 1

        return {
            "total_sent": total_sent,
            "total_received": total_received,
            "transaction_count": len(transactions),
            "monthly_data": monthly_data,
            "spending_by_type": [{"type": k, "count": v} for k, v in type_counts.items()],
        }


wallet_service = WalletService()
