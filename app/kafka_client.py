from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic

from app.config import settings

logger = logging.getLogger(__name__)


class KafkaManager:
    """Small wrapper around aiokafka for producing + consuming.

    This keeps the demo simple and readable.
    """

    def __init__(self) -> None:
        self._producer: Optional[AIOKafkaProducer] = None
        self._consumer: Optional[AIOKafkaConsumer] = None

    async def start(self) -> None:
        if settings.create_topics:
            await self._create_topic_if_needed(settings.kafka_topic_incoming)

        self._producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
        await self._producer.start()

        self._consumer = AIOKafkaConsumer(
            settings.kafka_topic_incoming,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
            enable_auto_commit=True,
            auto_offset_reset="earliest",
        )
        await self._consumer.start()

    async def stop(self) -> None:
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()

    async def produce_event(self, event: Dict[str, Any]) -> None:
        """Publish a JSON event to Kafka."""
        if not self._producer:
            raise RuntimeError("Kafka producer not started")
        payload = json.dumps(event).encode("utf-8")
        await self._producer.send_and_wait(settings.kafka_topic_incoming, payload)

    async def consume_events(self) -> AsyncIterator[Dict[str, Any]]:
        """Yield JSON events from Kafka."""
        if not self._consumer:
            raise RuntimeError("Kafka consumer not started")

        async for msg in self._consumer:
            try:
                data = json.loads(msg.value.decode("utf-8"))
                yield data
            except Exception:
                logger.exception("Failed to decode Kafka message")

    async def _create_topic_if_needed(self, topic_name: str) -> None:
        """Idempotently ensure a topic exists (single-node dev safe)."""
        admin = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers)
        await admin.start()
        try:
            topics = await admin.list_topics()
            if topic_name in topics:
                return

            await admin.create_topics(
                [NewTopic(name=topic_name, num_partitions=1, replication_factor=1)],
                validate_only=False,
            )
            logger.info("Created Kafka topic: %s", topic_name)
        except Exception:
            # In some environments topic auto-create is enabled; don't fail the demo
            logger.exception("Could not create topic (continuing)")
        finally:
            await admin.close()


kafka_manager = KafkaManager()
