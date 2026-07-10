from typing import Any, Protocol

from app.domain.events import GitHubWebhookEvent
from app.domain.models import AgentTask, PullRequestReview


class ReviewRepository(Protocol):
    async def save_review(self, review: PullRequestReview) -> None:
        """Save or update a pull request review entry."""

    async def save_task(self, task: AgentTask) -> None:
        """Save or update an agent task entry."""

    async def get_review(self, review_id: str) -> PullRequestReview | None:
        """Retrieve a review by its unique ID."""

    async def get_tasks(self, review_id: str) -> list[AgentTask]:
        """Retrieve all tasks associated with a review."""


class EventPublisher(Protocol):
    async def publish_github_webhook(self, event: GitHubWebhookEvent) -> None:
        """Publish a verified GitHub webhook event for asynchronous processing."""

    async def publish_agent_task(
        self,
        review_id: str,
        task_id: str,
        agent: str,
        repository: str,
        pull_request_number: int,
    ) -> None:
        """Publish an agent task to downstream queues for execution."""

    async def check(self) -> None:
        """Raise if the publisher is unavailable."""


class VulnerabilityExplainer(Protocol):
    async def explain_vulnerability(
        self,
        scanner: str,
        vulnerability_detail: dict[str, Any],
    ) -> dict[str, Any]:
        """Use the LLM to explain a vulnerability and recommend fixes.

        Returns a dict containing:
          - explanation (str)
          - recommendation (str)
          - code_fix (str or None)
        """


