from fastapi import Request

from app.services.health_service import HealthService
from app.services.webhook_service import GitHubWebhookService


def get_health_service(request: Request) -> HealthService:
    return HealthService(
        postgres_pool=request.app.state.postgres_pool,
        redis_client=request.app.state.redis_client,
        event_publisher=request.app.state.event_publisher,
    )


def get_github_webhook_service(request: Request) -> GitHubWebhookService:
    return GitHubWebhookService(
        settings=request.app.state.settings,
        event_publisher=request.app.state.event_publisher,
    )
