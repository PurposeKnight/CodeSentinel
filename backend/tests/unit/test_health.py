from unittest.mock import AsyncMock, MagicMock

from app.schemas.health import DependencyHealth
from app.services.health_service import HealthService


async def test_health_service_reports_ok_dependencies() -> None:
    pool = MagicMock()
    connection = AsyncMock()
    connection.fetchval.return_value = 1
    pool.acquire.return_value.__aenter__.return_value = connection

    redis = AsyncMock()
    redis.ping.return_value = True

    service = HealthService(postgres_pool=pool, redis_client=redis)

    result = await service.check_dependencies()

    assert result["postgres"].status == "ok"
    assert result["redis"].status == "ok"
    assert isinstance(result["postgres"], DependencyHealth)
