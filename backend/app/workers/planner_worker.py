import asyncio
import json
import signal
import uuid
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from aio_pika.abc import AbstractIncomingMessage

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.domain.events import GitHubWebhookEvent, PullRequestReviewPlan
from app.domain.models import AgentTask, PullRequestReview
from app.domain.ports import EventPublisher, ReviewRepository
from app.infrastructure.database import close_postgres_pool, create_postgres_pool, init_db
from app.infrastructure.postgres_repository import PostgresReviewRepository
from app.infrastructure.rabbitmq import (
    close_event_publisher,
    connect_with_retry,
    create_event_publisher,
    declare_all_topology,
)
from app.services.planner_service import PlannerService

logger = get_logger(__name__)


class PlannerWorker:
    def __init__(
        self,
        settings: Settings,
        planner_service: PlannerService,
        repository: ReviewRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._settings = settings
        self._planner_service = planner_service
        self._repository = repository
        self._event_publisher = event_publisher
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        configure_logging(self._settings)
        logger.info("planner_worker_starting")

        connection = await connect_with_retry(self._settings)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=self._settings.planner_worker_prefetch_count)
        
        # Declare all queue topologies (webhook and agent task queues)
        await declare_all_topology(channel, self._settings)
        queue = await channel.declare_queue(
            self._settings.rabbitmq_github_webhook_queue,
            durable=True,
        )

        await queue.consume(self._handle_message)
        logger.info(
            "planner_worker_consuming",
            queue=self._settings.rabbitmq_github_webhook_queue,
        )

        try:
            await self._stop_event.wait()
        finally:
            logger.info("planner_worker_stopping")
            await channel.close()
            await connection.close()

    async def stop(self) -> None:
        self._stop_event.set()

    async def _handle_message(self, message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            event = self._decode_message(message)
            plan = self._planner_service.plan_github_webhook(event)

            if plan is None:
                logger.info(
                    "planner_worker_event_ignored",
                    github_event=event.event,
                    action=event.action,
                    delivery_id=event.delivery_id,
                )
                return

            review_id = str(uuid.uuid4())
            review = PullRequestReview(
                id=review_id,
                repository=plan.repository_full_name,
                pull_request_number=plan.pull_request_number or 0,
                delivery_id=plan.delivery_id,
                status="pending",
            )
            
            logger.info(
                "planner_worker_saving_review",
                review_id=review_id,
                repository=review.repository,
                pull_request=review.pull_request_number,
            )
            await self._repository.save_review(review)

            for task_plan in plan.tasks:
                task_id = str(uuid.uuid4())
                task = AgentTask(
                    id=task_id,
                    review_id=review_id,
                    agent=task_plan.agent,
                    status="pending",
                    reason=task_plan.reason,
                )
                await self._repository.save_task(task)
                
                logger.info(
                    "planner_worker_publishing_task",
                    task_id=task_id,
                    review_id=review_id,
                    agent=task_plan.agent,
                )
                await self._event_publisher.publish_agent_task(
                    review_id=review_id,
                    task_id=task_id,
                    agent=task_plan.agent,
                    repository=plan.repository_full_name,
                    pull_request_number=plan.pull_request_number or 0,
                )

            self._log_plan(plan, review_id)

    @staticmethod
    def _decode_message(message: AbstractIncomingMessage) -> GitHubWebhookEvent:
        payload: dict[str, Any] = json.loads(message.body.decode("utf-8"))
        event_payload = payload.get("payload")
        if not isinstance(event_payload, dict):
            event_payload = {}

        return GitHubWebhookEvent(
            event=str(payload.get("event", "unknown")),
            delivery_id=payload.get("delivery_id"),
            action=payload.get("action"),
            repository_full_name=payload.get("repository"),
            payload=event_payload,
        )

    @staticmethod
    def _log_plan(plan: PullRequestReviewPlan, review_id: str) -> None:
        logger.info(
            "planner_worker_plan_created",
            review_id=review_id,
            delivery_id=plan.delivery_id,
            repository=plan.repository_full_name,
            pull_request_number=plan.pull_request_number,
            action=plan.action,
            planned_agents=[task.agent for task in plan.tasks],
        )


async def run_worker(
    settings_factory: Callable[[], Settings] = get_settings,
    worker_factory: (
        Callable[[Settings, PostgresReviewRepository, EventPublisher], PlannerWorker]
        | None
    ) = None,
) -> None:
    settings = settings_factory()
    configure_logging(settings)

    postgres_pool = await create_postgres_pool(settings)
    await init_db(postgres_pool)
    event_publisher = await create_event_publisher(settings)
    repository = PostgresReviewRepository(postgres_pool)

    if worker_factory:
        worker = worker_factory(settings, repository, event_publisher)
    else:
        worker = PlannerWorker(
            settings=settings,
            planner_service=PlannerService(),
            repository=repository,
            event_publisher=event_publisher,
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

