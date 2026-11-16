"""Regression tests for defects found in the application audit.

Each test pins one bug that previously shipped, so it cannot silently return.
None of them need external services.
"""

from __future__ import annotations

import sys
import types
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from jwt.exceptions import InvalidTokenError

from api.auth import jwt_handler
from api.main import app
from api.models.simulation import SimulationRunORM
from api.routers import ws
from api.services import cache, rate_limiter
from api.services.metrics import API_REQUEST_LATENCY
from ml.segment_models.segment_schema import SegmentFeatureMatrix, UserFeatures

# ── JWT ────────────────────────────────────────────────────────────────────────


def _token(**claims: Any) -> str:
    payload = {"sub": "u1", "email": "u@example.com", "role": "viewer", **claims}
    return jwt.encode(payload, jwt_handler._SECRET, algorithm=jwt_handler._ALGORITHM)


def test_malformed_org_id_is_rejected_not_mapped_to_default_org() -> None:
    with pytest.raises(InvalidTokenError):
        jwt_handler.decode_token(_token(org_id="not-a-uuid"))


def test_valid_org_id_round_trips() -> None:
    org_id = uuid.uuid4()
    assert jwt_handler.decode_token(_token(org_id=str(org_id))).org_id == org_id


def test_production_refuses_default_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        jwt_handler.assert_secure_config()


def test_development_allows_default_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "development")
    jwt_handler.assert_secure_config()


# ── Run cache ──────────────────────────────────────────────────────────────────


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value

    async def scan_iter(self, match: str, count: int = 10) -> Any:
        prefix = match.rstrip("*")
        for key in list(self.store):
            if key.startswith(prefix):
                yield key

    async def unlink(self, *keys: str) -> None:
        for key in keys:
            self.store.pop(key, None)


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    fake = _FakeRedis()
    monkeypatch.setattr(cache, "get_redis", lambda: fake)
    return fake


async def test_completed_run_cache_hits_for_owner_only(fake_redis: _FakeRedis) -> None:
    await cache.cache_run("org-a", "run-1", {"id": "run-1"}, "completed")

    assert await cache.get_cached_run("org-a", "run-1") == {"id": "run-1"}
    assert await cache.get_cached_run("org-b", "run-1") is None


@pytest.mark.parametrize("status", ["pending", "running", "failed"])
async def test_non_completed_runs_are_never_cached(fake_redis: _FakeRedis, status: str) -> None:
    await cache.cache_run("org-a", "run-1", {"id": "run-1"}, status)
    assert fake_redis.store == {}


async def test_invalidate_org_runs_only_touches_that_org(fake_redis: _FakeRedis) -> None:
    await cache.cache_run("org-a", "run-1", {"id": "run-1"}, "completed")
    await cache.cache_run("org-b", "run-2", {"id": "run-2"}, "completed")

    await cache.invalidate_org_runs("org-a")

    assert await cache.get_cached_run("org-a", "run-1") is None
    assert await cache.get_cached_run("org-b", "run-2") == {"id": "run-2"}


# ── Rate limiter ───────────────────────────────────────────────────────────────


def _pipeline_returning(count: int) -> MagicMock:
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[count, True])
    client = MagicMock()
    client.pipeline.return_value = pipe
    return client


