from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: str
    github_id: int
    username: str
    email: str | None = None
    avatar_url: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    session_token: str
    user_id: str
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)
