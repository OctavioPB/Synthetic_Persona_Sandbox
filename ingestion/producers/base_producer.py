"""Base Kafka producer with Confluent Avro wire-format support."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

from kafka import KafkaProducer

from ingestion.schemas.schema_registry import SchemaRegistryClient

logger = logging.getLogger(__name__)


class BaseAvroProducer(ABC):
    """Abstract Kafka producer that serializes messages using the Confluent wire format.

    Subclasses implement `produce_event()` for their specific event type.

    Args:
        bootstrap_servers: Kafka broker addresses.
        schema_registry_url: Schema Registry base URL.
    """

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        schema_registry_url: str | None = None,
    ) -> None:
        servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        sr_url  = schema_registry_url or os.getenv("KAFKA_SCHEMA_REGISTRY_URL", "http://localhost:8081")

        self._schema_registry = SchemaRegistryClient(sr_url)
        self._producer = KafkaProducer(
            bootstrap_servers=servers,
            acks="all",
            retries=5,
            value_serializer=None,  # we handle serialization manually
        )
        self._register_schemas()

    @abstractmethod
    def _register_schemas(self) -> None:
        """Register all schemas used by this producer with the Schema Registry."""

    def _send(self, topic: str, value: bytes, key: bytes | None = None) -> None:
        """Send a pre-serialized message to a Kafka topic.

        Args:
            topic: Destination Kafka topic.
            value: Avro-encoded bytes (Confluent wire format).
            key: Optional message key (bytes).
        """
        future = self._producer.send(topic, value=value, key=key)
        try:
            future.get(timeout=10)
        except Exception as exc:
            logger.error("Failed to send message to topic '%s': %s", topic, exc)
            raise

    def flush(self) -> None:
        """Flush buffered messages — call before shutting down."""
        self._producer.flush()

    def close(self) -> None:
        """Flush and close the underlying Kafka producer."""
        self._producer.flush()
        self._producer.close()
        logger.info("%s closed.", self.__class__.__name__)
