from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GitHubWebhookEvent:
    event: str
    delivery_id: str | None
    action: str | None
    repository_full_name: str | None
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PlannedAgentTask:
    agent: str
    reason: str


@dataclass(frozen=True, slots=True)
class PullRequestReviewPlan:
    delivery_id: str | None
    repository_full_name: str
    pull_request_number: int | None
    action: str | None
    tasks: tuple[PlannedAgentTask, ...]
