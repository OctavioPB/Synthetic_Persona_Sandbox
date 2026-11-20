"""Base Kafka consumer with DLQ support and graceful shutdown."""

from __future__ import annotations

import json
import logging
import os
import signal
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

from ingestion.schemas.events import TOPIC_DLQ
from ingestion.schemas.schema_registry import SchemaRegistryClient

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    success: bool
    error_type: str = ""
    error_message: str = ""


class BaseKafkaConsumer(ABC):
    """Abstract consumer with Schema Registry deserialization and DLQ routing.

    Subclasses implement `process_record()` with the decoded event dict.

    Args:
        topics:              List of Kafka topics to subscribe to.
        group_id:            Kafka consumer group id.
        bootstrap_servers:   Kafka broker addresses (defaults to env var).
        schema_registry_url: Schema Registry URL (defaults to env var).
        auto_offset_reset:   'earliest' or 'latest'.
    """

    def __init__(
        self,
        topics: list[str],
        group_id: str,
        bootstrap_servers: str | None = None,
        schema_registry_url: str | None = None,
        auto_offset_reset: str = "earliest",
    ) -> None:
        servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        sr_url = schema_registry_url or os.environ.get(
            "KAFKA_SCHEMA_REGISTRY_URL", "http://localhost:8081"
        )

        self._schema_registry = SchemaRegistryClient(sr_url)
        self._consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=servers,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=False,  # manual commit after successful processing
            value_deserializer=None,  # raw bytes — we decode manually
        )
        self._dlq_producer = KafkaProducer(
            bootstrap_servers=servers,
            value_serializer=lambda v: json.dumps(v).encode(),
        )
        self._running = False
        self._register_signals()

    def _register_signals(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum: int, frame: object) -> None:
        logger.info("Shutdown signal received (%d). Stopping consumer loop.", signum)
        self._running = False

    def _send_to_dlq(
        self, topic: str, raw_bytes: bytes, error_type: str, error_message: str
    ) -> None:
        """Route a failed message to the dead-letter queue topic."""
        dlq_msg = {
            "original_topic": topic,
            "original_payload": raw_bytes.hex(),  # JSON-safe hex encoding
            "error_type": error_type,
            "error_message": error_message,
            "failed_at_ms": int(time.time() * 1000),
        }
        try:
            self._dlq_producer.send(TOPIC_DLQ, value=dlq_msg)
            logger.warning(
                "Sent malformed message to DLQ. topic=%s error_type=%s",
                topic,
                error_type,
            )
        except KafkaError as exc:
            logger.error("Failed to send message to DLQ: %s", exc)

    @abstractmethod
    def process_record(self, topic: str, record: dict) -> ProcessingResult:  # type: ignore[type-arg]
        """Process one deserialized Avro record.

        Args:
            topic:  The source Kafka topic.
            record: Decoded event as a plain dict.

        Returns:
            ProcessingResult indicating success or the type of failure.
        """

    def _handle_message(self, topic: str, raw: bytes) -> None:
        """Decode and process one message, routing any failure to the DLQ.

        Never raises: one malformed record must not take the consumer down
        (it would be redelivered on restart and crash it again).
        """
        try:
            _, record = self._schema_registry.decode(raw)
        except Exception as exc:
            self._send_to_dlq(topic, raw, type(exc).__name__, str(exc))
            return

        try:
            result = self.process_record(topic, record)
        except Exception as exc:
            logger.exception("Unhandled error processing record from %s.", topic)
            result = ProcessingResult(
                success=False, error_type=type(exc).__name__, error_message=str(exc)
            )

        if not result.success:
            self._send_to_dlq(topic, raw, result.error_type, result.error_message)

    def run(self) -> None:
        """Start the blocking consumer loop. Exits cleanly on SIGTERM/SIGINT."""
        self._running = True
        logger.info(
            "%s started. Subscribed to: %s", self.__class__.__name__, self._consumer.subscription()
        )

        try:
            while self._running:
                records = self._consumer.poll(timeout_ms=1000)
                if not records:
                    continue

                for tp, messages in records.items():
                    for msg in messages:
                        self._handle_message(tp.topic, msg.value)

                # One offset commit per polled batch instead of one broker round
                # trip per message. A crash mid-batch replays the batch, which is
                # safe because process_record() implementations are idempotent.
                # Flush the DLQ first so a failed message is never acknowledged
                # before its DLQ copy is durable.
                self._dlq_producer.flush()
                self._consumer.commit()
        finally:
            self._consumer.close()
            self._dlq_producer.flush()
            self._dlq_producer.close()
            logger.info("%s stopped.", self.__class__.__name__)
