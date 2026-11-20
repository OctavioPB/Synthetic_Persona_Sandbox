"""Profile state endpoint — reads real-time behavioral data from Redis."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable
from typing import cast

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException

from api.auth.dependencies import CurrentUser
from api.models.profile import ProfileState
from api.services.cache import get_redis
from ingestion.anonymizer import hash_identifier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profiles", tags=["profiles"])

_PROFILE_KEY = "profile:{}"


@router.get("/{user_id}/state", response_model=ProfileState)
async def get_profile_state(user_id: str, _: CurrentUser) -> ProfileState:
    """Return the real-time behavioral profile for a user.

    Accepts the raw user_id; internally maps it to the anonymized hash
    used as the Redis key.

    Args:
        user_id: Raw user identifier (UUID or opaque string).

    Returns:
        ProfileState with aggregated behavioral metrics.

    Raises:
        HTTPException 404: If no events have been ingested for this user yet.
        HTTPException 503: If the profile store is unreachable.
    """
    user_id_hash = hash_identifier(user_id)

    try:
        data = await cast(
            "Awaitable[dict[str, str]]", get_redis().hgetall(_PROFILE_KEY.format(user_id_hash))
        )
    except aioredis.RedisError as exc:
        logger.error("Redis error fetching profile %s: %s", user_id_hash[:8], exc)
        raise HTTPException(status_code=503, detail="Profile store unavailable") from exc

    if not data:
        raise HTTPException(status_code=404, detail="No behavioral data found for this user")

    try:
        cats: list[str] = json.loads(data.get("categories_viewed", "[]"))
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
