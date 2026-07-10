from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.api.dependencies.services import get_github_webhook_service
from app.core.logging import get_logger
from app.schemas.webhooks import GitHubWebhookAccepted
from app.services.webhook_service import GitHubWebhookService, WebhookVerificationError

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/webhooks/github",
    response_model=GitHubWebhookAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def github_webhook(
    request: Request,
    webhook_service: Annotated[
        GitHubWebhookService,
        Depends(get_github_webhook_service),
    ],
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
) -> GitHubWebhookAccepted:
    raw_body = await request.body()
    try:
        event = await webhook_service.accept_event(
            raw_body=raw_body,
            signature=x_hub_signature_256,
            event_type=x_github_event,
            delivery_id=x_github_delivery,
        )
    except WebhookVerificationError as exc:
        logger.warning(
            "github_webhook_rejected",
            github_event=x_github_event,
            delivery_id=x_github_delivery,
            reason=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub webhook signature.",
        ) from exc

    logger.info(
        "github_webhook_received",
        github_event=event.event,
        delivery_id=event.delivery_id,
        action=event.action,
        repository=event.repository_full_name,
    )

    return GitHubWebhookAccepted(
        accepted=True,
        event=event.event,
        delivery_id=event.delivery_id,
        action=event.action,
        repository=event.repository_full_name,
        message="GitHub webhook verified and queued for workflow processing.",
    )
