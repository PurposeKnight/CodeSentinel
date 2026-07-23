import json
import uuid
from typing import Any

import asyncpg

from app.domain.models import AgentTask, PullRequestReview, User, UserSession
from app.domain.ports import ReviewRepository


class PostgresReviewRepository(ReviewRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def save_review(self, review: PullRequestReview) -> None:
        sql = """
            INSERT INTO pull_request_reviews (
                id, repository, pull_request_number, delivery_id, status,
                score, security_score, performance_score, architecture_score, documentation_score
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
            ) ON CONFLICT (id) DO UPDATE SET
                repository = EXCLUDED.repository,
                pull_request_number = EXCLUDED.pull_request_number,
                delivery_id = EXCLUDED.delivery_id,
                status = EXCLUDED.status,
                score = EXCLUDED.score,
                security_score = EXCLUDED.security_score,
                performance_score = EXCLUDED.performance_score,
                architecture_score = EXCLUDED.architecture_score,
                documentation_score = EXCLUDED.documentation_score,
                updated_at = CURRENT_TIMESTAMP
        """
        async with self._pool.acquire() as connection:
            await connection.execute(
                sql,
                uuid.UUID(review.id),
                review.repository,
                review.pull_request_number,
                review.delivery_id,
                review.status,
                review.score,
                review.security_score,
                review.performance_score,
                review.architecture_score,
                review.documentation_score,
            )

    async def save_task(self, task: AgentTask) -> None:
        sql = """
            INSERT INTO agent_tasks (
                id, review_id, agent, status, reason, report
            ) VALUES (
                $1, $2, $3, $4, $5, $6
            ) ON CONFLICT (id) DO UPDATE SET
                review_id = EXCLUDED.review_id,
                agent = EXCLUDED.agent,
                status = EXCLUDED.status,
                reason = EXCLUDED.reason,
                report = EXCLUDED.report,
                updated_at = CURRENT_TIMESTAMP
        """
        report_json = json.dumps(task.report) if task.report is not None else None

        async with self._pool.acquire() as connection:
            await connection.execute(
                sql,
                uuid.UUID(task.id),
                uuid.UUID(task.review_id),
                task.agent,
                task.status,
                task.reason,
                report_json,
            )

    async def get_review(self, review_id: str) -> PullRequestReview | None:
        sql = """
            SELECT id, repository, pull_request_number, delivery_id, status,
                   score, security_score, performance_score, architecture_score,
                   documentation_score, created_at, updated_at
            FROM pull_request_reviews
            WHERE id = $1
        """
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(sql, uuid.UUID(review_id))
            if not row:
                return None

            return PullRequestReview(
                id=str(row["id"]),
                repository=row["repository"],
                pull_request_number=row["pull_request_number"],
                delivery_id=row["delivery_id"],
                status=row["status"],
                score=row["score"],
                security_score=row["security_score"],
                performance_score=row["performance_score"],
                architecture_score=row["architecture_score"],
                documentation_score=row["documentation_score"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def get_tasks(self, review_id: str) -> list[AgentTask]:
        sql = """
            SELECT id, review_id, agent, status, reason, report, created_at, updated_at
            FROM agent_tasks
            WHERE review_id = $1
            ORDER BY created_at ASC
        """
        async with self._pool.acquire() as connection:
            rows = await connection.fetch(sql, uuid.UUID(review_id))
            tasks = []
            for row in rows:
                report_val = row["report"]
                report_data: dict[str, Any] | None = None
                if report_val is not None:
                    if isinstance(report_val, str):
                        report_data = json.loads(report_val)
                    elif isinstance(report_val, dict):
                        report_data = report_val

                tasks.append(
                    AgentTask(
                        id=str(row["id"]),
                        review_id=str(row["review_id"]),
                        agent=row["agent"],
                        status=row["status"],
                        reason=row["reason"],
                        report=report_data,
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            return tasks

    async def list_reviews(self) -> list[PullRequestReview]:
        sql = """
            SELECT id, repository, pull_request_number, delivery_id, status,
                   score, security_score, performance_score, architecture_score,
                   documentation_score, created_at, updated_at
            FROM pull_request_reviews
            ORDER BY created_at DESC
        """
        async with self._pool.acquire() as connection:
            rows = await connection.fetch(sql)
            reviews = []
            for row in rows:
                reviews.append(
                    PullRequestReview(
                        id=str(row["id"]),
                        repository=row["repository"],
                        pull_request_number=row["pull_request_number"],
                        delivery_id=row["delivery_id"],
                        status=row["status"],
                        score=row["score"],
                        security_score=row["security_score"],
                        performance_score=row["performance_score"],
                        architecture_score=row["architecture_score"],
                        documentation_score=row["documentation_score"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            return reviews

    async def save_user(self, user: User) -> None:
        sql = """
            INSERT INTO users (id, github_id, username, email, avatar_url, github_token, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
            ON CONFLICT (github_id) DO UPDATE
            SET username = EXCLUDED.username,
                email = EXCLUDED.email,
                avatar_url = EXCLUDED.avatar_url,
                github_token = EXCLUDED.github_token,
                updated_at = CURRENT_TIMESTAMP
        """
        async with self._pool.acquire() as connection:
            await connection.execute(
                sql,
                uuid.UUID(user.id),
                user.github_id,
                user.username,
                user.email,
                user.avatar_url,
                user.github_token,
            )

    async def get_user_by_github_id(self, github_id: int) -> User | None:
        sql = """
            SELECT id, github_id, username, email, avatar_url, github_token, created_at, updated_at
            FROM users
            WHERE github_id = $1
        """
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(sql, github_id)
            if not row:
                return None
            return User(
                id=str(row["id"]),
                github_id=row["github_id"],
                username=row["username"],
                email=row["email"],
                avatar_url=row["avatar_url"],
                github_token=row["github_token"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def get_user(self, user_id: str) -> User | None:
        sql = """
            SELECT id, github_id, username, email, avatar_url, github_token, created_at, updated_at
            FROM users
            WHERE id = $1
        """
        async with self._pool.acquire() as connection:
            try:
                user_uuid = uuid.UUID(user_id)
            except ValueError:
                return None
            row = await connection.fetchrow(sql, user_uuid)
            if not row:
                return None
            return User(
                id=str(row["id"]),
                github_id=row["github_id"],
                username=row["username"],
                email=row["email"],
                avatar_url=row["avatar_url"],
                github_token=row["github_token"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def save_session(self, session: UserSession) -> None:
        sql = """
            INSERT INTO user_sessions (session_token, user_id, expires_at)
            VALUES ($1, $2, $3)
        """
        async with self._pool.acquire() as connection:
            await connection.execute(
                sql,
                session.session_token,
                uuid.UUID(session.user_id),
                session.expires_at,
            )

    async def get_session(self, session_token: str) -> UserSession | None:
        sql = """
            SELECT session_token, user_id, expires_at, created_at
            FROM user_sessions
            WHERE session_token = $1
        """
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(sql, session_token)
            if not row:
                return None
            return UserSession(
                session_token=row["session_token"],
                user_id=str(row["user_id"]),
                expires_at=row["expires_at"],
                created_at=row["created_at"],
            )

    async def delete_session(self, session_token: str) -> None:
        sql = """
            DELETE FROM user_sessions
            WHERE session_token = $1
        """
        async with self._pool.acquire() as connection:
            await connection.execute(sql, session_token)

    async def get_repository_settings(self, repository: str) -> dict[str, Any] | None:
        sql = """
            SELECT repository, slack_webhook_url, alert_email, min_security_score, min_overall_score, enabled_agents
            FROM repository_settings
            WHERE repository = $1
        """
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(sql, repository)
            if not row:
                return None
            enabled_agents_val = row["enabled_agents"]
            enabled_agents_data = []
            if enabled_agents_val is not None:
                if isinstance(enabled_agents_val, str):
                    enabled_agents_data = json.loads(enabled_agents_val)
                elif isinstance(enabled_agents_val, list):
                    enabled_agents_data = enabled_agents_val
            return {
                "repository": row["repository"],
                "slack_webhook_url": row["slack_webhook_url"],
                "alert_email": row["alert_email"],
                "min_security_score": row["min_security_score"],
                "min_overall_score": row["min_overall_score"],
                "enabled_agents": enabled_agents_data,
            }

    async def save_repository_settings(self, repository: str, settings: dict[str, Any]) -> None:
        sql = """
            INSERT INTO repository_settings (repository, slack_webhook_url, alert_email, min_security_score, min_overall_score, enabled_agents, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
            ON CONFLICT (repository) DO UPDATE
            SET slack_webhook_url = EXCLUDED.slack_webhook_url,
                alert_email = EXCLUDED.alert_email,
                min_security_score = EXCLUDED.min_security_score,
                min_overall_score = EXCLUDED.min_overall_score,
                enabled_agents = EXCLUDED.enabled_agents,
                updated_at = CURRENT_TIMESTAMP
        """
        enabled_agents_json = json.dumps(settings.get("enabled_agents", []))
        async with self._pool.acquire() as connection:
            await connection.execute(
                sql,
                repository,
                settings.get("slack_webhook_url"),
                settings.get("alert_email"),
                settings.get("min_security_score", 70),
                settings.get("min_overall_score", 60),
                enabled_agents_json,
            )
