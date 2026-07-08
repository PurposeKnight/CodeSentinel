from redis.asyncio import Redis

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_redis_client(settings: Settings) -> Redis:
    logger.info("redis_client_creating", host=settings.redis_host, db=settings.redis_db)
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def close_redis_client(client: Redis | None) -> None:
    if client is None:
        return
    await client.aclose()
    logger.info("redis_client_closed")
