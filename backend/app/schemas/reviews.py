from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class AgentTaskSchema(BaseModel):
    id: str
    review_id: str
    agent: str
    status: str
    reason: str | None = None
    report: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PullRequestReviewSchema(BaseModel):
    id: str
    repository: str
    pull_request_number: int
    delivery_id: str | None = None
    status: str
    score: int | None = None
    security_score: int | None = None
    performance_score: int | None = None
    architecture_score: int | None = None
    documentation_score: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PullRequestReviewDetailSchema(PullRequestReviewSchema):
    tasks: list[AgentTaskSchema] = []
