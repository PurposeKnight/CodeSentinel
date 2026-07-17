from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.dependencies.services import get_review_repository
from app.domain.models import User, UserSession
from app.main import create_app


@pytest.fixture
def mock_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_repository: AsyncMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_review_repository] = lambda: mock_repository
    return TestClient(app)


def test_auth_login_redirect(client: TestClient) -> None:
    # In mock configuration mode, login redirects straight to callback
    response = client.get("/api/v1/auth/login", follow_redirects=False)
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert "auth/callback?code=mock-code" in response.headers["location"]


def test_auth_callback_flow(client: TestClient, mock_repository: AsyncMock) -> None:
    mock_repository.get_user_by_github_id.return_value = None

    response = client.get("/api/v1/auth/callback?code=mock-code", follow_redirects=False)

    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["location"] == "http://localhost:3000/"
    assert "session_token" in response.cookies

    # Check save operations called
    assert mock_repository.save_user.call_count == 1
    assert mock_repository.save_session.call_count == 1

    saved_user = mock_repository.save_user.call_args[0][0]
    assert saved_user.username == "mock-user"
    assert saved_user.github_id == 999999


def test_auth_me_authenticated(client: TestClient, mock_repository: AsyncMock) -> None:
    session_token = "valid-session-token"
    mock_session = UserSession(
        session_token=session_token,
        user_id="user-123",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    mock_user = User(
        id="user-123",
        github_id=999999,
        username="mock-user",
        email="mock@example.com",
        avatar_url="http://avatar",
        github_token="token",
    )
    mock_repository.get_session.return_value = mock_session
    mock_repository.get_user.return_value = mock_user

    # Set session cookie in request
    client.cookies.set("session_token", session_token)
    response = client.get("/api/v1/auth/me")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "mock-user"
    assert data["github_id"] == 999999
    mock_repository.get_session.assert_called_once_with(session_token)
    mock_repository.get_user.assert_called_once_with("user-123")


def test_auth_me_expired_session(client: TestClient, mock_repository: AsyncMock) -> None:
    session_token = "expired-session-token"
    mock_session = UserSession(
        session_token=session_token,
        user_id="user-123",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    mock_repository.get_session.return_value = mock_session

    client.cookies.set("session_token", session_token)
    response = client.get("/api/v1/auth/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "expired" in response.json()["detail"]
    mock_repository.delete_session.assert_called_once_with(session_token)


def test_auth_me_unauthorized(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "missing" in response.json()["detail"]


def test_auth_logout(client: TestClient, mock_repository: AsyncMock) -> None:
    session_token = "session-to-revoke"
    client.cookies.set("session_token", session_token)

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True
    # The session_token cookie is deleted via response Set-Cookie header
    set_cookie = response.headers.get("set-cookie", "")
    assert "session_token=" in set_cookie
    assert "max-age=0" in set_cookie.lower() or "expires=" in set_cookie.lower()
    mock_repository.delete_session.assert_called_once_with(session_token)
