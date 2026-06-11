"""API v1 router — aggregates all endpoint routers."""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, wallet, transactions, webauthn, security, bank

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(webauthn.router, prefix="/auth/webauthn", tags=["WebAuthn / FIDO2"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(security.router, prefix="/security", tags=["Security"])
api_router.include_router(bank.router, prefix="/bank-accounts", tags=["Bank Accounts"])
