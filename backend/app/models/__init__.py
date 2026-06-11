"""
BioPay Database Models
All models in one file for clarity; importable from app.models.*
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    String, Boolean, DateTime, Numeric, ForeignKey,
    Text, Enum, Index, LargeBinary
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ── Enums ──────────────────────────────────────────────────

class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


class TransactionType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER = "transfer"
    QR_PAYMENT = "qr_payment"


class SecurityEventType(str, enum.Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    BIOMETRIC_REGISTERED = "biometric_registered"
    BIOMETRIC_REMOVED = "biometric_removed"
    TRANSFER_INITIATED = "transfer_initiated"
    TRANSFER_COMPLETED = "transfer_completed"
    DEVICE_TRUSTED = "device_trusted"
    DEVICE_REMOVED = "device_removed"
    SESSION_EXPIRED = "session_expired"
    ACCOUNT_UPDATED = "account_updated"


# ── User ───────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_color: Mapped[str] = mapped_column(String(7), default="#00c896")
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True, index=True)
    upi_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    webauthn_credentials: Mapped[list["WebAuthnCredential"]] = relationship("WebAuthnCredential", back_populates="user", cascade="all, delete-orphan")
    trusted_devices: Mapped[list["TrustedDevice"]] = relationship("TrustedDevice", back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    security_logs: Mapped[list["SecurityLog"]] = relationship("SecurityLog", back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    bank_accounts: Mapped[list["BankAccount"]] = relationship("BankAccount", back_populates="user", cascade="all, delete-orphan")


# ── Wallet ─────────────────────────────────────────────────

class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    wallet_address: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="wallet")
    sent_transactions: Mapped[list["Transaction"]] = relationship("Transaction", foreign_keys="Transaction.sender_wallet_id", back_populates="sender_wallet")
    received_transactions: Mapped[list["Transaction"]] = relationship("Transaction", foreign_keys="Transaction.receiver_wallet_id", back_populates="receiver_wallet")


# ── Transaction ────────────────────────────────────────────

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_wallet_id: Mapped[Optional[str]] = mapped_column(ForeignKey("wallets.id"), nullable=True)
    receiver_wallet_id: Mapped[Optional[str]] = mapped_column(ForeignKey("wallets.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reference_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    qr_code_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    sender_wallet: Mapped[Optional["Wallet"]] = relationship("Wallet", foreign_keys=[sender_wallet_id], back_populates="sent_transactions")
    receiver_wallet: Mapped[Optional["Wallet"]] = relationship("Wallet", foreign_keys=[receiver_wallet_id], back_populates="received_transactions")

    __table_args__ = (
        Index("ix_transactions_created_at", "created_at"),
        Index("ix_transactions_status", "status"),
    )


# ── WebAuthn Credential ────────────────────────────────────

class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    credential_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    sign_count: Mapped[int] = mapped_column(default=0)
    device_name: Mapped[str] = mapped_column(String(100), default="Biometric Device")
    aaguid: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    transports: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="webauthn_credentials")


# ── Trusted Device ─────────────────────────────────────────

class TrustedDevice(Base):
    __tablename__ = "trusted_devices"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="trusted_devices")


# ── User Session ───────────────────────────────────────────

class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    device_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="sessions")


# ── Security Log ───────────────────────────────────────────

class SecurityLog(Base):
    __tablename__ = "security_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[SecurityEventType] = mapped_column(Enum(SecurityEventType), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="security_logs")


# ── Bank Account ──────────────────────────────────────

class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_holder_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_number: Mapped[str] = mapped_column(String(30), nullable=False)
    ifsc_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), default="savings")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="bank_accounts")


# ── Audit Log ──────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    changes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
