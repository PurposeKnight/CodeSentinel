import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from app.api.dependencies.services import get_review_repository
from app.domain.models import User
from app.services.health_service import HealthService
from app.main import create_app


@pytest.fixture
def mock_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_repository: AsyncMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_review_repository] = lambda: mock_repository
    return TestClient(app)


@pytest.mark.asyncio
async def test_get_repository_settings_fallback_default(client: TestClient, mock_repository: AsyncMock) -> None:
    mock_user = User(
        id="u1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1",
        github_id=12345,
        username="test-user",
        email="test@email.com",
        avatar_url=None,
        github_token="mock-token",
    )
    
    mock_repository.get_session.return_value = MagicMock(user_id=mock_user.id)
    mock_repository.get_user.return_value = mock_user
    mock_repository.get_repository_settings.return_value = None  # Mocking no settings in DB

    response = client.get(
        "/api/v1/repositories/owner-test/repo-test/settings",
        cookies={"session_token": "valid-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["repository"] == "owner-test/repo-test"
    assert data["min_security_score"] == 70
    assert data["min_overall_score"] == 60
    assert "security-agent" in data["enabled_agents"]


@pytest.mark.asyncio
async def test_save_repository_settings(client: TestClient, mock_repository: AsyncMock) -> None:
    mock_user = User(
        id="u1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1",
        github_id=12345,
        username="test-user",
        email="test@email.com",
        avatar_url=None,
        github_token="mock-token",
    )
    
    mock_repository.get_session.return_value = MagicMock(user_id=mock_user.id)
    mock_repository.get_user.return_value = mock_user

    payload = {
        "slack_webhook_url": "https://hooks.slack.com/services/new-mock-webhook",
        "alert_email": "alerts@test.com",
        "min_security_score": 85,
        "min_overall_score": 75,
        "enabled_agents": ["security-agent", "code-review-agent"]
    }

    response = client.post(
        "/api/v1/repositories/owner-test/repo-test/settings",
        json=payload,
        cookies={"session_token": "valid-token"}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    mock_repository.save_repository_settings.assert_called_once_with(
        "owner-test/repo-test",
        {
            "slack_webhook_url": "https://hooks.slack.com/services/new-mock-webhook",
            "alert_email": "alerts@test.com",
            "min_security_score": 85,
            "min_overall_score": 75,
            "enabled_agents": ["security-agent", "code-review-agent"]
        }
    )


@pytest.mark.asyncio
async def test_health_service_detailed_report() -> None:
    mock_pool = MagicMock()
    mock_redis = AsyncMock()
    mock_publisher = AsyncMock()
    
    # Return online/offline heartbeat values
    mock_redis.get.side_effect = lambda key: "online" if "planner-worker" in key else None

    # Mock postgres connection success
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchval.return_value = 1
    
    # Mock rabbitmq publisher success
    mock_publisher.check.return_value = None

    service = HealthService(mock_pool, mock_redis, mock_publisher)
    report = await service.check_detailed_dependencies()
    
    assert report["dependencies"]["postgres"]["status"] == "ok"
    assert report["dependencies"]["redis"]["status"] == "ok"
    assert report["dependencies"]["rabbitmq"]["status"] == "ok"
    assert report["workers"]["planner-worker"] == "online"
    assert report["workers"]["security-worker"] == "offline"
