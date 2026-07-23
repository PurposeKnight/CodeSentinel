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
from app.infrastructure.github_notifier import GitHubNotificationPublisher
from app.infrastructure.slack_notifier import SlackNotificationPublisher
from app.infrastructure.postgres_repository import PostgresReviewRepository
from app.infrastructure.rabbitmq import (
    close_event_publisher,
    connect_with_retry,
    create_event_publisher,
    declare_all_topology,
)
from app.services.review_coordinator import ReviewCoordinator
from app.services.deployment_agent_service import DeploymentAgentService

logger = get_logger(__name__)


class DeploymentWorker:
    def __init__(
        self,
        settings: Settings,
        repository: ReviewRepository,
        deployment_service: DeploymentAgentService,
        coordinator: ReviewCoordinator,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._deployment_service = deployment_service
        self._coordinator = coordinator
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        configure_logging(self._settings)
        logger.info("deployment_worker_starting")

        # Start heartbeat loop
        from app.infrastructure.heartbeat import publish_heartbeat
        heartbeat_task = asyncio.create_task(
            publish_heartbeat(
                redis_url=self._settings.redis_url,
                worker_name="deployment-worker",
                stop_event=self._stop_event,
            )
        )

        connection = await connect_with_retry(self._settings)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)

        await declare_all_topology(channel, self._settings)
        queue = await channel.declare_queue(
            "codesentinel.tasks.deployment",
            durable=True,
        )

        await queue.consume(self._handle_message)
        logger.info("deployment_worker_consuming", queue="codesentinel.tasks.deployment")

        try:
            await self._stop_event.wait()
        finally:
            logger.info("deployment_worker_stopping")
            await heartbeat_task
            await channel.close()
            await connection.close()

    async def stop(self) -> None:
        self._stop_event.set()

    async def _handle_message(self, message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                payload = json.loads(message.body.decode("utf-8"))
            except Exception as exc:
                logger.error("deployment_worker_decode_payload_failed", error=str(exc))
                return

            review_id = payload.get("review_id")
            task_id = payload.get("task_id")
            repository_name = payload.get("repository")
            pr_number = payload.get("pull_request_number", 0)

            if not review_id or not task_id or not repository_name:
                logger.error("deployment_worker_invalid_payload", payload=payload)
                return

            logger.info(
                "deployment_worker_processing_task",
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
                    agent="deployment-agent",
                    status="running",
                    reason="Deployment and liveness probes in progress.",
                )
            )

            try:
                # 2. Trigger deployment
                deploy_info = await self._deployment_service.trigger_deployment(
                    repository=repository_name,
                    pr_number=pr_number,
                )

                # Simulate deployment delay (e.g. 3 seconds)
                await asyncio.sleep(3.0)

                # 3. Verify health
                healthy, health_reason = await self._deployment_service.verify_health()

                if healthy:
                    report = {
                        "status": "success",
                        "environment": deploy_info.get("environment"),
                        "deployment_id": deploy_info.get("deployment_id"),
                        "url": deploy_info.get("url"),
                        "details": health_reason,
                    }

                    # Save task as completed
                    await self._repository.save_task(
                        AgentTask(
                            id=task_id,
                            review_id=review_id,
                            agent="deployment-agent",
                            status="completed",
                            reason="Deployment succeeded and verified healthy.",
                            report=report,
                        )
                    )
                else:
                    # Rollback since it's unhealthy
                    rollback_reason = await self._deployment_service.rollback(
                        repository=repository_name,
                        pr_number=pr_number,
                    )

                    report = {
                        "status": "failed",
                        "details": f"Deployment failed: {health_reason}",
                        "rollback": rollback_reason,
                    }

                    await self._repository.save_task(
                        AgentTask(
                            id=task_id,
                            review_id=review_id,
                            agent="deployment-agent",
                            status="failed",
                            reason=f"Health check failed: {health_reason}. Deployment rolled back.",
                            report=report,
                        )
                    )

                logger.info(
                    "deployment_worker_task_completed",
                    task_id=task_id,
                    review_id=review_id,
                )
            except Exception as exc:
                logger.error(
                    "deployment_worker_task_failed",
                    task_id=task_id,
                    review_id=review_id,
                    error=str(exc),
                    exc_info=True,
                )

                # Handle failure by doing a rollback attempt
                try:
                    rollback_reason = await self._deployment_service.rollback(
                        repository=repository_name,
                        pr_number=pr_number,
                    )
                except Exception as roll_exc:
                    rollback_reason = f"Rollback failed: {str(roll_exc)}"

                await self._repository.save_task(
                    AgentTask(
                        id=task_id,
                        review_id=review_id,
                        agent="deployment-agent",
                        status="failed",
                        reason=f"Deployment execution error: {str(exc)}",
                        report={"status": "error", "details": str(exc), "rollback": rollback_reason},
                    )
                )
            finally:
                await self._coordinator.check_and_finalize_review(review_id)


async def run_worker(
    settings_factory: Callable[[], Settings] = get_settings,
    worker_factory: (
        Callable[[Settings, PostgresReviewRepository, DeploymentAgentService, ReviewCoordinator], DeploymentWorker]
        | None
    ) = None,
) -> None:
    settings = settings_factory()
    configure_logging(settings)

    postgres_pool = await create_postgres_pool(settings)
    await init_db(postgres_pool)
    repository = PostgresReviewRepository(postgres_pool)

    event_publisher = await create_event_publisher(settings)
    deployment_service = DeploymentAgentService()

    notifier = GitHubNotificationPublisher(settings)
    slack_notifier = SlackNotificationPublisher(settings)
    coordinator = ReviewCoordinator(repository, notifier, slack_notifier, event_publisher)

    if worker_factory:
        worker = worker_factory(settings, repository, deployment_service, coordinator)
    else:
        worker = DeploymentWorker(
            settings=settings,
            repository=repository,
            deployment_service=deployment_service,
            coordinator=coordinator,
        )

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))

    try:
        await worker.run()
    finally:
        await close_event_publisher(event_publisher)
        await close_postgres_pool(postgres_pool)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
