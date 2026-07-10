import json
import uuid
from typing import Any

import asyncpg

from app.domain.models import AgentTask, PullRequestReview
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
