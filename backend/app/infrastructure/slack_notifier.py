import httpx
from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.ports import SlackPublisher

logger = get_logger(__name__)


class SlackNotificationPublisher(SlackPublisher):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def publish_review_alert(
        self,
        repository: str,
        pr_number: int,
        score: int | None,
        status: str,
        findings_count: int,
        review_id: str,
    ) -> None:
        webhook_secret = self._settings.slack_webhook_url
        webhook_url = webhook_secret.get_secret_value() if webhook_secret else None

        # Build clean Slack block layout
        score_text = f"{score}%" if score is not None else "N/A"
        
        # Color coding status indicators
        status_emoji = "✅" if status == "completed" else "⚠️" if status == "running" else "❌"
        
        payload = {
            "text": f"CodeSentinel audit completed for {repository} PR #{pr_number}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🔍 CodeSentinel Audit Alert",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*Repository:* {repository}\n"
                            f"*Pull Request:* #{pr_number}\n"
                            f"*Status:* {status_emoji} {status.upper()}\n"
                            f"*Overall Quality Index:* *{score_text}*"
                        )
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Findings:* {findings_count} issue(s) identified during audit."
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Dashboard Report"
                            },
                            "url": f"http://localhost:3000/reviews/{review_id}",
                            "style": "primary"
                        }
                    ]
                }
            ]
        }

        if not webhook_url or webhook_url == "mock-slack-url":
            logger.info(
                "slack_notification_skipped_mock_mode",
                repository=repository,
                pr_number=pr_number,
                score=score,
                status=status,
                findings_count=findings_count,
            )
            return

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(webhook_url, json=payload)
                if res.status_code not in (200, 201):
                    logger.error(
                        "slack_notification_failed",
                        status_code=res.status_code,
                        response=res.text,
                    )
                else:
                    logger.info("slack_notification_published", repository=repository, pr_number=pr_number)
        except Exception as e:
            logger.error("slack_notification_error", error=str(e))
