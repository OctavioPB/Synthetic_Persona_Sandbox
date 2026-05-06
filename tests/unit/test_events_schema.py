"""Unit tests for Avro schema files and event Pydantic models."""

import json
from pathlib import Path

import fastavro
import pytest

from ingestion.schemas.events import (
    RawPageViewEvent,
    RawPurchaseEvent,
    RawSessionEvent,
    SessionEventType,
    load_avro_schema,
)

_SCHEMA_DIR = Path("ingestion/schemas")
_AVSC_FILES = list(_SCHEMA_DIR.glob("*.avsc"))


# ── Avro schema file validation ────────────────────────────────────────────────

@pytest.mark.parametrize("schema_path", _AVSC_FILES, ids=[p.name for p in _AVSC_FILES])
def test_avsc_is_valid_json(schema_path: Path) -> None:
    with schema_path.open() as f:
        data = json.load(f)
    assert isinstance(data, dict)
    assert data.get("type") == "record"


@pytest.mark.parametrize("schema_path", _AVSC_FILES, ids=[p.name for p in _AVSC_FILES])
def test_avsc_parseable_by_fastavro(schema_path: Path) -> None:
    with schema_path.open() as f:
        schema_dict = json.load(f)
    parsed = fastavro.parse_schema(schema_dict)
    assert parsed is not None


@pytest.mark.parametrize("schema_path", _AVSC_FILES, ids=[p.name for p in _AVSC_FILES])
def test_avsc_has_required_fields(schema_path: Path) -> None:
    with schema_path.open() as f:
        data = json.load(f)
    field_names = {f["name"] for f in data["fields"]}
    # Every event must have these core fields
    assert "event_id"     in field_names
    assert "user_id"      in field_names
    assert "session_id"   in field_names
    assert "timestamp_ms" in field_names


# ── load_avro_schema helper ────────────────────────────────────────────────────

def test_load_avro_schema_returns_dict() -> None:
    schema = load_avro_schema("page_view_event")
    assert isinstance(schema, dict)
    assert schema["name"] == "PageViewEvent"


def test_load_avro_schema_unknown_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_avro_schema("nonexistent_event")


# ── Pydantic event model validation ───────────────────────────────────────────

def test_raw_page_view_event_valid() -> None:
    event = RawPageViewEvent(
        event_id="evt-001",
        user_id="user-abc",
        session_id="sess-001",
        timestamp_ms=1_700_000_000_000,
        url="/products/laptop",
        user_agent="Mozilla/5.0",
        ip_address="10.0.0.1",
    )
    assert event.referrer is None
    assert event.category is None


def test_raw_purchase_event_valid() -> None:
    event = RawPurchaseEvent(
        event_id="evt-002",
        user_id="user-abc",
        session_id="sess-001",
        timestamp_ms=1_700_000_001_000,
        order_id="ORD-001",
        product_id="PROD-E01",
        product_name="Laptop Pro 15",
        category="Electronics",
        amount=999.99,
        currency="USD",
        quantity=1,
        email="alice@example.com",
    )
    assert event.currency == "USD"


def test_raw_session_event_default_duration_none() -> None:
    event = RawSessionEvent(
        event_id="evt-003",
        user_id="user-abc",
        session_id="sess-001",
        timestamp_ms=1_700_000_002_000,
        event_type=SessionEventType.SESSION_START,
    )
    assert event.duration_seconds is None
    assert event.page_count is None


def test_session_event_type_enum_values() -> None:
    assert SessionEventType.SESSION_START.value == "SESSION_START"
    assert SessionEventType.SESSION_END.value   == "SESSION_END"
