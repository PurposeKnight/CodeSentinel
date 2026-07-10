import json
from asyncio import sleep

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractChannel, AbstractQueue, AbstractRobustConnection

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.events import GitHubWebhookEvent

logger = get_logger(__name__)


class RabbitMQEventPublisher:
    def __init__(
        self,
        connection: AbstractRobustConnection,
        channel: AbstractChannel,
        settings: Settings,
    ) -> None:
        self._connection = connection
        self._channel = channel
        self._settings = settings

    @classmethod
    async def create(cls, settings: Settings) -> "RabbitMQEventPublisher":
        logger.info("rabbitmq_connecting", host=settings.rabbitmq_host)
        connection = await connect_with_retry(settings)
        channel = await connection.channel(publisher_confirms=True)
        await declare_github_webhook_topology(channel, settings)

        logger.info(
            "rabbitmq_connected",
            exchange=settings.rabbitmq_exchange,
            queue=settings.rabbitmq_github_webhook_queue,
        )
        return cls(connection=connection, channel=channel, settings=settings)

    async def publish_github_webhook(self, event: GitHubWebhookEvent) -> None:
        exchange = await self._channel.get_exchange(self._settings.rabbitmq_exchange)
        body = json.dumps(
            {
                "event": event.event,
                "delivery_id": event.delivery_id,
                "action": event.action,
                "repository": event.repository_full_name,
                "payload": event.payload,
            },
            separators=(",", ":"),
        ).encode("utf-8")

        await exchange.publish(
            Message(
                body=body,
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
                correlation_id=event.delivery_id,
                headers={
                    "github_event": event.event,
                    "github_action": event.action,
                    "repository": event.repository_full_name,
                },
            ),
            routing_key=self._settings.rabbitmq_github_webhook_routing_key,
        )

    async def check(self) -> None:
        if self._connection.is_closed or self._channel.is_closed:
            raise RuntimeError("RabbitMQ connection is closed.")

    async def close(self) -> None:
        if not self._channel.is_closed:
            await self._channel.close()
        if not self._connection.is_closed:
            await self._connection.close()
        logger.info("rabbitmq_connection_closed")


async def create_event_publisher(settings: Settings) -> RabbitMQEventPublisher:
    return await RabbitMQEventPublisher.create(settings)


async def close_event_publisher(publisher: RabbitMQEventPublisher | None) -> None:
    if publisher is None:
        return
    await publisher.close()


async def declare_github_webhook_topology(
    channel: AbstractChannel,
    settings: Settings,
) -> AbstractQueue:
    exchange = await channel.declare_exchange(
        settings.rabbitmq_exchange,
        ExchangeType.DIRECT,
        durable=True,
    )
    queue = await channel.declare_queue(
        settings.rabbitmq_github_webhook_queue,
        durable=True,
    )
    await queue.bind(
        exchange,
        routing_key=settings.rabbitmq_github_webhook_routing_key,
    )
    return queue


async def connect_with_retry(settings: Settings) -> AbstractRobustConnection:
    last_error: Exception | None = None
    for attempt in range(1, settings.rabbitmq_connect_retries + 1):
        try:
            return await aio_pika.connect_robust(settings.rabbitmq_url)
        except Exception as exc:  # noqa: BLE001 - startup needs bounded retry with logging.
            last_error = exc
            logger.warning(
                "rabbitmq_connect_retrying",
                attempt=attempt,
                max_attempts=settings.rabbitmq_connect_retries,
                error=str(exc),
            )
            await sleep(settings.rabbitmq_connect_retry_delay_seconds)

    raise RuntimeError("RabbitMQ connection failed after retries.") from last_error
