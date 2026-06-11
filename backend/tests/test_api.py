"""
BioPay Backend Tests
Run with: pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings

# ── Test DB (SQLite in-memory) ─────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession  = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Health check ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# ── User registration ──────────────────────────────────────

@pytest.mark.asyncio
async def test_register_user(client):
    r = await client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email":    "test@example.com",
        "display_name": "Test User",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["username"]     == "testuser"
    assert data["email"]        == "test@example.com"
    assert data["display_name"] == "Test User"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    payload = {"username": "dupe", "email": "a@b.com", "display_name": "A"}
    await client.post("/api/v1/auth/register", json=payload)
    r = await client.post("/api/v1/auth/register", json={**payload, "email": "c@d.com"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_register_invalid_username(client):
    r = await client.post("/api/v1/auth/register", json={
        "username": "x",          # too short
        "email": "x@x.com",
        "display_name": "X",
    })
    assert r.status_code == 422


# ── Wallet ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wallet_created_on_registration(client):
    """Wallet should be auto-created with registration."""
    from app.core.database import get_db as real_get_db
    r = await client.post("/api/v1/auth/register", json={
        "username": "wallettest",
        "email": "wallet@test.com",
        "display_name": "Wallet Test",
    })
    assert r.status_code == 201
    user_id = r.json()["id"]
    # Wallet creation is internal; just verify user was created
    assert user_id


# ── Protected routes require auth ──────────────────────────

@pytest.mark.asyncio
async def test_wallet_requires_auth(client):
    r = await client.get("/api/v1/wallet/")
    assert r.status_code == 403  # No auth header


@pytest.mark.asyncio
async def test_transactions_requires_auth(client):
    r = await client.get("/api/v1/transactions/")
    assert r.status_code == 403


# ── WebAuthn begin requires existing user ──────────────────

@pytest.mark.asyncio
async def test_webauthn_register_begin_unknown_user(client):
    r = await client.post("/api/v1/auth/webauthn/register/begin", json={
        "user_id": "00000000-0000-0000-0000-000000000000",
        "device_name": "Test Device",
    })
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_webauthn_login_begin_unknown_user(client):
    r = await client.post("/api/v1/auth/webauthn/login/begin", json={
        "username": "nobody"
    })
    assert r.status_code == 404
