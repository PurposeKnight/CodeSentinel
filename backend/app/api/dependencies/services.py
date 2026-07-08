from fastapi import Request

from app.services.health_service import HealthService


def get_health_service(request: Request) -> HealthService:
    return HealthService(
        postgres_pool=request.app.state.postgres_pool,
        redis_client=request.app.state.redis_client,
    )
