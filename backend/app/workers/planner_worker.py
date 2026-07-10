import asyncio
import json
import signal
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from aio_pika.abc import AbstractIncomingMessage

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.domain.events import GitHubWebhookEvent, PullRequestReviewPlan
from app.infrastructure.rabbitmq import connect_with_retry, declare_github_webhook_topology
from app.services.planner_service import PlannerService

logger = get_logger(__name__)


class PlannerWorker:
    def __init__(self, settings: Settings, planner_service: PlannerService) -> None:
        self._settings = settings
        self._planner_service = planner_service
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        configure_logging(self._settings)
        logger.info("planner_worker_starting")

        connection = await connect_with_retry(self._settings)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=self._settings.planner_worker_prefetch_count)
        queue = await declare_github_webhook_topology(channel, self._settings)

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

            self._log_plan(plan)

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
    def _log_plan(plan: PullRequestReviewPlan) -> None:
        logger.info(
            "planner_worker_plan_created",
            delivery_id=plan.delivery_id,
            repository=plan.repository_full_name,
            pull_request_number=plan.pull_request_number,
            action=plan.action,
            planned_agents=[task.agent for task in plan.tasks],
        )


async def run_worker(
    settings_factory: Callable[[], Settings] = get_settings,
    worker_factory: Callable[[Settings], PlannerWorker] | None = None,
) -> None:
    settings = settings_factory()
    worker = worker_factory(settings) if worker_factory else PlannerWorker(
        settings=settings,
        planner_service=PlannerService(),
    )

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))

    await worker.run()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
