from typing import Protocol

from app.domain.events import GitHubWebhookEvent


class EventPublisher(Protocol):
    async def publish_github_webhook(self, event: GitHubWebhookEvent) -> None:
        """Publish a verified GitHub webhook event for asynchronous processing."""

    async def check(self) -> None:
        """Raise if the publisher is unavailable."""
