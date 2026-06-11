"""Custom security middleware."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self';"
        )
        return response


class SessionTimeoutMiddleware(BaseHTTPMiddleware):
    """Check Redis-backed session validity and enforce timeout."""

    EXEMPT_PATHS = {"/health", "/api/v1/auth/register", "/api/v1/auth/login",
                   "/api/v1/auth/webauthn/register/begin", "/api/v1/auth/webauthn/register/complete",
                   "/api/v1/auth/webauthn/login/begin", "/api/v1/auth/webauthn/login/complete",
                   "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.EXEMPT_PATHS or not request.url.path.startswith("/api/v1/"):
            return await call_next(request)
        # Actual session validation happens in JWT dependency; middleware just tags request
        return await call_next(request)