async def test_rate_limit_buckets_are_per_org(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _pipeline_returning(1)
    monkeypatch.setattr(rate_limiter, "get_redis", lambda: client)

    await rate_limiter.check_simulation_rate_limit("org-a")
    await rate_limiter.check_simulation_rate_limit("org-b")

    keys = [call.args[0] for call in client.pipeline.return_value.incr.call_args_list]
    assert keys[0].startswith("ratelimit:simulate:org-a:")
    assert keys[1].startswith("ratelimit:simulate:org-b:")


async def test_rate_limit_exceeded_returns_429_with_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi import HTTPException

    client = _pipeline_returning(rate_limiter._LIMIT_PER_MINUTE + 1)
    monkeypatch.setattr(rate_limiter, "get_redis", lambda: client)

    with pytest.raises(HTTPException) as excinfo:
        await rate_limiter.check_simulation_rate_limit("org-a")

    assert excinfo.value.status_code == 429
    assert int((excinfo.value.headers or {})["Retry-After"]) >= 1


async def test_rate_limiter_fails_open_when_redis_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.pipeline.side_effect = ConnectionError("redis down")
    monkeypatch.setattr(rate_limiter, "get_redis", lambda: client)

    await rate_limiter.check_simulation_rate_limit("org-a")  # must not raise


# ── WebSocket serialization ────────────────────────────────────────────────────


def test_ws_payload_is_json_safe_and_carries_error_detail() -> None:
    run = SimulationRunORM()
    run.id = uuid.uuid4()
    run.segment_id = uuid.uuid4()
    run.stimulus = {"type": "promo"}
    run.status = "failed"
    run.sentiment = None
    run.verbatim_response = None
    run.likelihood_to_convert = Decimal("0.4200")  # NUMERIC columns arrive as Decimal
    run.conversion_score = Decimal("0.3400")
    run.llm_metadata = {"error": "LLM_API_UNAVAILABLE"}
    run.created_at = datetime.now(UTC)
    run.completed_at = None

    payload = ws._serialize_run(run)

    assert payload["conversion_score"] == pytest.approx(0.34)
    assert isinstance(payload["likelihood_to_convert"], float)
    assert payload["error_detail"] == "LLM_API_UNAVAILABLE"
    assert payload["stimulus_type"] == "promo"


# ── Metrics label cardinality ──────────────────────────────────────────────────


async def test_latency_metric_is_labelled_by_route_template_not_raw_path() -> None:
    raw_path = f"/no/such/route/{uuid.uuid4()}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        await client.get("/health")
        await client.get(raw_path)

    paths = {
        sample.labels["path"]
        for metric in API_REQUEST_LATENCY.collect()
        for sample in metric.samples
    }
    assert "/health" in paths
    assert "unmatched" in paths
    assert raw_path not in paths


# ── Feature matrix / DAG contract ──────────────────────────────────────────────


def test_feature_matrix_size_is_len_and_recency_handles_aware_timestamps() -> None:
    user = UserFeatures(
        user_id_hash="h",
        page_view_count=4,
        purchase_count=1,
        session_count=2,
        total_spent=30.0,
        category_diversity=1,
        last_activity=datetime.now(UTC) - timedelta(days=2),
        window_days=30,
    )
    matrix = SegmentFeatureMatrix(segment_id="s", segment_name="n", window_days=30, users=[user])

    # run_simulation_pipeline used a non-existent `matrix.user_count` attribute.
    assert len(matrix) == 1
    assert not hasattr(matrix, "user_count")
    assert user.recency_days == pytest.approx(2.0, abs=0.01)
    assert SegmentFeatureMatrix.from_dict(matrix.to_dict()).computed_at == matrix.computed_at


# ── Kafka lag sensor ───────────────────────────────────────────────────────────


@pytest.fixture
def lag_sensor_cls(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Import the sensor with Airflow stubbed out (Airflow is an optional extra)."""

    class _BaseSensorOperator:
        def __init__(self, **kwargs: Any) -> None:
            self.task_id = kwargs.get("task_id")

    stubs = {
        "airflow": types.ModuleType("airflow"),
        "airflow.plugins_manager": types.ModuleType("airflow.plugins_manager"),
        "airflow.sensors": types.ModuleType("airflow.sensors"),
        "airflow.sensors.base": types.ModuleType("airflow.sensors.base"),
    }
    stubs["airflow.plugins_manager"].AirflowPlugin = object  # type: ignore[attr-defined]
    stubs["airflow.sensors.base"].BaseSensorOperator = _BaseSensorOperator  # type: ignore[attr-defined]
    for name, module in stubs.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.delitem(sys.modules, "orchestration.plugins.kafka_lag_sensor", raising=False)

    from orchestration.plugins.kafka_lag_sensor import KafkaConsumerLagSensor

    return KafkaConsumerLagSensor


@pytest.mark.parametrize(
    ("committed", "end", "max_lag", "expected"),
    [
        (100, 100, 0, True),  # fully caught up
        (90, 100, 10, True),  # within threshold
        (80, 100, 10, False),  # lagging
        (None, 5, 0, False),  # group never committed → whole log is lag
    ],
)
def test_lag_sensor_reads_integer_committed_offsets(
    lag_sensor_cls: Any, committed: int | None, end: int, max_lag: int, expected: bool
) -> None:
    from kafka.structs import TopicPartition

    consumer = MagicMock()
    consumer.partitions_for_topic.return_value = {0}
    consumer.end_offsets.return_value = {TopicPartition("events.purchases", 0): end}
    # kafka-python returns a plain int (or None), not an OffsetAndMetadata.
    consumer.committed.return_value = committed

    sensor = lag_sensor_cls(task_id="t", topic="events.purchases", group_id="g", max_lag=max_lag)
    with patch("kafka.KafkaConsumer", return_value=consumer):
        assert sensor.poke({}) is expected
    consumer.close.assert_called_once()
