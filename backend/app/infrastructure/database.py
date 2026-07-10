import asyncpg

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_postgres_pool(settings: Settings) -> asyncpg.Pool:
    logger.info(
        "postgres_pool_creating",
        host=settings.postgres_host,
        database=settings.postgres_db,
    )
    return await asyncpg.create_pool(
        dsn=settings.postgres_dsn,
        min_size=1,
        max_size=10,
        command_timeout=30,
    )


async def close_postgres_pool(pool: asyncpg.Pool | None) -> None:
    if pool is None:
        return
    await pool.close()
    logger.info("postgres_pool_closed")
