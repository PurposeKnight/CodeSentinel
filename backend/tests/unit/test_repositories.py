from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.dependencies.services import get_review_repository
from app.core.config import Settings
from app.domain.models import User, UserSession
from app.infrastructure.slack_notifier import SlackNotificationPublisher
from app.main import create_app


@pytest.fixture
def mock_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_repository: AsyncMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_review_repository] = lambda: mock_repository
    return TestClient(app)


@patch("redis.Redis")
def test_list_repositories_mock_flow(mock_redis_class: MagicMock, client: TestClient, mock_repository: AsyncMock) -> None:
    # Setup mock user and session
    session_token = "valid-session-token"
    mock_user = User(
        id="user-123",
        github_id=999999,
        username="mock-user",
        email="mock@example.com",
        avatar_url="http://avatar",
        github_token="mock-access-token", # triggers mock repository listing
    )
    mock_session = UserSession(
        session_token=session_token,
        user_id="user-123",
        expires_at=None,
    )
    mock_repository.get_session.return_value = mock_session
    mock_repository.get_user.return_value = mock_user

    # Mock Redis responses
    mock_redis = MagicMock()
    mock_redis.smembers.return_value = {"pallets/flask"}
    mock_redis_class.return_value = mock_redis

    client.cookies.set("session_token", session_token)
    response = client.get("/api/v1/repositories")

    assert response.status_code == status.HTTP_200_OK
    repos = response.json()
    assert len(repos) == 4
    # Check is_linked calculation
    flask_repo = next(r for r in repos if r["full_name"] == "pallets/flask")
    assert flask_repo["is_linked"] is True
    django_repo = next(r for r in repos if r["full_name"] == "django/django")
    assert django_repo["is_linked"] is False


@patch("redis.Redis")
def test_link_repository_mock_flow(mock_redis_class: MagicMock, client: TestClient, mock_repository: AsyncMock) -> None:
    session_token = "valid-session-token"
    mock_user = User(
        id="user-123",
        github_id=999999,
        username="mock-user",
        email="mock@example.com",
        avatar_url="http://avatar",
        github_token="mock-access-token",
    )
    mock_session = UserSession(
        session_token=session_token,
        user_id="user-123",
        expires_at=None,
    )
    mock_repository.get_session.return_value = mock_session
    mock_repository.get_user.return_value = mock_user

    mock_redis = MagicMock()
    mock_redis_class.return_value = mock_redis

    client.cookies.set("session_token", session_token)
    response = client.post("/api/v1/repositories/link", json={"repository": "pallets/flask"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True
    mock_redis.sadd.assert_called_once_with("codesentinel:linked_repos", "pallets/flask")


@patch("redis.Redis")
def test_unlink_repository_mock_flow(mock_redis_class: MagicMock, client: TestClient, mock_repository: AsyncMock) -> None:
    session_token = "valid-session-token"
    mock_user = User(
        id="user-123",
        github_id=999999,
        username="mock-user",
        email="mock@example.com",
        avatar_url="http://avatar",
        github_token="mock-access-token",
    )
    mock_session = UserSession(
        session_token=session_token,
        user_id="user-123",
        expires_at=None,
    )
    mock_repository.get_session.return_value = mock_session
    mock_repository.get_user.return_value = mock_user

    mock_redis = MagicMock()
    mock_redis_class.return_value = mock_redis

    client.cookies.set("session_token", session_token)
    response = client.post("/api/v1/repositories/unlink", json={"repository": "pallets/flask"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True
    mock_redis.srem.assert_called_once_with("codesentinel:linked_repos", "pallets/flask")


@pytest.mark.anyio
async def test_slack_notifier_mock_mode() -> None:
    settings = Settings(
        slack_webhook_url="mock-slack-url"
    )
    publisher = SlackNotificationPublisher(settings)
    
    # Should not raise exception, but log mock operation
    await publisher.publish_review_alert(
        repository="pallets/flask",
        pr_number=42,
        score=90,
        status="completed",
        findings_count=0,
        review_id="review-abc",
    )
