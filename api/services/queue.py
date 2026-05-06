"""ARQ Redis queue — async job queue for simulation runs.

Provides the ARQ pool singleton and a FastAPI dependency.
The pool is initialized lazily on first call (eager init in on_startup is
optional but recommended to surface connectivity errors early).

Usage from a router:
    from api.services.queue import QueueDep
    async def my_endpoint(queue: QueueDep): ...

Usage from main.py startup/shutdown:
    from api.services.queue import close_arq_pool, get_arq_pool
"""

from __future__ import annotations

import os
from typing import Annotated

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import Depends

ARQ_REDIS_SETTINGS = RedisSettings(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    database=int(os.getenv("REDIS_DB", "0")),
    password=os.getenv("REDIS_PASSWORD") or None,
)

_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    """Return the module-level ARQ pool, creating it on first call."""
    global _pool
    if _pool is None:
        _pool = await create_pool(ARQ_REDIS_SETTINGS)
    return _pool


async def close_arq_pool() -> None:
    """Close the ARQ pool on application shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


# FastAPI dependency
async def _queue_dep() -> ArqRedis:
    return await get_arq_pool()


QueueDep = Annotated[ArqRedis, Depends(_queue_dep)]
