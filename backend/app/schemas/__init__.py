"""Pydantic schemas for request/response validation."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, field_validator, model_validator
import re


# ── User Schemas ───────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    display_name: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]{3,50}$", v):
            raise ValueError("Username must be 3-50 alphanumeric characters or underscores")
        return v.lower()


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str
    avatar_color: str
    phone_number: Optional[str] = None
    upi_id: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    avatar_color: Optional[str] = None
    phone_number: Optional[str] = None
    upi_id: Optional[str] = None


# ── WebAuthn Schemas ───────────────────────────────────────

class WebAuthnRegisterBeginRequest(BaseModel):
    user_id: str
    device_name: str = "My Device"


class WebAuthnRegisterCompleteRequest(BaseModel):
    user_id: str
    credential: dict
    device_name: str = "My Device"


class WebAuthnLoginBeginRequest(BaseModel):
    username: str


class WebAuthnLoginCompleteRequest(BaseModel):
    username: str
    credential: dict
    device_fingerprint: Optional[str] = None
    device_name: Optional[str] = None


class WebAuthnCredentialResponse(BaseModel):
    id: str
    credential_id: str
    device_name: str
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Auth Schemas ───────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None  # returned only in the HttpOnly cookie, not the body
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


# ── Wallet Schemas ─────────────────────────────────────────

class WalletResponse(BaseModel):
    id: str
    balance: Decimal
    currency: str
    wallet_address: str
    is_frozen: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Transaction Schemas ────────────────────────────────────

class TransferRequest(BaseModel):
    receiver_username: str
    amount: Decimal
    description: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        if v > Decimal("100000"):
            raise ValueError("Amount exceeds maximum transfer limit")
        return round(v, 2)


class QRPaymentRequest(BaseModel):
    qr_data: str
    amount: Decimal

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return round(v, 2)


class GenerateQRRequest(BaseModel):
    amount: Optional[Decimal] = None
    description: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    amount: Decimal
    fee: Decimal
    currency: str
    transaction_type: str
    status: str
    description: Optional[str] = None
    reference_id: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    sender_wallet_id: Optional[str] = None
    receiver_wallet_id: Optional[str] = None

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    page: int
    page_size: int


# ── Analytics Schemas ──────────────────────────────────────

class AnalyticsResponse(BaseModel):
    total_sent: Decimal
    total_received: Decimal
    transaction_count: int
    monthly_data: List[dict]
    spending_by_type: List[dict]


# ── Security Log Schemas ───────────────────────────────────

class SecurityLogResponse(BaseModel):
    id: str
    event_type: str
    ip_address: Optional[str] = None
    details: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Bank Account Schemas ───────────────────────────────

class BankAccountRequest(BaseModel):
    account_holder_name: str
    account_number: str
    ifsc_code: Optional[str] = None
    bank_name: str
    account_type: str = "savings"
    is_primary: bool = False


class BankAccountResponse(BaseModel):
    id: str
    account_holder_name: str
    account_number: str
    ifsc_code: Optional[str] = None
    bank_name: str
    account_type: str
    is_primary: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── QR Code Schemas ────────────────────────────────────────

class QRCodeResponse(BaseModel):
    qr_data: str
    wallet_address: str
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    expires_at: datetime
