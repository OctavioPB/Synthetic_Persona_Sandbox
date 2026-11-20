"""Redis-backed rate limiter for the simulation API.

Strategy: fixed-window counter per org_id per clock minute (INCR + EXPIRE).

Default: 60 simulation requests per org per minute, configurable through
SIMULATE_RATE_LIMIT (or RATE_LIMIT_PER_MINUTE, the name used by the k8s
ConfigMap). Exceeding the limit raises HTTP 429 with a Retry-After header.

Usage from a router:
    from api.services.rate_limiter import RateLimitDep

    @router.post("/simulate/run")
    async def run(body: ..., _: RateLimitDep): ...
"""

from __future__ import annotations

import logging
import os
import time
from typing import Annotated

from fastapi import Depends, HTTPException

from api.auth.dependencies import CurrentUser
from api.services.cache import get_redis

logger = logging.getLogger(__name__)

_LIMIT_PER_MINUTE = int(
    os.getenv("SIMULATE_RATE_LIMIT") or os.getenv("RATE_LIMIT_PER_MINUTE") or "60"
)
_WINDOW_SECONDS = 60


async def check_simulation_rate_limit(org_id: str) -> None:
    """Raise HTTP 429 if the org has exceeded the per-minute simulation limit.

    The window is aligned to clock minutes (not rolling), so the counter resets
    at the start of each minute. Simpler than a true sliding window and
    sufficient for abuse prevention.

    Args:
        org_id: Organization UUID string — each tenant gets its own bucket.

    Raises:
        HTTPException(429): If the rate limit has been exceeded.
    """
    now = int(time.time())
    key = f"ratelimit:simulate:{org_id}:{now // _WINDOW_SECONDS}"

    try:
        # INCR + EXPIRE in one round trip; EXPIRE on every hit is harmless and
        # guarantees the key can never be left without a TTL.
        pipe = get_redis().pipeline(transaction=False)
        pipe.incr(key)
        pipe.expire(key, _WINDOW_SECONDS * 2)
        count, _ = await pipe.execute()
    except Exception as exc:
        # Redis unavailable — fail open to avoid blocking simulations
        logger.warning("Rate limiter Redis error (failing open): %s", exc)
        return

    if count > _LIMIT_PER_MINUTE:
        retry_after = _WINDOW_SECONDS - (now % _WINDOW_SECONDS)
        logger.warning(
            "Rate limit exceeded for org %s: %d requests in current window.", org_id, count
        )
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "limit": _LIMIT_PER_MINUTE,
                "window_secs": _WINDOW_SECONDS,
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )


async def _rate_limit_dep(claims: CurrentUser) -> None:
    await check_simulation_rate_limit(str(claims.org_id))


RateLimitDep = Annotated[None, Depends(_rate_limit_dep)]
