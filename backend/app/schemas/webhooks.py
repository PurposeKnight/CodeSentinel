from pydantic import BaseModel


class GitHubWebhookAccepted(BaseModel):
    accepted: bool
    event: str
    delivery_id: str | None
    message: str
