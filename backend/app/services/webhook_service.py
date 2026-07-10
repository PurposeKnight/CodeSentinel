import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings


class WebhookVerificationError(Exception):
    """Raised when a webhook cannot be trusted or parsed."""


@dataclass(frozen=True, slots=True)
class GitHubWebhookEvent:
    event: str
    delivery_id: str | None
    action: str | None
    repository_full_name: str | None
    payload: dict[str, Any]


class GitHubWebhookService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def parse_event(
        self,
        raw_body: bytes,
        signature: str | None,
        event_type: str | None,
        delivery_id: str | None,
    ) -> GitHubWebhookEvent:
        self._verify_signature(raw_body=raw_body, signature=signature)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise WebhookVerificationError("Invalid JSON payload.") from exc

        repository = payload.get("repository") if isinstance(payload, dict) else None
        repository_full_name = (
            repository.get("full_name") if isinstance(repository, dict) else None
        )

        return GitHubWebhookEvent(
            event=event_type or "unknown",
            delivery_id=delivery_id,
            action=payload.get("action") if isinstance(payload, dict) else None,
            repository_full_name=repository_full_name,
            payload=payload,
        )

    def _verify_signature(self, raw_body: bytes, signature: str | None) -> None:
        if not signature:
            raise WebhookVerificationError("Missing X-Hub-Signature-256 header.")

        expected = self._build_signature(raw_body)
        if not hmac.compare_digest(expected, signature):
            raise WebhookVerificationError("Signature mismatch.")

    def _build_signature(self, raw_body: bytes) -> str:
        secret = self._settings.github_webhook_secret.get_secret_value().encode("utf-8")
        digest = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"
