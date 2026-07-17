from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.dependencies.services import get_review_repository
from app.domain.models import AgentTask, PullRequestReview
from app.main import create_app


@pytest.fixture
def mock_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_repository: AsyncMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_review_repository] = lambda: mock_repository
    return TestClient(app)


def test_list_reviews_endpoint(client: TestClient, mock_repository: AsyncMock) -> None:
    mock_reviews = [
        PullRequestReview(
            id="a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1",
            repository="org/repo1",
            pull_request_number=10,
            delivery_id="del-1",
            status="completed",
            score=85,
        ),
        PullRequestReview(
            id="b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2",
            repository="org/repo2",
            pull_request_number=20,
            delivery_id="del-2",
            status="pending",
        ),
    ]
    mock_repository.list_reviews.return_value = mock_reviews

    response = client.get("/api/v1/reviews")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["repository"] == "org/repo1"
    assert data[0]["score"] == 85
    assert data[1]["repository"] == "org/repo2"
    assert data[1]["score"] is None
    mock_repository.list_reviews.assert_called_once()


def test_get_review_detail_endpoint(client: TestClient, mock_repository: AsyncMock) -> None:
    review_id = "a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1"
    mock_review = PullRequestReview(
        id=review_id,
        repository="org/repo1",
        pull_request_number=10,
        delivery_id="del-1",
        status="completed",
        score=85,
    )
    mock_tasks = [
        AgentTask(
            id="t1",
            review_id=review_id,
            agent="security-agent",
            status="completed",
            report={"findings": []},
        )
    ]
    mock_repository.get_review.return_value = mock_review
    mock_repository.get_tasks.return_value = mock_tasks

    response = client.get(f"/api/v1/reviews/{review_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == review_id
    assert data["repository"] == "org/repo1"
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["agent"] == "security-agent"
    mock_repository.get_review.assert_called_once_with(review_id)
    mock_repository.get_tasks.assert_called_once_with(review_id)


def test_get_review_detail_not_found(client: TestClient, mock_repository: AsyncMock) -> None:
    review_id = "nonexistent-id"
    mock_repository.get_review.return_value = None

    response = client.get(f"/api/v1/reviews/{review_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]
    mock_repository.get_review.assert_called_once_with(review_id)
