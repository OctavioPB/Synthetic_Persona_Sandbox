"""Profile state endpoint — reads real-time behavioral data from Redis."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os

import redis
from fastapi import APIRouter, HTTPException

from api.models.profile import ProfileState

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profiles", tags=["profiles"])

_SALT = os.getenv("PII_SALT", "dev-only-salt-change-in-prod").encode()
_PROFILE_KEY = "profile:{}"


def _get_redis() -> redis.Redis:  # type: ignore[type-arg]
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
    )


def _hash_user_id(user_id: str) -> str:
    """Hash raw user_id with the same algorithm used by the anonymizer."""
    return hmac.new(_SALT, user_id.encode(), hashlib.sha256).hexdigest()


@router.get("/{user_id}/state", response_model=ProfileState)
async def get_profile_state(user_id: str) -> ProfileState:
    """Return the real-time behavioral profile for a user.

    Accepts the raw user_id; internally maps it to the anonymized hash
    used as the Redis key.

    Args:
        user_id: Raw user identifier (UUID or opaque string).

    Returns:
        ProfileState with aggregated behavioral metrics.

    Raises:
        HTTPException 404: If no events have been ingested for this user yet.
    """
    user_id_hash = _hash_user_id(user_id)
    key = _PROFILE_KEY.format(user_id_hash)

    try:
        r = _get_redis()
        data = r.hgetall(key)
    except redis.RedisError as exc:
        logger.error("Redis error fetching profile %s: %s", user_id_hash[:8], exc)
        raise HTTPException(status_code=503, detail="Profile store unavailable") from exc

    if not data:
        raise HTTPException(status_code=404, detail="No behavioral data found for this user")

    raw_cats = data.get("categories_viewed", "[]")
    try:
        cats: list[str] = json.loads(raw_cats)
    except json.JSONDecodeError:
        cats = []

    return ProfileState(
        user_id_hash=user_id_hash,
        page_views_total=int(data.get("page_views_total", 0)),
        purchase_count=int(data.get("purchase_count", 0)),
        purchase_total_amount=float(data.get("purchase_total_amount", 0.0)),
        session_count=int(data.get("session_count", 0)),
        categories_viewed=cats,
        last_seen=data.get("last_seen"),
    )
