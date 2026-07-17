import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aio_pika.abc import AbstractIncomingMessage

from app.core.config import Settings
from app.domain.models import AgentTask, PullRequestReview
from app.infrastructure.openai_test_analyzer import OpenAITestAnalyzer
from app.services.testing_agent_service import TestingAgentService
from app.workers.testing_worker import TestingWorker


@pytest.mark.asyncio
async def test_openai_test_analyzer_mock_mode() -> None:
    settings = Settings(openai_api_key="mock-key")
    analyzer = OpenAITestAnalyzer(settings)
    report = await analyzer.analyze_tests("/tmp/dir")

    assert len(report["findings"]) == 1
    assert report["findings"][0]["file"] == "app/main.py"


@pytest.mark.asyncio
async def test_testing_agent_service_coordinates_flow() -> None:
    mock_git = AsyncMock()
    mock_analyzer = AsyncMock()
    mock_analyzer.analyze_tests.return_value = {
        "findings": [{"file": "app/main.py", "test_status": "partial"}],
    }

    service = TestingAgentService(mock_git, mock_analyzer)
    report = await service.run_testing_analysis("org/repo", 42)

    assert len(report["findings"]) == 1
    assert mock_git.clone_and_checkout_pr.call_count == 1
    assert mock_analyzer.analyze_tests.call_count == 1


@pytest.mark.asyncio
async def test_testing_worker_message_processing() -> None:
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
        architecture_score=90,
    )
    mock_repo.get_review.return_value = mock_review

    mock_service.run_testing_analysis.return_value = {
        "findings": [],
    }

    mock_coordinator = AsyncMock()
    worker = TestingWorker(settings, mock_repo, mock_service, mock_coordinator)

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
    # Verify save_review is called to update overall score (since security=80, architecture=90 -> average=85)
    assert mock_repo.save_review.call_count == 1
    saved_review = mock_repo.save_review.call_args[0][0]
    assert saved_review.score == 85

    # Verify coordinator finalization is called
    mock_coordinator.check_and_finalize_review.assert_called_once_with("a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1")
