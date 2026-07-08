from pydantic import BaseModel, Field


class DependencyHealth(BaseModel):
    status: str = Field(examples=["ok", "unavailable"])
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    dependencies: dict[str, DependencyHealth]
