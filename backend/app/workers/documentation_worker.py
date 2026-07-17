import asyncio
import json
import signal
from collections.abc import Callable
from contextlib import suppress

from aio_pika.abc import AbstractIncomingMessage

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.domain.models import AgentTask, PullRequestReview
from app.domain.ports import ReviewRepository
from app.infrastructure.database import close_postgres_pool, create_postgres_pool, init_db
from app.infrastructure.git_service import GitService
from app.infrastructure.github_notifier import GitHubNotificationPublisher
from app.infrastructure.slack_notifier import SlackNotificationPublisher
from app.infrastructure.openai_doc_analyzer import OpenAIDocAnalyzer
from app.infrastructure.postgres_repository import PostgresReviewRepository
from app.infrastructure.rabbitmq import connect_with_retry, declare_all_topology
from app.services.documentation_agent_service import DocumentationAgentService
from app.services.review_coordinator import ReviewCoordinator

logger = get_logger(__name__)


class DocumentationWorker:
    def __init__(
        self,
        settings: Settings,
        repository: ReviewRepository,
        documentation_service: DocumentationAgentService,
        coordinator: ReviewCoordinator,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._documentation_service = documentation_service
        self._coordinator = coordinator
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        configure_logging(self._settings)
        logger.info("documentation_worker_starting")

        connection = await connect_with_retry(self._settings)
        channel = await connection.channel()
        # 1 task at a time to prevent resource starvation during concurrency
        await channel.set_qos(prefetch_count=1)

        await declare_all_topology(channel, self._settings)
        queue = await channel.declare_queue(
            "codesentinel.tasks.documentation",
            durable=True,
        )

        await queue.consume(self._handle_message)
        logger.info("documentation_worker_consuming", queue="codesentinel.tasks.documentation")

        try:
            await self._stop_event.wait()
        finally:
            logger.info("documentation_worker_stopping")
            await channel.close()
            await connection.close()

    async def stop(self) -> None:
        self._stop_event.set()

    async def _handle_message(self, message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                payload = json.loads(message.body.decode("utf-8"))
            except Exception as exc:
                logger.error("documentation_worker_decode_payload_failed", error=str(exc))
                return

            review_id = payload.get("review_id")
            task_id = payload.get("task_id")
            repository_name = payload.get("repository")
            pr_number = payload.get("pull_request_number", 0)

            if not review_id or not task_id or not repository_name:
                logger.error("documentation_worker_invalid_payload", payload=payload)
                return

            logger.info(
                "documentation_worker_processing_task",
                task_id=task_id,
                review_id=review_id,
                repository=repository_name,
                pr_number=pr_number,
            )

            # 1. Update task status to running
            await self._repository.save_task(
                AgentTask(
                    id=task_id,
                    review_id=review_id,
                    agent="documentation-agent",
                    status="running",
                    reason="Documentation analysis in progress",
                )
            )

            # 2. Run documentation analysis
            try:
                report = await self._documentation_service.run_documentation_analysis(
                    repository=repository_name,
                    pr_number=pr_number,
                )

                # Extract documentation score
                doc_score = report.get("documentation_score", 100)

                # 3. Save task as completed with report details
                await self._repository.save_task(
                    AgentTask(
                        id=task_id,
                        review_id=review_id,
                        agent="documentation-agent",
                        status="completed",
                        report=report,
                    )
                )

                # 4. Update the parent review with scores
                review = await self._repository.get_review(review_id)
                if review:
                    temp_review = PullRequestReview(
                        id=review.id,
                        repository=review.repository,
                        pull_request_number=review.pull_request_number,
                        delivery_id=review.delivery_id,
                        status=review.status,
                        score=review.score,
                        security_score=review.security_score,
                        performance_score=review.performance_score,
                        architecture_score=review.architecture_score,
                        documentation_score=doc_score,
                    )
                    overall_score = temp_review.calculate_overall_score()
                    updated_review = PullRequestReview(
                        id=review.id,
                        repository=review.repository,
                        pull_request_number=review.pull_request_number,
                        delivery_id=review.delivery_id,
                        status=review.status,
                        score=overall_score,
                        security_score=review.security_score,
                        performance_score=review.performance_score,
                        architecture_score=review.architecture_score,
                        documentation_score=doc_score,
                    )
                    await self._repository.save_review(updated_review)

                logger.info(
                    "documentation_worker_task_completed",
                    task_id=task_id,
                    review_id=review_id,
                    documentation_score=doc_score,
                )
            except Exception as exc:
                logger.error(
                    "documentation_worker_task_failed",
                    task_id=task_id,
                    review_id=review_id,
                    error=str(exc),
                    exc_info=True,
                )
                await self._repository.save_task(
                    AgentTask(
                        id=task_id,
                        review_id=review_id,
                        agent="documentation-agent",
                        status="failed",
                        reason=f"Execution error: {str(exc)}",
                    )
                )
            finally:
                await self._coordinator.check_and_finalize_review(review_id)


async def run_worker(
    settings_factory: Callable[[], Settings] = get_settings,
    worker_factory: (
        Callable[[Settings, PostgresReviewRepository, DocumentationAgentService, ReviewCoordinator], DocumentationWorker] | None
    ) = None,
) -> None:
    settings = settings_factory()
    configure_logging(settings)

    postgres_pool = await create_postgres_pool(settings)
    await init_db(postgres_pool)
    repository = PostgresReviewRepository(postgres_pool)

    git_service = GitService()
    doc_analyzer = OpenAIDocAnalyzer(settings)
    documentation_service = DocumentationAgentService(git_service, doc_analyzer)

    notifier = GitHubNotificationPublisher(settings)
    slack_notifier = SlackNotificationPublisher(settings)
    coordinator = ReviewCoordinator(repository, notifier, slack_notifier)

    if worker_factory:
        worker = worker_factory(settings, repository, documentation_service, coordinator)
    else:
        worker = DocumentationWorker(
            settings=settings,
            repository=repository,
            documentation_service=documentation_service,
            coordinator=coordinator,
        )

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))

    try:
        await worker.run()
    finally:
        await close_postgres_pool(postgres_pool)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
