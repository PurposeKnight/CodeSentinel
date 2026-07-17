import httpx
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.ports import NotificationPublisher

logger = get_logger(__name__)


class GitHubNotificationPublisher(NotificationPublisher):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        token = settings.github_token.get_secret_value()
        self._is_mock = token == "mock-token"
        self._token = token

    async def publish_pr_review(
        self,
        repository: str,
        pr_number: int,
        review_summary: dict[str, Any],
        findings: list[dict[str, Any]],
    ) -> None:
        # Build markdown summary review body
        score = review_summary.get("score")
        sec_score = review_summary.get("security_score")
        perf_score = review_summary.get("performance_score")
        arch_score = review_summary.get("architecture_score")
        doc_score = review_summary.get("documentation_score")

        summary_body = f"""### CodeSentinel Automated PR Review Report

| Category | Score |
| --- | --- |
| **Overall Score** | **{score if score is not None else 'N/A'}** / 100 |
| Security | {sec_score if sec_score is not None else 'N/A'} / 100 |
| Performance | {perf_score if perf_score is not None else 'N/A'} / 100 |
| Architecture | {arch_score if arch_score is not None else 'N/A'} / 100 |
| Documentation | {doc_score if doc_score is not None else 'N/A'} / 100 |

We found {len(findings)} issues or recommendations. Please review the detailed comments below.
"""

        # Map findings into GitHub review comments
        comments = []
        for finding in findings:
            file_path = finding.get("file", finding.get("file_path", "unknown"))
            line = finding.get("line") or finding.get("line_number")
            # If line is missing, we don't attach line comments (they are added to the summary body)
            if not file_path or file_path == "unknown" or line is None:
                continue

            explanation = finding.get("explanation", finding.get("description", ""))
            recommendation = finding.get("recommendation", "")
            code_fix = finding.get("code_fix")

            comment_body = f"**[{finding.get('scanner', 'Review Agent').upper()}]**\n\n{explanation}\n\n*Recommendation:* {recommendation}"
            if code_fix:
                comment_body += f"\n\n```python\n{code_fix}\n```"

            comments.append({
                "path": file_path,
                "line": int(line),
                "body": comment_body,
            })

        if self._is_mock:
            logger.info(
                "github_notification_publisher_mock_mode",
                repository=repository,
                pr_number=pr_number,
                summary=summary_body,
                comments_count=len(comments),
                comments=comments,
            )
            return

        # Make the actual GitHub API request
        url = f"https://api.github.com/repos/{repository}/pulls/{pr_number}/reviews"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github.v3+json",
        }
        payload = {
            "body": summary_body,
            "event": "COMMENT",
            "comments": comments,
        }

        logger.info("github_notification_publisher_sending_request", repository=repository, pr_number=pr_number)
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            if response.status_code >= 400:
                logger.error(
                    "github_notification_publisher_failed",
                    status_code=response.status_code,
                    response=response.text,
                )
                response.raise_for_status()
            logger.info("github_notification_publisher_succeeded", repository=repository, pr_number=pr_number)
