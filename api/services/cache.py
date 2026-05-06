"""Redis cache layer for simulation results and segment embeddings — S10-06.

TTL strategy:
  - completed simulation runs:  24 hours (immutable once complete)
  - pending/running runs:        30 seconds (volatile, polled by WS)
  - segment profile summaries:   1 hour (updated when re-trained)
  - org info:                    5 minutes (low-churn reference data)

All keys are namespaced: spb:{scope}:{id}
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_REDIS_URL = (
    f"redis://:{os.getenv('REDIS_PASSWORD', '')}@"
    f"{os.getenv('REDIS_HOST', 'localhost')}:"
    f"{os.getenv('REDIS_PORT', '6379')}/0"
).replace("://:@", "://")  # strip empty password

_TTL_SIMULATION_COMPLETE = 86_400   # 24 h
_TTL_SIMULATION_PENDING  = 30       # 30 s
_TTL_SEGMENT_SUMMARY     = 3_600    # 1 h
_TTL_ORG_INFO            = 300      # 5 min

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(_REDIS_URL, decode_responses=True)
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


# ── Simulation run cache ──────────────────────────────────────────────────────

def _run_key(run_id: str) -> str:
    return f"spb:run:{run_id}"


async def get_cached_run(run_id: str) -> dict[str, Any] | None:
    try:
        r = await get_redis()
        raw = await r.get(_run_key(run_id))
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("Cache read failed for run %s (non-fatal): %s", run_id, exc)
        return None


async def cache_run(run_id: str, data: dict[str, Any], status: str) -> None:
    ttl = _TTL_SIMULATION_COMPLETE if status == "completed" else _TTL_SIMULATION_PENDING
    try:
        r = await get_redis()
        await r.setex(_run_key(run_id), ttl, json.dumps(data))
    except Exception as exc:
        logger.warning("Cache write failed for run %s (non-fatal): %s", run_id, exc)


async def invalidate_run(run_id: str) -> None:
    try:
        r = await get_redis()
        await r.delete(_run_key(run_id))
    except Exception as exc:
        logger.warning("Cache invalidation failed for run %s (non-fatal): %s", run_id, exc)


# ── Segment summary cache ─────────────────────────────────────────────────────

def _segment_key(org_id: str, segment_id: str) -> str:
    return f"spb:segment:{org_id}:{segment_id}"


async def get_cached_segment(org_id: str, segment_id: str) -> dict[str, Any] | None:
    try:
        r = await get_redis()
        raw = await r.get(_segment_key(org_id, segment_id))
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("Cache read failed for segment %s (non-fatal): %s", segment_id, exc)
        return None


async def cache_segment(org_id: str, segment_id: str, data: dict[str, Any]) -> None:
    try:
        r = await get_redis()
        await r.setex(_segment_key(org_id, segment_id), _TTL_SEGMENT_SUMMARY, json.dumps(data))
    except Exception as exc:
        logger.warning("Cache write failed for segment %s (non-fatal): %s", segment_id, exc)


async def invalidate_segment(org_id: str, segment_id: str) -> None:
    try:
        r = await get_redis()
        await r.delete(_segment_key(org_id, segment_id))
    except Exception as exc:
        logger.warning("Cache invalidation failed for segment %s (non-fatal): %s", segment_id, exc)


# ── Org info cache ────────────────────────────────────────────────────────────

def _org_key(org_id: str) -> str:
    return f"spb:org:{org_id}"


async def get_cached_org(org_id: str) -> dict[str, Any] | None:
    try:
        r = await get_redis()
        raw = await r.get(_org_key(org_id))
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("Cache read failed for org %s (non-fatal): %s", org_id, exc)
        return None


async def cache_org(org_id: str, data: dict[str, Any]) -> None:
    try:
        r = await get_redis()
        await r.setex(_org_key(org_id), _TTL_ORG_INFO, json.dumps(data))
    except Exception as exc:
        logger.warning("Cache write failed for org %s (non-fatal): %s", org_id, exc)


async def invalidate_org(org_id: str) -> None:
    try:
        r = await get_redis()
        await r.delete(_org_key(org_id))
    except Exception as exc:
        logger.warning("Cache invalidation failed for org %s (non-fatal): %s", org_id, exc)
