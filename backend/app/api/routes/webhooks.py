from typing import Any

from fastapi import APIRouter, Header, Request, status

from app.core.logging import get_logger
from app.schemas.webhooks import GitHubWebhookAccepted

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/webhooks/github",
    response_model=GitHubWebhookAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
) -> GitHubWebhookAccepted:
    payload: dict[str, Any] = await request.json()
    logger.info(
        "github_webhook_received",
        event=x_github_event,
        delivery_id=x_github_delivery,
        repository=payload.get("repository", {}).get("full_name"),
    )

    return GitHubWebhookAccepted(
        accepted=True,
        event=x_github_event or "unknown",
        delivery_id=x_github_delivery,
        message="GitHub webhook accepted for future workflow processing.",
    )
