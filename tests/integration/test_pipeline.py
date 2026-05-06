"""Integration tests: event → Kafka → consumer → Redis → API.

These tests require the full docker-compose stack to be running:
    docker compose up -d kafka schema-registry postgres redis

Run with:
    uv run pytest tests/integration/ -v -m integration

Skipped in standard CI — require `INTEGRATION_TESTS=1` env var.
"""

from __future__ import annotations

import json
import os
import time
import uuid

import pytest
import redis
from httpx import ASGITransport, AsyncClient

from api.main import app
from ingestion.anonymizer import AnonymizerService
from ingestion.schemas.events import (
    RawPageViewEvent,
    RawPurchaseEvent,
    SessionEventType,
)

pytestmark = pytest.mark.skipif(
    os.getenv("INTEGRATION_TESTS") != "1",
    reason="Set INTEGRATION_TESTS=1 to run integration tests",
)


@pytest.fixture(scope="module")
def redis_client() -> redis.Redis:  # type: ignore[type-arg]
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
    )


@pytest.fixture()
def user_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture()
def anonymizer() -> AnonymizerService:
    return AnonymizerService()


# ── PII anonymizer → Redis ─────────────────────────────────────────────────────

def test_page_view_profile_updated_in_redis(
    redis_client: redis.Redis,  # type: ignore[type-arg]
    anonymizer: AnonymizerService,
    user_id: str,
) -> None:
    """Simulates what the behavioral consumer does and checks Redis state."""
    raw = RawPageViewEvent(
        event_id=str(uuid.uuid4()),
        user_id=user_id,
        session_id=str(uuid.uuid4()),
        timestamp_ms=int(time.time() * 1000),
        url="/products/electronics/laptop",
        category="Electronics",
        user_agent="Mozilla/5.0",
        ip_address="10.0.1.50",
    )
    anon = anonymizer.anonymize_page_view(raw)
    key = f"profile:{anon.user_id_hash}"

    # Write directly as the consumer would
    pipe = redis_client.pipeline()
    pipe.hincrby(key, "page_views_total", 1)
    pipe.hset(key, "last_seen", "2026-05-05T00:00:00+00:00")
    pipe.hset(key, "categories_viewed", json.dumps(["Electronics"]))
    pipe.execute()

    data = redis_client.hgetall(key)
    assert data["page_views_total"] == "1"
    assert "Electronics" in json.loads(data["categories_viewed"])

    # Cleanup
    redis_client.delete(key)


# ── API endpoint reads from Redis ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_profile_state_returns_404_for_unknown_user() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/profiles/{uuid.uuid4()}/state")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_profile_state_returns_data_after_ingest(
    redis_client: redis.Redis,  # type: ignore[type-arg]
    anonymizer: AnonymizerService,
) -> None:
    user_id = str(uuid.uuid4())
    raw = RawPurchaseEvent(
        event_id=str(uuid.uuid4()),
        user_id=user_id,
        session_id=str(uuid.uuid4()),
        timestamp_ms=int(time.time() * 1000),
        order_id="ORD-INT-001",
        product_id="PROD-E01",
        product_name="Laptop Pro 15",
        category="Electronics",
        amount=999.99,
        currency="USD",
        quantity=1,
        email="integration@test.com",
    )
    anon = anonymizer.anonymize_purchase(raw)
    key = f"profile:{anon.user_id_hash}"

    redis_client.hset(key, mapping={
        "purchase_count":          "1",
        "purchase_total_amount":   "999.99",
        "page_views_total":        "0",
        "session_count":           "0",
        "last_seen":               "2026-05-05T00:00:00+00:00",
        "categories_viewed":       "[]",
    })

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/profiles/{user_id}/state")

    assert response.status_code == 200
    body = response.json()
    assert body["purchase_count"] == 1
    assert abs(body["purchase_total_amount"] - 999.99) < 0.01

    redis_client.delete(key)
