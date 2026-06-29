"""
BioPay FastAPI Backend — Main Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog

from app.core.config import settings
from app.core.database import init_db
from app.core.redis_client import init_redis, close_redis
from app.api.v1.router import api_router
from app.core.middleware import SecurityHeadersMiddleware, SessionTimeoutMiddleware

logger = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("BioPay backend starting up...")
    await init_db()
    await init_redis()
    logger.info("BioPay backend ready.")
    yield
    logger.info("BioPay backend shutting down...")
    await close_redis()


app = FastAPI(
    title="BioPay API",
    description="Biometric Payment Platform — WebAuthn/FIDO2 Powered",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# ── Rate limiting ──────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ── Custom middleware ──────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SessionTimeoutMiddleware)

# ── Routes ─────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "BioPay API", "version": "1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )
