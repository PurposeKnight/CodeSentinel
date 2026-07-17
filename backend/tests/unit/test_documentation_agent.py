import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aio_pika.abc import AbstractIncomingMessage

from app.core.config import Settings
from app.domain.models import AgentTask, PullRequestReview
from app.infrastructure.openai_doc_analyzer import OpenAIDocAnalyzer
from app.services.documentation_agent_service import DocumentationAgentService
from app.workers.documentation_worker import DocumentationWorker


@pytest.mark.asyncio
async def test_openai_doc_analyzer_mock_mode() -> None:
    settings = Settings(openai_api_key="mock-key")
    analyzer = OpenAIDocAnalyzer(settings)
    report = await analyzer.analyze_documentation("/tmp/dir")

    assert report["documentation_score"] == 95
    assert len(report["findings"]) == 1


@pytest.mark.asyncio
async def test_documentation_agent_service_coordinates_flow() -> None:
    mock_git = AsyncMock()
    mock_analyzer = AsyncMock()
    mock_analyzer.analyze_documentation.return_value = {
        "documentation_score": 90,
        "findings": [{"file": "README.md", "explanation": "Looks fine"}],
    }

    service = DocumentationAgentService(mock_git, mock_analyzer)
    report = await service.run_documentation_analysis("org/repo", 42)

    assert report["documentation_score"] == 90
    assert len(report["findings"]) == 1
    assert mock_git.clone_and_checkout_pr.call_count == 1
    assert mock_analyzer.analyze_documentation.call_count == 1


@pytest.mark.asyncio
async def test_documentation_worker_message_processing() -> None:
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

    mock_service.run_documentation_analysis.return_value = {
        "documentation_score": 90,
        "findings": [],
    }

    worker = DocumentationWorker(settings, mock_repo, mock_service)

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
    # Security=80, Documentation=90 -> Average = 85
    assert mock_repo.save_review.call_count == 1
    saved_review = mock_repo.save_review.call_args[0][0]
    assert saved_review.documentation_score == 90
    assert saved_review.score == 85
