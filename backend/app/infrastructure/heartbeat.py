import asyncio
from redis.asyncio import Redis
from app.core.logging import get_logger

logger = get_logger(__name__)


async def publish_heartbeat(redis_url: str, worker_name: str, stop_event: asyncio.Event) -> None:
    logger.info("worker_heartbeat_loop_starting", worker=worker_name)
    redis = None
    try:
        redis = Redis.from_url(redis_url)
        while not stop_event.is_set():
            try:
                # Key expires after 15 seconds, heartbeat refreshed every 5 seconds
                await redis.set(f"codesentinel:heartbeat:{worker_name}", "online", ex=15)
            except Exception as exc:
                logger.warning("worker_heartbeat_failed", worker=worker_name, error=str(exc))

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass
    except Exception as exc:
        logger.error("worker_heartbeat_fatal_error", worker=worker_name, error=str(exc))
    finally:
        if redis:
            await redis.close()
        logger.info("worker_heartbeat_loop_stopped", worker=worker_name)
