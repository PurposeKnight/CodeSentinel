from pydantic import BaseModel


class GitHubWebhookAccepted(BaseModel):
    accepted: bool
    event: str
    delivery_id: str | None
    action: str | None
    repository: str | None
    message: str
