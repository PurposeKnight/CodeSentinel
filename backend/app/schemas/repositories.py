from pydantic import BaseModel, ConfigDict


class RepositoryResponse(BaseModel):
    id: int
    name: str
    full_name: str
    html_url: str
    description: str | None = None
    is_linked: bool = False

    model_config = ConfigDict(from_attributes=True)


class LinkRepositoryRequest(BaseModel):
    repository: str


class RepositorySettingsResponse(BaseModel):
    repository: str
    slack_webhook_url: str | None = None
    alert_email: str | None = None
    min_security_score: int = 70
    min_overall_score: int = 60
    enabled_agents: list[str] = ["security-agent", "code-review-agent", "testing-agent", "documentation-agent", "deployment-agent"]

    model_config = ConfigDict(from_attributes=True)


class RepositorySettingsUpdate(BaseModel):
    slack_webhook_url: str | None = None
    alert_email: str | None = None
    min_security_score: int = 70
    min_overall_score: int = 60
    enabled_agents: list[str] = ["security-agent", "code-review-agent", "testing-agent", "documentation-agent", "deployment-agent"]
