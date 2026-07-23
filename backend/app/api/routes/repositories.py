from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Cookie, status

from app.core.config import get_settings, Settings
from app.api.dependencies.services import get_review_repository
from app.domain.ports import ReviewRepository
from app.schemas.repositories import RepositoryResponse, LinkRepositoryRequest, RepositorySettingsResponse, RepositorySettingsUpdate

router = APIRouter()


async def get_current_user_from_session(
    repository: Annotated[ReviewRepository, Depends(get_review_repository)],
    session_token: str | None = Cookie(default=None),
):
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token cookie missing.",
        )
    session = await repository.get_session(session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )
    user = await repository.get_user(session.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorized user record not found.",
        )
    return user


@router.get(
    "/repositories",
    response_model=list[RepositoryResponse],
    status_code=status.HTTP_200_OK,
)
async def list_repositories(
    user: Annotated[Any, Depends(get_current_user_from_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[RepositoryResponse]:
    # We will use Redis client to query linked repos
    import redis
    r_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password.get_secret_value() if settings.redis_password else None,
        decode_responses=True,
    )
    linked_repos = r_client.smembers("codesentinel:linked_repos") or set()

    if user.github_token.startswith("mock-"):
        # Mock repositories for local testing
        mock_repos = [
            RepositoryResponse(
                id=1,
                name="flask",
                full_name="pallets/flask",
                html_url="https://github.com/pallets/flask",
                description="A simple framework for building complex web applications.",
                is_linked="pallets/flask" in linked_repos,
            ),
            RepositoryResponse(
                id=2,
                name="django",
                full_name="django/django",
                html_url="https://github.com/django/django",
                description="The Web framework for perfectionists with deadlines.",
                is_linked="django/django" in linked_repos,
            ),
            RepositoryResponse(
                id=3,
                name="requests",
                full_name="psf/requests",
                html_url="https://github.com/psf/requests",
                description="A simple, friendly HTTP library for Python.",
                is_linked="psf/requests" in linked_repos,
            ),
            RepositoryResponse(
                id=4,
                name="fastapi",
                full_name="fastapi/fastapi",
                html_url="https://github.com/fastapi/fastapi",
                description="FastAPI framework, high performance, easy to learn, fast to code, ready for production",
                is_linked="fastapi/fastapi" in linked_repos,
            ),
        ]
        return mock_repos

    # Real GitHub API fetch
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://api.github.com/user/repos?per_page=100&type=owner",
                headers={
                    "Authorization": f"Bearer {user.github_token}",
                    "User-Agent": "CodeSentinel-API",
                },
            )
            if res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch user repositories from GitHub.",
                )
            repos_data = res.json()
            
            repos = []
            for r in repos_data:
                repos.append(
                    RepositoryResponse(
                        id=r["id"],
                        name=r["name"],
                        full_name=r["full_name"],
                        html_url=r["html_url"],
                        description=r.get("description"),
                        is_linked=r["full_name"] in linked_repos,
                    )
                )
            return repos
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub repository fetch error: {str(e)}",
        )


@router.post(
    "/repositories/link",
    status_code=status.HTTP_200_OK,
)
async def link_repository(
    request: LinkRepositoryRequest,
    user: Annotated[Any, Depends(get_current_user_from_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    import redis
    r_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password.get_secret_value() if settings.redis_password else None,
        decode_responses=True,
    )
    
    repo_name = request.repository

    if user.github_token.startswith("mock-"):
        # Toggles linked status locally
        r_client.sadd("codesentinel:linked_repos", repo_name)
        return {"success": True, "message": f"Successfully mock-linked repository {repo_name}"}

    # Real GitHub API Webhook Registration
    webhook_secret = settings.github_webhook_secret.get_secret_value()
    # Replace public_url placeholder or redirect
    public_url = f"http://{settings.github_redirect_uri.split('/')[2]}/api/v1/webhooks/github" if settings.github_redirect_uri else "http://localhost:8000/api/v1/webhooks/github"
    
    try:
        async with httpx.AsyncClient() as client:
            hook_res = await client.post(
                f"https://api.github.com/repos/{repo_name}/hooks",
                json={
                    "name": "web",
                    "active": True,
                    "events": ["pull_request"],
                    "config": {
                        "url": public_url,
                        "content_type": "json",
                        "secret": webhook_secret,
                    },
                },
                headers={
                    "Authorization": f"Bearer {user.github_token}",
                    "User-Agent": "CodeSentinel-API",
                    "Accept": "application/vnd.github+json",
                },
            )
            if hook_res.status_code not in (200, 201):
                # If webhook already exists, register it in Redis anyway
                if "already exists" in hook_res.text:
                    r_client.sadd("codesentinel:linked_repos", repo_name)
                    return {"success": True, "message": "Webhook already exists on GitHub, registered internally."}
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"GitHub hook creation failed: {hook_res.text}",
                )

            r_client.sadd("codesentinel:linked_repos", repo_name)
            return {"success": True, "message": f"Successfully registered webhook on GitHub for {repo_name}"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering GitHub webhook: {str(e)}",
        )


@router.post(
    "/repositories/unlink",
    status_code=status.HTTP_200_OK,
)
async def unlink_repository(
    request: LinkRepositoryRequest,
    user: Annotated[Any, Depends(get_current_user_from_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    import redis
    r_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password.get_secret_value() if settings.redis_password else None,
        decode_responses=True,
    )
    
    repo_name = request.repository
    r_client.srem("codesentinel:linked_repos", repo_name)
    return {"success": True, "message": f"Successfully unlinked repository {repo_name}"}


@router.get(
    "/repositories/{owner}/{repo}/settings",
    response_model=RepositorySettingsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_repo_settings(
    owner: str,
    repo: str,
    user: Annotated[Any, Depends(get_current_user_from_session)],
    repository: Annotated[ReviewRepository, Depends(get_review_repository)],
) -> RepositorySettingsResponse:
    repo_full_name = f"{owner}/{repo}"
    settings = await repository.get_repository_settings(repo_full_name)
    if not settings:
        return RepositorySettingsResponse(
            repository=repo_full_name,
            slack_webhook_url=None,
            alert_email=None,
            min_security_score=70,
            min_overall_score=60,
            enabled_agents=["security-agent", "code-review-agent", "testing-agent", "documentation-agent", "deployment-agent"],
        )
    return RepositorySettingsResponse(**settings)


@router.post(
    "/repositories/{owner}/{repo}/settings",
    status_code=status.HTTP_200_OK,
)
async def update_repo_settings(
    owner: str,
    repo: str,
    update_data: RepositorySettingsUpdate,
    user: Annotated[Any, Depends(get_current_user_from_session)],
    repository: Annotated[ReviewRepository, Depends(get_review_repository)],
):
    repo_full_name = f"{owner}/{repo}"
    settings_dict = {
        "slack_webhook_url": update_data.slack_webhook_url,
        "alert_email": update_data.alert_email,
        "min_security_score": update_data.min_security_score,
        "min_overall_score": update_data.min_overall_score,
        "enabled_agents": update_data.enabled_agents,
    }
    await repository.save_repository_settings(repo_full_name, settings_dict)
    return {"success": True, "message": f"Successfully updated settings for {repo_full_name}"}
