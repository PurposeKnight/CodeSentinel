from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GitHubWebhookEvent:
    event: str
    delivery_id: str | None
    action: str | None
    repository_full_name: str | None
    payload: dict[str, Any]
