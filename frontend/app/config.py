"""Flask configuration."""
import os


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://backend:8000")
    SESSION_COOKIE_SECURE = os.environ.get("APP_ENV", "development") == "production"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
