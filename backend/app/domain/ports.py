from typing import Any, Protocol

from app.domain.events import GitHubWebhookEvent
from app.domain.models import AgentTask, PullRequestReview, User, UserSession


class ReviewRepository(Protocol):
    async def save_review(self, review: PullRequestReview) -> None:
        """Save or update a pull request review entry."""

    async def save_task(self, task: AgentTask) -> None:
        """Save or update an agent task entry."""

    async def get_review(self, review_id: str) -> PullRequestReview | None:
        """Retrieve a review by its unique ID."""

    async def get_tasks(self, review_id: str) -> list[AgentTask]:
        """Retrieve all tasks associated with a review."""

    async def list_reviews(self) -> list[PullRequestReview]:
        """Retrieve all pull request reviews, ordered by creation date."""

    async def save_user(self, user: User) -> None:
        """Save or update user details."""

    async def get_user_by_github_id(self, github_id: int) -> User | None:
        """Retrieve a user by their unique GitHub ID."""

    async def get_user(self, user_id: str) -> User | None:
        """Retrieve a user by their unique database ID."""

    async def save_session(self, session: UserSession) -> None:
        """Save a new user session."""

    async def get_session(self, session_token: str) -> UserSession | None:
        """Retrieve an active user session."""

    async def delete_session(self, session_token: str) -> None:
        """Delete/revoke a user session."""

    async def get_repository_settings(self, repository: str) -> dict[str, Any] | None:
        """Retrieve settings for a repository."""

    async def save_repository_settings(self, repository: str, settings: dict[str, Any]) -> None:
        """Save settings for a repository."""


class SlackPublisher(Protocol):
    async def publish_review_alert(
        self,
        repository: str,
        pr_number: int,
        score: int | None,
        status: str,
        findings_count: int,
        review_id: str,
        webhook_url: str | None = None,
    ) -> None:
        """Publish a summary alert of the review to Slack channels."""


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


class CodeReviewer(Protocol):
    async def review_code(self, diff: str) -> dict[str, Any]:
        """Use LLM to review the changes diff and return analysis.

        Returns a dict containing:
          - architecture_score (int)
          - performance_score (int)
          - findings (list of dict)
        """


class TestAnalyzer(Protocol):
    async def analyze_tests(self, target_dir: str) -> dict[str, Any]:
        """Use LLM / local logic to check for missing tests and suggest test cases.

        Returns a dict containing:
          - findings (list of dict)
        """


class DocAnalyzer(Protocol):
    async def analyze_documentation(self, target_dir: str) -> dict[str, Any]:
        """Use LLM / local logic to assess docs, docstrings, API doc impact.

        Returns a dict containing:
          - documentation_score (int)
          - findings (list of dict)
        """


class NotificationPublisher(Protocol):
    async def publish_pr_review(
        self,
        repository: str,
        pr_number: int,
        review_summary: dict[str, Any],
        findings: list[dict[str, Any]],
    ) -> None:
        """Publish a pull request review with a summary and line-level comments/findings."""


class DeploymentService(Protocol):
    async def evaluate_gates(self, review_summary: dict[str, Any]) -> tuple[bool, str]:
        """Check whether the review scores satisfy deployment gate thresholds.

        Returns (passed, reason).
        """

    async def trigger_deployment(self, repository: str, pr_number: int) -> dict[str, Any]:
        """Simulate triggering the CI/CD pipeline and return details."""

    async def verify_health(self) -> tuple[bool, str]:
        """Verify the health of the deployed application (liveness check)."""

    async def rollback(self, repository: str, pr_number: int) -> str:
        """Simulate rolling back the deployment."""


