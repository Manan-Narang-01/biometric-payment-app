"""Redis client for sessions and caching."""
import redis.asyncio as aioredis
from app.core.config import settings
import structlog

logger = structlog.get_logger()
redis_client: aioredis.Redis | None = None


async def init_redis():
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    await redis_client.ping()
    logger.info("Redis connected")


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()


def get_redis() -> aioredis.Redis:
    if redis_client is None:
        raise RuntimeError("Redis not initialized")
    return redis_client
