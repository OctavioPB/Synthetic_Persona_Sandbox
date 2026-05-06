"""Redis-backed rate limiter for the simulation API.

Strategy: sliding window counter per org_id per minute.
Uses Redis INCR + EXPIRE — atomic for single-key operations.

Default: 60 simulation requests per org per minute.
Exceeding the limit raises HTTP 429.

Usage from a router:
    from api.services.rate_limiter import check_simulation_rate_limit, RateLimitDep

    @router.post("/simulate/run")
    async def run(body: ..., _: RateLimitDep): ...
"""

from __future__ import annotations

import logging
import os
import time
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException

logger = logging.getLogger(__name__)

_LIMIT_PER_MINUTE = int(os.getenv("SIMULATE_RATE_LIMIT", "60"))
_WINDOW_SECONDS   = 60

# Hardcoded org_id for Sprint 6 — replaced by Auth context in Sprint 9
_DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"

_redis_client: aioredis.Redis | None = None  # type: ignore[type-arg]


def _get_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD") or None,
            decode_responses=True,
        )
    return _redis_client


async def check_simulation_rate_limit(org_id: str = _DEFAULT_ORG_ID) -> None:
    """Raise HTTP 429 if the org has exceeded the per-minute simulation limit.

    The rate limit window is aligned to clock minutes (not rolling), so
    the counter resets at the start of each minute. This is simpler than
    a true rolling window but sufficient for MVP rate abuse prevention.

    Args:
        org_id: Organization UUID string.

    Raises:
        HTTPException(429): If the rate limit has been exceeded.
    """
    window_bucket = int(time.time()) // _WINDOW_SECONDS
    key           = f"ratelimit:simulate:{org_id}:{window_bucket}"

    client = _get_redis()
    try:
        count = await client.incr(key)
        if count == 1:
            # Set TTL only on first increment to prevent key living forever
            await client.expire(key, _WINDOW_SECONDS * 2)

        if count > _LIMIT_PER_MINUTE:
            logger.warning(
                "Rate limit exceeded for org %s: %d requests in current window.",
                org_id, count,
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "error":       "rate_limit_exceeded",
                    "limit":        _LIMIT_PER_MINUTE,
                    "window_secs":  _WINDOW_SECONDS,
                    "retry_after":  _WINDOW_SECONDS - (int(time.time()) % _WINDOW_SECONDS),
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Redis unavailable — fail open to avoid blocking simulations
        logger.warning("Rate limiter Redis error (failing open): %s", exc)


# FastAPI dependency
async def _rate_limit_dep() -> None:
    await check_simulation_rate_limit()


RateLimitDep = Annotated[None, Depends(_rate_limit_dep)]
