"""PII anonymization layer.

All events MUST pass through this module before any data reaches PostgreSQL,
Redis, or any downstream system. Raw PII (email, exact IP) never leaves the
ingestion layer.

Hashing is deterministic (HMAC-SHA256 + project-level salt) so events from
the same user can be correlated without revealing the original identifier.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

from ingestion.schemas.events import (
    AnonPageViewEvent,
    AnonPurchaseEvent,
    AnonSessionEvent,
    RawPageViewEvent,
    RawPurchaseEvent,
    RawSessionEvent,
)

logger = logging.getLogger(__name__)

# Read salt from env; fail loudly in production if not set.
_SALT = os.getenv("PII_SALT", "dev-only-salt-change-in-prod").encode()


def _hmac_sha256(value: str) -> str:
    """Return a deterministic hex digest of `value` keyed with the project salt."""
    return hmac.new(_SALT, value.encode(), hashlib.sha256).hexdigest()


def _mask_ipv4(ip: str) -> str:
    """Return a /24-masked IPv4 string (e.g. '192.168.1.100' → '192.168.1').

    Returns empty string for IPv6 or unparseable addresses — they are not stored.
    """
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}"
    logger.debug("Non-IPv4 address discarded during anonymization: %s", ip[:8])
    return ""


class AnonymizerService:
    """Transforms raw events into PII-free anonymized versions.

    All public methods are pure (no side effects) and return new model instances.
    """

    def anonymize_page_view(self, event: RawPageViewEvent) -> AnonPageViewEvent:
        """Hash user_id and mask IP; all other fields are non-PII.

        Args:
            event: Raw page view event from Kafka.

        Returns:
            Anonymized event safe for persistence.
        """
        return AnonPageViewEvent(
            event_id=event.event_id,
            user_id_hash=_hmac_sha256(event.user_id),
            session_id=event.session_id,
            timestamp_ms=event.timestamp_ms,
            url=event.url,
            referrer=event.referrer,
            category=event.category,
            user_agent=event.user_agent,
            ip_prefix=_mask_ipv4(event.ip_address),
        )

    def anonymize_purchase(self, event: RawPurchaseEvent) -> AnonPurchaseEvent:
        """Hash user_id and email; all other fields are non-PII.

        Args:
            event: Raw purchase event from Kafka.

        Returns:
            Anonymized event safe for persistence.
        """
        return AnonPurchaseEvent(
            event_id=event.event_id,
            user_id_hash=_hmac_sha256(event.user_id),
            email_hash=_hmac_sha256(event.email),
            session_id=event.session_id,
            timestamp_ms=event.timestamp_ms,
            order_id=event.order_id,
            product_id=event.product_id,
            product_name=event.product_name,
            category=event.category,
            amount=event.amount,
            currency=event.currency,
            quantity=event.quantity,
        )

    def anonymize_session(self, event: RawSessionEvent) -> AnonSessionEvent:
        """Hash user_id; session events contain no other direct PII.

        Args:
            event: Raw session event from Kafka.

        Returns:
            Anonymized event safe for persistence.
        """
        return AnonSessionEvent(
            event_id=event.event_id,
            user_id_hash=_hmac_sha256(event.user_id),
            session_id=event.session_id,
            timestamp_ms=event.timestamp_ms,
            event_type=event.event_type,
            duration_seconds=event.duration_seconds,
            page_count=event.page_count,
        )
