import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aio_pika.abc import AbstractIncomingMessage

from app.core.config import Settings
from app.domain.models import AgentTask, PullRequestReview
from app.infrastructure.openai_code_reviewer import OpenAICodeReviewer
from app.services.code_review_agent_service import CodeReviewAgentService
from app.workers.code_review_worker import CodeReviewWorker, run_worker


@pytest.mark.asyncio
async def test_openai_code_reviewer_mock_mode() -> None:
    settings = Settings(openai_api_key="mock-key")
    reviewer = OpenAICodeReviewer(settings)
    report = await reviewer.review_code("some-diff")

    assert report["architecture_score"] == 90
    assert report["performance_score"] == 85
    assert len(report["findings"]) == 1


@pytest.mark.asyncio
async def test_code_review_agent_service_coordinates_flow() -> None:
    mock_git = AsyncMock()
    mock_git.get_diff.return_value = "git-diff"
    mock_reviewer = AsyncMock()
    mock_reviewer.review_code.return_value = {
        "architecture_score": 95,
        "performance_score": 90,
        "findings": [{"file": "main.py", "explanation": "Looks good"}],
    }

    service = CodeReviewAgentService(mock_git, mock_reviewer)
    report = await service.run_code_review("org/repo", 42)

    assert report["architecture_score"] == 95
    assert report["performance_score"] == 90
    assert mock_git.clone_and_checkout_pr.call_count == 1
    assert mock_git.get_diff.call_count == 1


@pytest.mark.asyncio
async def test_code_review_worker_message_processing() -> None:
    settings = Settings()
    mock_repo = AsyncMock()
    mock_service = AsyncMock()
    
    mock_review = PullRequestReview(
        id="a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1",
        repository="org/repo",
        pull_request_number=42,
        delivery_id="delivery-id",
        status="pending",
        security_score=80,
    )
    mock_repo.get_review.return_value = mock_review

    mock_service.run_code_review.return_value = {
        "architecture_score": 90,
        "performance_score": 80,
        "findings": [],
    }

    worker = CodeReviewWorker(settings, mock_repo, mock_service)

    # Mock incoming message
    message = MagicMock(spec=AbstractIncomingMessage)
    message.body = json.dumps({
        "review_id": "a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1",
        "task_id": "b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2",
        "repository": "org/repo",
        "pull_request_number": 42,
    }).encode("utf-8")

    # Mock processing context manager
    async_context = AsyncMock()
    message.process.return_value = async_context

    await worker._handle_message(message)

    # Verify task updates
    assert mock_repo.save_task.call_count == 2
    # Verify save_review is called with the calculated overall score:
    # Security=80, Performance=80, Architecture=90 -> Average = 83
    assert mock_repo.save_review.call_count == 1
    saved_review = mock_repo.save_review.call_args[0][0]
    assert saved_review.architecture_score == 90
    assert saved_review.performance_score == 80
    assert saved_review.score == 83
