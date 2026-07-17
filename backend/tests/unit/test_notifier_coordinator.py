from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.domain.models import AgentTask, PullRequestReview
from app.infrastructure.github_notifier import GitHubNotificationPublisher
from app.services.review_coordinator import ReviewCoordinator


@pytest.mark.asyncio
async def test_github_notification_publisher_mock() -> None:
    settings = Settings(github_token="mock-token")
    notifier = GitHubNotificationPublisher(settings)

    # Calling publish should succeed in mock mode
    await notifier.publish_pr_review(
        repository="org/repo",
        pr_number=42,
        review_summary={"score": 80},
        findings=[{"file": "main.py", "line": 10, "explanation": "Vulnerability info", "recommendation": "Fix it"}],
    )


@pytest.mark.asyncio
async def test_review_coordinator_tasks_pending() -> None:
    mock_repo = AsyncMock()
    mock_notifier = AsyncMock()

    review = PullRequestReview(
        id="a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1",
        repository="org/repo",
        pull_request_number=42,
        delivery_id="delivery-1",
        status="pending",
    )
    mock_repo.get_review.return_value = review

    # One pending task, one completed
    tasks = [
        AgentTask(id="t1", review_id=review.id, agent="security-agent", status="completed"),
        AgentTask(id="t2", review_id=review.id, agent="code-review-agent", status="pending"),
    ]
    mock_repo.get_tasks.return_value = tasks

    coordinator = ReviewCoordinator(mock_repo, mock_notifier)
    await coordinator.check_and_finalize_review(review.id)

    # Should not save review status to completed/failed
    assert mock_repo.save_review.call_count == 0
    # Should not notify
    assert mock_notifier.publish_pr_review.call_count == 0


@pytest.mark.asyncio
async def test_review_coordinator_all_tasks_completed() -> None:
    mock_repo = AsyncMock()
    mock_notifier = AsyncMock()

    review = PullRequestReview(
        id="a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1",
        repository="org/repo",
        pull_request_number=42,
        delivery_id="delivery-1",
        status="pending",
        security_score=80,
        architecture_score=90,
    )
    mock_repo.get_review.return_value = review

    # Both completed
    tasks = [
        AgentTask(
            id="t1",
            review_id=review.id,
            agent="security-agent",
            status="completed",
            report={"findings": [{"file": "main.py", "line": 5, "explanation": "Vuln description"}]},
        ),
        AgentTask(
            id="t2",
            review_id=review.id,
            agent="code-review-agent",
            status="completed",
            report={"findings": [{"file": "app.py", "line": 12, "explanation": "Code issue"}]},
        ),
    ]
    mock_repo.get_tasks.return_value = tasks

    coordinator = ReviewCoordinator(mock_repo, mock_notifier)
    await coordinator.check_and_finalize_review(review.id)

    # Should save review status to completed
    assert mock_repo.save_review.call_count == 1
    updated_review = mock_repo.save_review.call_args[0][0]
    assert updated_review.status == "completed"
    assert updated_review.score == 85  # Average of 80 and 90

    # Should notify
    assert mock_notifier.publish_pr_review.call_count == 1
    call_args = mock_notifier.publish_pr_review.call_args[1]
    assert call_args["repository"] == "org/repo"
    assert call_args["pr_number"] == 42
    assert len(call_args["findings"]) == 2
