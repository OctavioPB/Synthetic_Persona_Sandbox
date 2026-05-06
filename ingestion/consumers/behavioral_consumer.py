"""Behavioral event consumer.

Reads anonymized events from all three topics, writes raw events to the
`behavioral_events` PostgreSQL table, and maintains a live profile state
in Redis for real-time API access.

The PII anonymizer is applied BEFORE any data touches storage.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import redis
from tenacity import retry, stop_after_attempt, wait_exponential

from ingestion.anonymizer import AnonymizerService
from ingestion.consumers.base_consumer import BaseKafkaConsumer, ProcessingResult
from ingestion.schemas.events import (
    TOPIC_PAGE_VIEWS,
    TOPIC_PURCHASES,
    TOPIC_SESSIONS,
    RawPageViewEvent,
    RawPurchaseEvent,
    RawSessionEvent,
    SessionEventType,
)

logger = logging.getLogger(__name__)

# Redis key pattern: profile:{user_id_hash}
_PROFILE_KEY = "profile:{}"


def _redis_client() -> redis.Redis:  # type: ignore[type-arg]
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
    )


def _pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "synthetic_persona"),
        user=os.getenv("POSTGRES_USER", "spb_user"),
        password=os.getenv("POSTGRES_PASSWORD", "changeme"),
    )


class BehavioralEventConsumer(BaseKafkaConsumer):
    """Writes behavioral events to PostgreSQL and updates Redis profile state.

    All PII is anonymized via `AnonymizerService` before any write.
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(
            topics=[TOPIC_PAGE_VIEWS, TOPIC_PURCHASES, TOPIC_SESSIONS],
            group_id="behavioral-consumer-group",
            **kwargs,  # type: ignore[arg-type]
        )
        self._anonymizer = AnonymizerService()
        self._pg = _pg_conn()
        self._redis = _redis_client()

    # ── Public entry point ─────────────────────────────────────────────────────

    def process_record(self, topic: str, record: dict) -> ProcessingResult:  # type: ignore[type-arg]
        """Anonymize, persist, and update profile for one event.

        Args:
            topic:  Source Kafka topic.
            record: Raw deserialized Avro dict (may contain PII).

        Returns:
            ProcessingResult with success flag.
        """
        try:
            if topic == TOPIC_PAGE_VIEWS:
                return self._handle_page_view(record)
            elif topic == TOPIC_PURCHASES:
                return self._handle_purchase(record)
            elif topic == TOPIC_SESSIONS:
                return self._handle_session(record)
            else:
                return ProcessingResult(success=False, error_type="UnknownTopic", error_message=f"No handler for topic: {topic}")
        except psycopg2.Error as exc:
            logger.error("PostgreSQL error processing %s: %s", topic, exc)
            return ProcessingResult(success=False, error_type="PostgresError", error_message=str(exc))
        except redis.RedisError as exc:
            logger.error("Redis error processing %s: %s", topic, exc)
            return ProcessingResult(success=False, error_type="RedisError", error_message=str(exc))

    # ── Topic handlers ─────────────────────────────────────────────────────────

    def _handle_page_view(self, record: dict) -> ProcessingResult:  # type: ignore[type-arg]
        raw = RawPageViewEvent(**record)
        anon = self._anonymizer.anonymize_page_view(raw)

        self._insert_behavioral_event(
            event_id=anon.event_id,
            event_type="page_view",
            user_id_hash=anon.user_id_hash,
            session_id=anon.session_id,
            timestamp_ms=anon.timestamp_ms,
            payload=anon.model_dump(),
        )
        self._update_profile_page_view(anon.user_id_hash, anon.category, anon.timestamp_ms)
        return ProcessingResult(success=True)

    def _handle_purchase(self, record: dict) -> ProcessingResult:  # type: ignore[type-arg]
        raw = RawPurchaseEvent(**record)
        anon = self._anonymizer.anonymize_purchase(raw)

        self._insert_behavioral_event(
            event_id=anon.event_id,
            event_type="purchase",
            user_id_hash=anon.user_id_hash,
            session_id=anon.session_id,
            timestamp_ms=anon.timestamp_ms,
            payload=anon.model_dump(),
        )
        self._update_profile_purchase(anon.user_id_hash, anon.amount, anon.category, anon.timestamp_ms)
        return ProcessingResult(success=True)

    def _handle_session(self, record: dict) -> ProcessingResult:  # type: ignore[type-arg]
        # SessionEventType is an Enum in the Avro schema — compare by value
        record_copy = dict(record)
        record_copy["event_type"] = SessionEventType(record["event_type"])
        raw = RawSessionEvent(**record_copy)
        anon = self._anonymizer.anonymize_session(raw)

        self._insert_behavioral_event(
            event_id=anon.event_id,
            event_type="session",
            user_id_hash=anon.user_id_hash,
            session_id=anon.session_id,
            timestamp_ms=anon.timestamp_ms,
            payload=anon.model_dump(),
        )
        if anon.event_type == SessionEventType.SESSION_START:
            self._update_profile_session(anon.user_id_hash, anon.timestamp_ms)
        return ProcessingResult(success=True)

    # ── PostgreSQL writes ──────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def _insert_behavioral_event(
        self,
        event_id: str,
        event_type: str,
        user_id_hash: str,
        session_id: str,
        timestamp_ms: int,
        payload: dict,  # type: ignore[type-arg]
    ) -> None:
        ts = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        sql = """
            INSERT INTO behavioral_events
                (event_id, event_type, user_id_hash, session_id, timestamp, payload)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO NOTHING
        """
        with self._pg.cursor() as cur:
            cur.execute(sql, (event_id, event_type, user_id_hash, session_id, ts, json.dumps(payload)))
        self._pg.commit()

    # ── Redis profile upserts ──────────────────────────────────────────────────

    def _update_profile_page_view(
        self, user_id_hash: str, category: str | None, timestamp_ms: int
    ) -> None:
        key = _PROFILE_KEY.format(user_id_hash)
        pipe = self._redis.pipeline()
        pipe.hincrby(key, "page_views_total", 1)
        pipe.hset(key, "last_seen", datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat())
        if category:
            # Append category to a JSON list stored in a hash field
            raw_cats = self._redis.hget(key, "categories_viewed") or "[]"
            cats: list[str] = json.loads(raw_cats)
            if category not in cats:
                cats.append(category)
            pipe.hset(key, "categories_viewed", json.dumps(cats))
        pipe.execute()

    def _update_profile_purchase(
        self, user_id_hash: str, amount: float, category: str, timestamp_ms: int
    ) -> None:
        key = _PROFILE_KEY.format(user_id_hash)
        pipe = self._redis.pipeline()
        pipe.hincrby(key, "purchase_count", 1)
        # Accumulate total spend as string-encoded float
        existing = self._redis.hget(key, "purchase_total_amount")
        new_total = (float(existing) if existing else 0.0) + amount
        pipe.hset(key, "purchase_total_amount", f"{new_total:.2f}")
        pipe.hset(key, "last_seen", datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat())
        pipe.execute()

    def _update_profile_session(self, user_id_hash: str, timestamp_ms: int) -> None:
        key = _PROFILE_KEY.format(user_id_hash)
        pipe = self._redis.pipeline()
        pipe.hincrby(key, "session_count", 1)
        pipe.hset(key, "last_seen", datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat())
        pipe.execute()
