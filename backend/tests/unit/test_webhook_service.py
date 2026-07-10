import hashlib
import hmac

import pytest

from app.core.config import Settings
from app.services.webhook_service import GitHubWebhookService, WebhookVerificationError


def test_parse_event_accepts_valid_github_signature() -> None:
    settings = Settings(github_webhook_secret="test-secret")
    service = GitHubWebhookService(settings=settings)
    body = b'{"action":"opened","repository":{"full_name":"PurposeKnight/CodeSentinel"}}'
    signature = _signature(secret="test-secret", body=body)

    event = service.parse_event(
        raw_body=body,
        signature=signature,
        event_type="pull_request",
        delivery_id="delivery-1",
    )

    assert event.event == "pull_request"
    assert event.delivery_id == "delivery-1"
    assert event.action == "opened"
    assert event.repository_full_name == "PurposeKnight/CodeSentinel"


def test_parse_event_rejects_invalid_github_signature() -> None:
    settings = Settings(github_webhook_secret="test-secret")
    service = GitHubWebhookService(settings=settings)

    with pytest.raises(WebhookVerificationError):
        service.parse_event(
            raw_body=b'{"action":"opened"}',
            signature="sha256=bad",
            event_type="pull_request",
            delivery_id="delivery-1",
        )


def _signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"
