from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, webhooks
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.infrastructure.database import close_postgres_pool, create_postgres_pool
from app.infrastructure.rabbitmq import close_event_publisher, create_event_publisher
from app.infrastructure.redis import close_redis_client, create_redis_client

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    configure_logging(settings)

    logger.info("application_starting", app_name=settings.app_name, environment=settings.app_env)
    app.state.settings = settings
    app.state.postgres_pool = await create_postgres_pool(settings)
    app.state.redis_client = create_redis_client(settings)
    app.state.event_publisher = await create_event_publisher(settings)

    try:
        yield
    finally:
        logger.info("application_stopping")
        await close_event_publisher(app.state.event_publisher)
        await close_redis_client(app.state.redis_client)
        await close_postgres_pool(app.state.postgres_pool)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings)

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.app_debug,
        lifespan=lifespan,
    )
    app.state.settings = app_settings

    app.include_router(health.router, tags=["health"])
    app.include_router(webhooks.router, prefix=app_settings.api_v1_prefix, tags=["webhooks"])

    return app


app = create_app()
