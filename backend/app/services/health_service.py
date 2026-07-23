from time import perf_counter
from typing import Any

import asyncpg
from redis.asyncio import Redis

from app.domain.ports import EventPublisher
from app.schemas.health import DependencyHealth


class HealthService:
    def __init__(
        self,
        postgres_pool: asyncpg.Pool,
        redis_client: Redis,
        event_publisher: EventPublisher,
    ) -> None:
        self._postgres_pool = postgres_pool
        self._redis_client = redis_client
        self._event_publisher = event_publisher

    async def check_dependencies(self) -> dict[str, DependencyHealth]:
        postgres = await self._check_postgres()
        redis = await self._check_redis()
        rabbitmq = await self._check_rabbitmq()
        return {"postgres": postgres, "redis": redis, "rabbitmq": rabbitmq}

    async def check_detailed_dependencies(self) -> dict[str, Any]:
        postgres = await self._check_postgres()
        redis = await self._check_redis()
        rabbitmq = await self._check_rabbitmq()

        workers = [
            "planner-worker",
            "security-worker",
            "code-review-worker",
            "testing-worker",
            "documentation-worker",
            "deployment-worker",
        ]

        worker_statuses = {}
        for w in workers:
            try:
                val = await self._redis_client.get(f"codesentinel:heartbeat:{w}")
                worker_statuses[w] = "online" if val == "online" else "offline"
            except Exception:
                worker_statuses[w] = "offline"

        return {
            "dependencies": {
                "postgres": {
                    "status": postgres.status,
                    "latency_ms": postgres.latency_ms,
                    "detail": postgres.detail,
                },
                "redis": {
                    "status": redis.status,
                    "latency_ms": redis.latency_ms,
                    "detail": redis.detail,
                },
                "rabbitmq": {
                    "status": rabbitmq.status,
                    "latency_ms": rabbitmq.latency_ms,
                    "detail": rabbitmq.detail,
                },
            },
            "workers": worker_statuses,
        }

    async def _check_postgres(self) -> DependencyHealth:
        start = perf_counter()
        try:
            async with self._postgres_pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
        except Exception as exc:  # noqa: BLE001 - health endpoint must surface dependency state.
            return DependencyHealth(status="unavailable", detail=str(exc))

        return DependencyHealth(status="ok", latency_ms=self._elapsed_ms(start))

    async def _check_redis(self) -> DependencyHealth:
        start = perf_counter()
        try:
            await self._redis_client.ping()
        except Exception as exc:  # noqa: BLE001 - health endpoint must surface dependency state.
            return DependencyHealth(status="unavailable", detail=str(exc))

        return DependencyHealth(status="ok", latency_ms=self._elapsed_ms(start))

    async def _check_rabbitmq(self) -> DependencyHealth:
        start = perf_counter()
        try:
            await self._event_publisher.check()
        except Exception as exc:  # noqa: BLE001 - health endpoint must surface dependency state.
            return DependencyHealth(status="unavailable", detail=str(exc))

        return DependencyHealth(status="ok", latency_ms=self._elapsed_ms(start))

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        return round((perf_counter() - start) * 1000, 2)
