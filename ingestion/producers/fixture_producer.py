"""Dev fixture producer — generates synthetic behavioral events for local testing.

Produces a realistic mix of PageViewEvent, PurchaseEvent, and SessionEvent
messages to Kafka so the consumer pipeline can be exercised without real traffic.

Usage (from repo root):
    python scripts/run_fixture_producer.py --events-per-type 50
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from datetime import datetime

from ingestion.producers.base_producer import BaseAvroProducer
from ingestion.schemas.events import (
    TOPIC_PAGE_VIEWS,
    TOPIC_PURCHASES,
    TOPIC_SESSIONS,
    RawPageViewEvent,
    RawPurchaseEvent,
    RawSessionEvent,
    SessionEventType,
    load_avro_schema,
)

logger = logging.getLogger(__name__)

# ── Fixture data pools ─────────────────────────────────────────────────────────

_CATEGORIES = ["Electronics", "Fashion", "Home & Garden", "Sports", "Books", "Food & Beverage"]

_PRODUCTS: dict[str, list[tuple[str, str]]] = {
    "Electronics":    [("PROD-E01", "Laptop Pro 15"), ("PROD-E02", "Wireless Earbuds"), ("PROD-E03", "4K Monitor")],
    "Fashion":        [("PROD-F01", "Running Shoes"), ("PROD-F02", "Denim Jacket"), ("PROD-F03", "Leather Watch")],
    "Home & Garden":  [("PROD-H01", "Coffee Maker"), ("PROD-H02", "LED Lamp"), ("PROD-H03", "Planter Set")],
    "Sports":         [("PROD-S01", "Yoga Mat"), ("PROD-S02", "Resistance Bands"), ("PROD-S03", "Water Bottle")],
    "Books":          [("PROD-B01", "Clean Code"), ("PROD-B02", "Designing Data-Intensive Apps"), ("PROD-B03", "Deep Work")],
    "Food & Beverage":[("PROD-FB01", "Premium Coffee Blend"), ("PROD-FB02", "Protein Bars 12-Pack"), ("PROD-FB03", "Olive Oil")],
}

_PAGE_URLS = [
    "/", "/products", "/products/{category}/{slug}",
    "/cart", "/checkout", "/account", "/wishlist",
]

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 Safari/605",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/125.0 Mobile",
]

_REFERRERS = [None, "https://google.com", "https://instagram.com", "https://t.co", None, None]


def _random_ip() -> str:
    return f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def _random_email() -> str:
    names = ["alice", "bob", "carol", "dave", "eve", "frank", "grace", "heidi"]
    domains = ["example.com", "demo.org", "test.net"]
    return f"{random.choice(names)}{random.randint(1, 9999)}@{random.choice(domains)}"


def _now_ms() -> int:
    return int(time.time() * 1000)


class FixtureEventProducer(BaseAvroProducer):
    """Produces fake behavioral events for all three event types."""

    def _register_schemas(self) -> None:
        pv_schema  = load_avro_schema("page_view_event")
        pur_schema = load_avro_schema("purchase_event")
        ses_schema = load_avro_schema("session_event")

        self._pv_schema_id  = self._schema_registry.register_schema(f"{TOPIC_PAGE_VIEWS}-value",  pv_schema)
        self._pur_schema_id = self._schema_registry.register_schema(f"{TOPIC_PURCHASES}-value",   pur_schema)
        self._ses_schema_id = self._schema_registry.register_schema(f"{TOPIC_SESSIONS}-value",    ses_schema)

        self._pv_schema  = pv_schema
        self._pur_schema = pur_schema
        self._ses_schema = ses_schema

    # ── Page view ──────────────────────────────────────────────────────────────

    def produce_page_view(self, user_id: str | None = None) -> RawPageViewEvent:
        """Produce one fake PageViewEvent. Returns the event for inspection."""
        uid      = user_id or str(uuid.uuid4())
        category = random.choice(_CATEGORIES)
        event = RawPageViewEvent(
            event_id=str(uuid.uuid4()),
            user_id=uid,
            session_id=str(uuid.uuid4()),
            timestamp_ms=_now_ms(),
            url=f"/products/{category.lower().replace(' ', '-')}/item-{random.randint(1, 99)}",
            referrer=random.choice(_REFERRERS),
            category=category,
            user_agent=random.choice(_USER_AGENTS),
            ip_address=_random_ip(),
        )
        payload = self._schema_registry.encode(
            self._pv_schema_id, event.model_dump(), self._pv_schema
        )
        self._send(TOPIC_PAGE_VIEWS, payload, key=uid.encode())
        return event

    # ── Purchase ───────────────────────────────────────────────────────────────

    def produce_purchase(self, user_id: str | None = None) -> RawPurchaseEvent:
        """Produce one fake PurchaseEvent. Returns the event for inspection."""
        uid      = user_id or str(uuid.uuid4())
        category = random.choice(_CATEGORIES)
        product_id, product_name = random.choice(_PRODUCTS[category])
        event = RawPurchaseEvent(
            event_id=str(uuid.uuid4()),
            user_id=uid,
            session_id=str(uuid.uuid4()),
            timestamp_ms=_now_ms(),
            order_id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            product_id=product_id,
            product_name=product_name,
            category=category,
            amount=round(random.uniform(9.99, 599.99), 2),
            currency="USD",
            quantity=random.randint(1, 3),
            email=_random_email(),
        )
        payload = self._schema_registry.encode(
            self._pur_schema_id, event.model_dump(), self._pur_schema
        )
        self._send(TOPIC_PURCHASES, payload, key=uid.encode())
        return event

    # ── Session ────────────────────────────────────────────────────────────────

    def produce_session_start(self, user_id: str | None = None) -> RawSessionEvent:
        """Produce a SESSION_START event."""
        uid = user_id or str(uuid.uuid4())
        event = RawSessionEvent(
            event_id=str(uuid.uuid4()),
            user_id=uid,
            session_id=str(uuid.uuid4()),
            timestamp_ms=_now_ms(),
            event_type=SessionEventType.SESSION_START,
        )
        payload = self._schema_registry.encode(
            self._ses_schema_id, event.model_dump(), self._ses_schema
        )
        self._send(TOPIC_SESSIONS, payload, key=uid.encode())
        return event

    def produce_session_end(
        self, user_id: str | None = None, session_id: str | None = None
    ) -> RawSessionEvent:
        """Produce a SESSION_END event."""
        uid = user_id or str(uuid.uuid4())
        event = RawSessionEvent(
            event_id=str(uuid.uuid4()),
            user_id=uid,
            session_id=session_id or str(uuid.uuid4()),
            timestamp_ms=_now_ms(),
            event_type=SessionEventType.SESSION_END,
            duration_seconds=random.randint(30, 1800),
            page_count=random.randint(1, 20),
        )
        payload = self._schema_registry.encode(
            self._ses_schema_id, event.model_dump(), self._ses_schema
        )
        self._send(TOPIC_SESSIONS, payload, key=uid.encode())
        return event

    def produce_batch(
        self,
        n_page_views: int = 20,
        n_purchases: int = 5,
        n_sessions: int = 10,
    ) -> None:
        """Produce a mixed batch of events across all topics.

        Args:
            n_page_views: Number of page view events to produce.
            n_purchases:  Number of purchase events to produce.
            n_sessions:   Number of session pairs (start + end) to produce.
        """
        for _ in range(n_page_views):
            self.produce_page_view()

        for _ in range(n_purchases):
            self.produce_purchase()

        for _ in range(n_sessions):
            uid = str(uuid.uuid4())
            start = self.produce_session_start(user_id=uid)
            self.produce_session_end(user_id=uid, session_id=start.session_id)

        self.flush()
        logger.info(
            "Fixture batch produced: %d page_views, %d purchases, %d sessions.",
            n_page_views, n_purchases, n_sessions,
        )
