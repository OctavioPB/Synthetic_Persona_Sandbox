"""Redis cache layer and shared async Redis client — S10-06.

TTL strategy:
  - completed simulation runs:  24 hours (immutable once complete)
  - org info:                    5 minutes (low-churn reference data)

Runs that are still pending/running are never cached: clients poll them for
status changes, so serving a cached snapshot would hide the transition.

All keys are namespaced and tenant-scoped: spb:{scope}:{org_id}[:{id}]

Cache failures are non-fatal: reads fall through to the database and writes
are skipped, so a Redis outage degrades latency rather than availability.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_TTL_SIMULATION_COMPLETE = 86_400  # 24 h
_TTL_ORG_INFO = 300  # 5 min

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return the process-wide async Redis client, creating it on first use.

    Shared by the cache, the rate limiter and the profile-state router so the
    API holds a single connection pool.
    """
    global _client
    if _client is None:
        _client = aioredis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD") or None,
            decode_responses=True,
        )
    return _client


async def close_redis() -> None:
    """Close the shared client on application shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


# ── Generic helpers ───────────────────────────────────────────────────────────


async def _get_json(key: str) -> dict[str, Any] | None:
    try:
        raw = await get_redis().get(key)
    except Exception as exc:
        logger.warning("Cache read failed for %s (non-fatal): %s", key, exc)
        return None
    if not raw:
        return None
    data: dict[str, Any] = json.loads(raw)
    return data


async def _set_json(key: str, ttl: int, data: dict[str, Any]) -> None:
    try:
        await get_redis().setex(key, ttl, json.dumps(data))
    except Exception as exc:
        logger.warning("Cache write failed for %s (non-fatal): %s", key, exc)


# ── Simulation run cache ──────────────────────────────────────────────────────


def _run_key(org_id: str, run_id: str) -> str:
    return f"spb:run:{org_id}:{run_id}"


async def get_cached_run(org_id: str, run_id: str) -> dict[str, Any] | None:
    """Return a cached completed run for this org, or None on a miss."""
    return await _get_json(_run_key(org_id, run_id))


async def cache_run(org_id: str, run_id: str, data: dict[str, Any], status: str) -> None:
    """Cache a run response. Only completed (immutable) runs are stored."""
    if status != "completed":
        return
    await _set_json(_run_key(org_id, run_id), _TTL_SIMULATION_COMPLETE, data)


async def invalidate_org_runs(org_id: str) -> None:
    """Drop every cached run for an org (used when its data is deleted)."""
    try:
        client = get_redis()
        keys = [key async for key in client.scan_iter(match=_run_key(org_id, "*"), count=500)]
        if keys:
            await client.unlink(*keys)
    except Exception as exc:
        logger.warning("Cache invalidation failed for org %s (non-fatal): %s", org_id, exc)


# ── Org info cache ────────────────────────────────────────────────────────────


def _org_key(org_id: str) -> str:
    return f"spb:org:{org_id}"


async def get_cached_org(org_id: str) -> dict[str, Any] | None:
    return await _get_json(_org_key(org_id))


async def cache_org(org_id: str, data: dict[str, Any]) -> None:
    await _set_json(_org_key(org_id), _TTL_ORG_INFO, data)
