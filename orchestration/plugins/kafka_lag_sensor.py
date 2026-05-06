"""KafkaConsumerLagSensor — Airflow sensor that blocks until a consumer group
has zero (or below-threshold) lag on a given topic.

Used in run_simulation_pipeline to ensure behavioral events have been fully
consumed before feature engineering runs, so the feature matrix is up-to-date.

Implementation uses kafka-python's AdminClient to query committed offsets and
latest log-end offsets, computing lag = sum(LEO - committed) across partitions.

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
        self.topic             = topic
        self.group_id          = group_id
        self.max_lag           = max_lag
        self.bootstrap_servers = (
            bootstrap_servers
            or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        )

    def poke(self, context: dict) -> bool:  # type: ignore[override]
        """Check if consumer group lag is within the acceptable threshold.

        Returns True (sensor passes) if total lag <= max_lag.
        Returns False to continue polling.
        """
        from kafka import KafkaAdminClient, KafkaConsumer
        from kafka.structs import TopicPartition

        try:
            admin = KafkaAdminClient(bootstrap_servers=self.bootstrap_servers)
            consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                enable_auto_commit=False,
            )

            # Get all partitions for the topic
            partitions = consumer.partitions_for_topic(self.topic)
            if not partitions:
                logger.warning(
                    "Topic '%s' has no partitions — assuming lag is 0.", self.topic
                )
                consumer.close()
                admin.close()
                return True

            tps = [TopicPartition(self.topic, p) for p in partitions]

            # Get log-end offsets (latest available on broker)
            end_offsets   = consumer.end_offsets(tps)

            # Get committed offsets for this consumer group
            committed = {}
            for tp in tps:
                offset_and_meta = consumer.committed(tp)
                committed[tp] = offset_and_meta.offset if offset_and_meta else 0

            total_lag = sum(
                max(0, end_offsets[tp] - committed.get(tp, 0)) for tp in tps
            )

            consumer.close()
            admin.close()

            logger.info(
                "KafkaConsumerLagSensor: topic=%s group=%s lag=%d (threshold=%d).",
                self.topic, self.group_id, total_lag, self.max_lag,
            )
            return total_lag <= self.max_lag

        except Exception as exc:
            logger.warning(
                "KafkaConsumerLagSensor poke failed (will retry): %s", exc
            )
            return False


# ── Airflow plugin registration ────────────────────────────────────────────────

class KafkaLagSensorPlugin(AirflowPlugin):
    name     = "kafka_lag_sensor_plugin"
    sensors  = [KafkaConsumerLagSensor]
