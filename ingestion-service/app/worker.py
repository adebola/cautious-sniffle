"""RabbitMQ consumer worker for document processing messages.

Connects to the ``chatcraft`` topic exchange, binds to the
``document.process`` queue with routing key ``document.process``, and
dispatches each message to the :class:`IngestionPipeline`.
"""

import json
import logging

import aio_pika

from app.config import Settings
from app.services.ingestion_pipeline import IngestionPipeline

logger = logging.getLogger(__name__)


async def start_worker(settings: Settings) -> None:
    """Connect to RabbitMQ and start consuming ``document.process`` messages.

    This function runs indefinitely.  It is designed to be launched as an
    ``asyncio.Task`` from the FastAPI startup event.

    Args:
        settings: Application settings (used for RabbitMQ URL and pipeline config).
    """
    logger.info("Connecting to RabbitMQ at %s", settings.rabbitmq_url)

    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()

    # Limit concurrent processing to 2 documents at a time
    await channel.set_qos(prefetch_count=2)

    # Declare the exchange and queue
    exchange = await channel.declare_exchange(
        "chatcraft",
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )
    queue = await channel.declare_queue("document.process", durable=True)
    await queue.bind(exchange, "document.process")

    logger.info("RabbitMQ worker started, listening on queue 'document.process'")

    # Build the pipeline once, reused across messages
    pipeline = IngestionPipeline(settings)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                try:
                    body = message.body.decode("utf-8")
                    data = json.loads(body)

                    document_id = data.get("document_id")
                    organization_id = data.get("organization_id")
                    storage_path = data.get("storage_path")

                    if not all([document_id, organization_id, storage_path]):
                        logger.error(
                            "Invalid message payload - missing required fields: %s",
                            body,
                        )
                        continue

                    logger.info(
                        "Received document.process message: document_id=%s, org=%s, path=%s",
                        document_id,
                        organization_id,
                        storage_path,
                    )

                    await pipeline.process_document(
                        document_id=document_id,
                        organization_id=organization_id,
                        storage_path=storage_path,
                    )

                except json.JSONDecodeError:
                    logger.error(
                        "Failed to decode message body as JSON: %s",
                        message.body[:500],
                    )
                except Exception:
                    logger.exception("Unexpected error processing message")
