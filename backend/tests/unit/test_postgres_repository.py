import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.models import AgentTask, PullRequestReview
from app.infrastructure.postgres_repository import PostgresReviewRepository


@pytest.mark.asyncio
async def test_save_review_executes_correct_sql() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    repo = PostgresReviewRepository(mock_pool)
    review_id = str(uuid.uuid4())
    review = PullRequestReview(
        id=review_id,
        repository="PurposeKnight/CodeSentinel",
        pull_request_number=12,
        delivery_id="delivery-abc",
        status="pending",
    )

    await repo.save_review(review)

    mock_conn.execute.assert_called_once()
    args = mock_conn.execute.call_args[0]
    sql = args[0]
    assert "INSERT INTO pull_request_reviews" in sql
    assert args[1] == uuid.UUID(review_id)
    assert args[2] == "PurposeKnight/CodeSentinel"
    assert args[3] == 12
    assert args[4] == "delivery-abc"
    assert args[5] == "pending"


@pytest.mark.asyncio
async def test_save_task_executes_correct_sql() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    repo = PostgresReviewRepository(mock_pool)
    review_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    task = AgentTask(
        id=task_id,
        review_id=review_id,
        agent="security-agent",
        status="pending",
        reason="Run static analysis",
        report={"issues": []},
    )

    await repo.save_task(task)

    mock_conn.execute.assert_called_once()
    args = mock_conn.execute.call_args[0]
    sql = args[0]
    assert "INSERT INTO agent_tasks" in sql
    assert args[1] == uuid.UUID(task_id)
    assert args[2] == uuid.UUID(review_id)
    assert args[3] == "security-agent"
    assert args[4] == "pending"
    assert args[5] == "Run static analysis"
    assert args[6] == json.dumps({"issues": []})


@pytest.mark.asyncio
async def test_get_review_returns_mapped_model() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    review_id = uuid.uuid4()
    mock_row = {
        "id": review_id,
        "repository": "PurposeKnight/CodeSentinel",
        "pull_request_number": 42,
        "delivery_id": "delivery-xyz",
        "status": "completed",
        "score": 85,
        "security_score": 90,
        "performance_score": 80,
        "architecture_score": 85,
        "documentation_score": 90,
        "created_at": None,
        "updated_at": None,
    }
    mock_conn.fetchrow.return_value = mock_row

    repo = PostgresReviewRepository(mock_pool)
    res = await repo.get_review(str(review_id))

    assert res is not None
    assert res.id == str(review_id)
    assert res.repository == "PurposeKnight/CodeSentinel"
    assert res.pull_request_number == 42
    assert res.status == "completed"
    assert res.score == 85
    assert res.security_score == 90


@pytest.mark.asyncio
async def test_get_tasks_returns_mapped_models() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    review_id = uuid.uuid4()
    task_id = uuid.uuid4()
    mock_rows = [
        {
            "id": task_id,
            "review_id": review_id,
            "agent": "security-agent",
            "status": "pending",
            "reason": "Test",
            "report": '{"status":"ok"}',
            "created_at": None,
            "updated_at": None,
        }
    ]
    mock_conn.fetch.return_value = mock_rows

    repo = PostgresReviewRepository(mock_pool)
    res = await repo.get_tasks(str(review_id))

    assert len(res) == 1
    assert res[0].id == str(task_id)
    assert res[0].review_id == str(review_id)
    assert res[0].agent == "security-agent"
    assert res[0].report == {"status": "ok"}
