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
