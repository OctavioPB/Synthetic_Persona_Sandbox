"""Pydantic event models that mirror the Avro schemas.

Used for validation on the producer side and for typed access in consumers.
The canonical schema definitions live in the .avsc files in this directory.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

_SCHEMA_DIR = Path(__file__).parent


def load_avro_schema(name: str) -> dict:  # type: ignore[type-arg]
    """Load a .avsc file as a dict.

    Args:
        name: Schema file name without extension (e.g. 'page_view_event').

    Returns:
        The parsed schema as a dict.
    """
    path = _SCHEMA_DIR / f"{name}.avsc"
    with path.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


# ── Kafka topic names ──────────────────────────────────────────────────────────
TOPIC_PAGE_VIEWS = "events.page_views"
TOPIC_PURCHASES  = "events.purchases"
TOPIC_SESSIONS   = "events.sessions"
TOPIC_DLQ        = "events.dlq"

ALL_TOPICS = [TOPIC_PAGE_VIEWS, TOPIC_PURCHASES, TOPIC_SESSIONS]


# ── Event type discriminator ───────────────────────────────────────────────────
class EventType(str, Enum):
    PAGE_VIEW = "page_view"
    PURCHASE  = "purchase"
    SESSION   = "session"


class SessionEventType(str, Enum):
    SESSION_START = "SESSION_START"
    SESSION_END   = "SESSION_END"


# ── Raw event models (as produced — may contain PII) ──────────────────────────

class RawPageViewEvent(BaseModel):
    event_id:     str
    user_id:      str
    session_id:   str
    timestamp_ms: int
    url:          str
    referrer:     str | None = None
    category:     str | None = None
    user_agent:   str
    ip_address:   str


class RawPurchaseEvent(BaseModel):
    event_id:     str
    user_id:      str
    session_id:   str
    timestamp_ms: int
    order_id:     str
    product_id:   str
    product_name: str
    category:     str
    amount:       float
    currency:     str = "USD"
    quantity:     int
    email:        str


class RawSessionEvent(BaseModel):
    event_id:         str
    user_id:          str
    session_id:       str
    timestamp_ms:     int
    event_type:       SessionEventType
    duration_seconds: int | None = None
    page_count:       int | None = None


# ── Anonymized event models (safe to persist) ──────────────────────────────────

class AnonPageViewEvent(BaseModel):
    event_id:      str
    user_id_hash:  str
    session_id:    str
    timestamp_ms:  int
    url:           str
    referrer:      str | None = None
    category:      str | None = None
    user_agent:    str
    ip_prefix:     str   # e.g. "192.168.1" — /24 mask


class AnonPurchaseEvent(BaseModel):
    event_id:      str
    user_id_hash:  str
    email_hash:    str
    session_id:    str
    timestamp_ms:  int
    order_id:      str
    product_id:    str
    product_name:  str
    category:      str
    amount:        float
    currency:      str
    quantity:      int


class AnonSessionEvent(BaseModel):
    event_id:         str
    user_id_hash:     str
    session_id:       str
    timestamp_ms:     int
    event_type:       SessionEventType
    duration_seconds: int | None = None
    page_count:       int | None = None


# ── DLQ envelope ──────────────────────────────────────────────────────────────

class DLQMessage(BaseModel):
    original_topic:   str
    original_payload: bytes
    error_type:       str
    error_message:    str
    failed_at_ms:     int
