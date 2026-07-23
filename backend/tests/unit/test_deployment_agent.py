import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aio_pika.abc import AbstractIncomingMessage

from app.core.config import Settings
from app.domain.models import AgentTask, PullRequestReview
from app.services.deployment_agent_service import DeploymentAgentService
from app.workers.deployment_worker import DeploymentWorker


@pytest.mark.asyncio
async def test_deployment_gates_evaluation() -> None:
    service = DeploymentAgentService()

    # Pass case
    passed, reason = await service.evaluate_gates({"score": 75, "security_score": 80})
    assert passed is True
    assert "passed" in reason.lower()

    # Security score below threshold
    passed, reason = await service.evaluate_gates({"score": 75, "security_score": 50})
    assert passed is False
    assert "security score" in reason.lower()

    # Overall score below threshold
    passed, reason = await service.evaluate_gates({"score": 55, "security_score": 80})
    assert passed is False
    assert "overall quality score" in reason.lower()


@pytest.mark.asyncio
async def test_deployment_health_check() -> None:
    service = DeploymentAgentService(api_url="http://mock-api")

    # Mock dynamic endpoint checks
    with patch("httpx.AsyncClient.get") as mock_get:
        # Mock API returning healthy status
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ready"}
        mock_get.return_value = mock_response

        healthy, msg = await service.verify_health()
        assert healthy is True
        assert "probe succeeded" in msg.lower()


@pytest.mark.asyncio
async def test_deployment_worker_message_processing() -> None:
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

    mock_service.trigger_deployment.return_value = {
        "environment": "staging",
        "deployment_id": "dep-mock",
        "url": "http://staging.mock",
    }
    mock_service.verify_health.return_value = (True, "Ready status returned.")

    mock_coordinator = AsyncMock()
    worker = DeploymentWorker(settings, mock_repo, mock_service, mock_coordinator)

    # Mock incoming message
    message = MagicMock(spec=AbstractIncomingMessage)
    message.body = json.dumps({
        "review_id": "a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1",
        "task_id": "b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2",
        "repository": "org/repo",
        "pull_request_number": 42,
    }).encode("utf-8")

    async_context = AsyncMock()
    message.process.return_value = async_context

    with patch("asyncio.sleep", return_value=None):
        await worker._handle_message(message)

    # Verify task saves (1 for running state, 1 for completed state)
    assert mock_repo.save_task.call_count == 2
    assert mock_service.trigger_deployment.call_count == 1
    assert mock_service.verify_health.call_count == 1

    # Verify coordinator check_and_finalize_review gets called at end
    mock_coordinator.check_and_finalize_review.assert_called_once_with("a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1")
