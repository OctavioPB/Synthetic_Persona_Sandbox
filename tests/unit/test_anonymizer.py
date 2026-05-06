"""Unit tests for the PII anonymizer."""

import os

import pytest

# Set salt before importing — module reads it at import time
os.environ["PII_SALT"] = "test-salt-fixed"

from ingestion.anonymizer import AnonymizerService, _hmac_sha256, _mask_ipv4
from ingestion.schemas.events import (
    RawPageViewEvent,
    RawPurchaseEvent,
    RawSessionEvent,
    SessionEventType,
)


# ── _mask_ipv4 ─────────────────────────────────────────────────────────────────

def test_mask_ipv4_returns_three_octets() -> None:
    assert _mask_ipv4("192.168.1.100") == "192.168.1"


def test_mask_ipv4_returns_empty_for_ipv6() -> None:
    result = _mask_ipv4("2001:db8::1")
    assert result == ""


def test_mask_ipv4_returns_empty_for_invalid() -> None:
    assert _mask_ipv4("not-an-ip") == ""


# ── _hmac_sha256 ───────────────────────────────────────────────────────────────

def test_hmac_sha256_is_deterministic() -> None:
    assert _hmac_sha256("user-123") == _hmac_sha256("user-123")


def test_hmac_sha256_differs_for_different_inputs() -> None:
    assert _hmac_sha256("user-123") != _hmac_sha256("user-456")


def test_hmac_sha256_returns_hex_string() -> None:
    result = _hmac_sha256("test")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


# ── AnonymizerService ──────────────────────────────────────────────────────────

@pytest.fixture()
def anonymizer() -> AnonymizerService:
    return AnonymizerService()


@pytest.fixture()
def raw_page_view() -> RawPageViewEvent:
    return RawPageViewEvent(
        event_id="evt-001",
        user_id="user-abc",
        session_id="sess-001",
        timestamp_ms=1_700_000_000_000,
        url="/products/electronics/laptop",
        referrer="https://google.com",
        category="Electronics",
        user_agent="Mozilla/5.0",
        ip_address="203.0.113.42",
    )


@pytest.fixture()
def raw_purchase() -> RawPurchaseEvent:
    return RawPurchaseEvent(
        event_id="evt-002",
        user_id="user-abc",
        session_id="sess-001",
        timestamp_ms=1_700_000_001_000,
        order_id="ORD-001",
        product_id="PROD-E01",
        product_name="Laptop Pro 15",
        category="Electronics",
        amount=1299.99,
        currency="USD",
        quantity=1,
        email="alice123@example.com",
    )


@pytest.fixture()
def raw_session() -> RawSessionEvent:
    return RawSessionEvent(
        event_id="evt-003",
        user_id="user-abc",
        session_id="sess-001",
        timestamp_ms=1_700_000_002_000,
        event_type=SessionEventType.SESSION_START,
    )


class TestAnonymizePageView:
    def test_user_id_is_hashed(self, anonymizer: AnonymizerService, raw_page_view: RawPageViewEvent) -> None:
        anon = anonymizer.anonymize_page_view(raw_page_view)
        assert anon.user_id_hash != raw_page_view.user_id
        assert len(anon.user_id_hash) == 64

    def test_ip_is_masked_to_prefix(self, anonymizer: AnonymizerService, raw_page_view: RawPageViewEvent) -> None:
        anon = anonymizer.anonymize_page_view(raw_page_view)
        assert anon.ip_prefix == "203.0.113"
        assert "42" not in anon.ip_prefix

    def test_non_pii_fields_preserved(self, anonymizer: AnonymizerService, raw_page_view: RawPageViewEvent) -> None:
        anon = anonymizer.anonymize_page_view(raw_page_view)
        assert anon.event_id  == raw_page_view.event_id
        assert anon.url       == raw_page_view.url
        assert anon.category  == raw_page_view.category

    def test_no_raw_ip_in_output(self, anonymizer: AnonymizerService, raw_page_view: RawPageViewEvent) -> None:
        anon = anonymizer.anonymize_page_view(raw_page_view)
        # The full IP must not appear anywhere in the serialized output
        assert raw_page_view.ip_address not in anon.model_dump_json()


class TestAnonymizePurchase:
    def test_user_id_and_email_hashed(self, anonymizer: AnonymizerService, raw_purchase: RawPurchaseEvent) -> None:
        anon = anonymizer.anonymize_purchase(raw_purchase)
        assert anon.user_id_hash != raw_purchase.user_id
        assert anon.email_hash   != raw_purchase.email
        assert len(anon.email_hash) == 64

    def test_same_email_always_same_hash(self, anonymizer: AnonymizerService, raw_purchase: RawPurchaseEvent) -> None:
        anon1 = anonymizer.anonymize_purchase(raw_purchase)
        anon2 = anonymizer.anonymize_purchase(raw_purchase)
        assert anon1.email_hash == anon2.email_hash

    def test_no_raw_email_in_output(self, anonymizer: AnonymizerService, raw_purchase: RawPurchaseEvent) -> None:
        anon = anonymizer.anonymize_purchase(raw_purchase)
        assert raw_purchase.email not in anon.model_dump_json()

    def test_amount_preserved(self, anonymizer: AnonymizerService, raw_purchase: RawPurchaseEvent) -> None:
        anon = anonymizer.anonymize_purchase(raw_purchase)
        assert anon.amount == raw_purchase.amount


class TestAnonymizeSession:
    def test_user_id_hashed(self, anonymizer: AnonymizerService, raw_session: RawSessionEvent) -> None:
        anon = anonymizer.anonymize_session(raw_session)
        assert anon.user_id_hash != raw_session.user_id

    def test_event_type_preserved(self, anonymizer: AnonymizerService, raw_session: RawSessionEvent) -> None:
        anon = anonymizer.anonymize_session(raw_session)
        assert anon.event_type == raw_session.event_type

    def test_duration_none_for_session_start(self, anonymizer: AnonymizerService, raw_session: RawSessionEvent) -> None:
        anon = anonymizer.anonymize_session(raw_session)
        assert anon.duration_seconds is None
