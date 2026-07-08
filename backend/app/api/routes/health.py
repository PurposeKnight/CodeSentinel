from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.dependencies.services import get_health_service
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        dependencies={},
    )


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(
    request: Request,
    health_service: HealthService = Depends(get_health_service),
) -> HealthResponse | JSONResponse:
    settings = request.app.state.settings
    dependencies = await health_service.check_dependencies()
    is_ready = all(item.status == "ok" for item in dependencies.values())
    response = HealthResponse(
        status="ok" if is_ready else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        dependencies=dependencies,
    )

    if is_ready:
        return response

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(mode="json"),
    )
