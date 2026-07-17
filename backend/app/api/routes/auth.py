import secrets
from datetime import datetime, timezone, timedelta
from typing import Annotated
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, status
from fastapi.responses import RedirectResponse

from app.core.config import get_settings, Settings
from app.api.dependencies.services import get_review_repository
from app.domain.ports import ReviewRepository
from app.domain.models import User, UserSession
from app.schemas.auth import UserResponse

router = APIRouter()


@router.get("/auth/login")
async def login(settings: Annotated[Settings, Depends(get_settings)]):
    if not settings.github_client_id or settings.github_client_id == "mock-client-id":
        # In mock/development mode, redirect directly to callback with mock code
        return RedirectResponse(url="/api/v1/auth/callback?code=mock-code")

    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={settings.github_redirect_uri}"
        f"&scope=repo,user"
    )
    return RedirectResponse(url=url)


@router.get("/auth/callback")
async def callback(
    code: str,
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[ReviewRepository, Depends(get_review_repository)],
):
    if not settings.github_client_id or settings.github_client_id == "mock-client-id" or code == "mock-code":
        # Mock/development flow
        github_id = 999999
        username = "mock-user"
        email = "mock-user@example.com"
        avatar_url = "https://avatars.githubusercontent.com/u/999999"
        access_token = "mock-access-token"
    else:
        # Production flow: Exchange OAuth code for token
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret.get_secret_value() if settings.github_client_secret else "",
                    "code": code,
                    "redirect_uri": settings.github_redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            if token_res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code for token.",
                )
            token_data = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="GitHub OAuth exchange did not return an access token.",
                )

            # Fetch authenticated user profile details
            user_res = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "User-Agent": "CodeSentinel-API",
                },
            )
            if user_res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch user profile details from GitHub API.",
                )
            user_data = user_res.json()
            github_id = user_data["id"]
            username = user_data["login"]
            email = user_data.get("email")
            avatar_url = user_data.get("avatar_url")

    # Get or create user in DB
    user = await repository.get_user_by_github_id(github_id)
    if not user:
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            github_id=github_id,
            username=username,
            email=email,
            avatar_url=avatar_url,
            github_token=access_token,
        )
        await repository.save_user(user)
    else:
        # Update details and token
        user = User(
            id=user.id,
            github_id=github_id,
            username=username,
            email=email,
            avatar_url=avatar_url,
            github_token=access_token,
        )
        await repository.save_user(user)

    # Generate session token and save session
    session_token = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session = UserSession(
        session_token=session_token,
        user_id=user.id,
        expires_at=expires_at,
    )
    await repository.save_session(session)

    # Redirect to Next.js dashboard and set session cookie
    response = RedirectResponse(url="http://localhost:3000/")
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=7 * 24 * 60 * 60,
    )
    return response


@router.get("/auth/me", response_model=UserResponse)
async def me(
    repository: Annotated[ReviewRepository, Depends(get_review_repository)],
    session_token: str | None = Cookie(default=None),
) -> UserResponse:
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token cookie missing.",
        )

    session = await repository.get_session(session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token.",
        )

    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        await repository.delete_session(session_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User session expired.",
        )

    user = await repository.get_user(session.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorized user record not found.",
        )

    return UserResponse.model_validate(user)


@router.post("/auth/logout")
async def logout(
    response: Response,
    repository: Annotated[ReviewRepository, Depends(get_review_repository)],
    session_token: str | None = Cookie(default=None),
):
    if session_token:
        await repository.delete_session(session_token)
    response.delete_cookie(key="session_token")
    return {"success": True}
