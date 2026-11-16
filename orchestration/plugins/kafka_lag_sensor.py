"""KafkaConsumerLagSensor — Airflow sensor that blocks until a consumer group
has zero (or below-threshold) lag on a given topic.

Used in run_simulation_pipeline to ensure behavioral events have been fully
consumed before feature engineering runs, so the feature matrix is up-to-date.

Implementation uses a non-subscribing kafka-python consumer to read the group's
committed offsets and the log-end offsets, computing lag = sum(LEO - committed)
across partitions.

The sensor is registered as an Airflow plugin so it can be used from any DAG
without being in the dags/ folder.
"""

from __future__ import annotations

import logging
import os

from airflow.plugins_manager import AirflowPlugin
from airflow.sensors.base import BaseSensorOperator

logger = logging.getLogger(__name__)


class KafkaConsumerLagSensor(BaseSensorOperator):
    """Sensor that waits until consumer group lag drops to <= max_lag.

    Args:
        topic:          Kafka topic name to monitor.
        group_id:       Consumer group ID to measure lag for.
        max_lag:        Maximum acceptable total lag across all partitions.
                        Defaults to 0 (fully caught up).
        bootstrap_servers: Kafka broker(s). Falls back to KAFKA_BOOTSTRAP_SERVERS env var.
    """

    template_fields = ("topic", "group_id")

    def __init__(
        self,
        topic: str,
        group_id: str,
        max_lag: int = 0,
        bootstrap_servers: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.topic = topic
        self.group_id = group_id
        self.max_lag = max_lag
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )

    def poke(self, context: dict) -> bool:  # type: ignore[override]
        """Check if consumer group lag is within the acceptable threshold.

        Returns True (sensor passes) if total lag <= max_lag.
        Returns False to continue polling.
        """
        from kafka import KafkaConsumer
        from kafka.structs import TopicPartition

        consumer = None
        try:
            # group_id is only used to look up the group's committed offsets;
            # the consumer never subscribes, so it does not join the group or
            # trigger a rebalance.
            consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                enable_auto_commit=False,
            )

            partitions = consumer.partitions_for_topic(self.topic)
            if not partitions:
                logger.warning("Topic '%s' has no partitions — assuming lag is 0.", self.topic)
                return True

            tps = [TopicPartition(self.topic, p) for p in partitions]
            end_offsets = consumer.end_offsets(tps)

            total_lag = 0
            for tp in tps:
                # committed() returns the offset as an int, or None when the
                # group has never committed on this partition.
                committed = consumer.committed(tp) or 0
                total_lag += max(0, end_offsets[tp] - committed)

            logger.info(
                "KafkaConsumerLagSensor: topic=%s group=%s lag=%d (threshold=%d).",
                self.topic,
                self.group_id,
                total_lag,
                self.max_lag,
            )
            return total_lag <= self.max_lag

        except Exception as exc:
            logger.warning("KafkaConsumerLagSensor poke failed (will retry): %s", exc)
            return False
        finally:
            if consumer is not None:
                consumer.close()


# ── Airflow plugin registration ────────────────────────────────────────────────


class KafkaLagSensorPlugin(AirflowPlugin):
    name = "kafka_lag_sensor_plugin"
    sensors = [KafkaConsumerLagSensor]
