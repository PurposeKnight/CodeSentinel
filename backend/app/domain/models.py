from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class PullRequestReview:
    id: str
    repository: str
    pull_request_number: int
    delivery_id: str | None
    status: str
    score: int | None = None
    security_score: int | None = None
    performance_score: int | None = None
    architecture_score: int | None = None
    documentation_score: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AgentTask:
    id: str
    review_id: str
    agent: str
    status: str
    reason: str | None = None
    report: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
