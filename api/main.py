"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api import __version__
from api.auth.jwt_handler import assert_secure_config
from api.routers import admin, auth, campaigns, health, org, profiles, segments, simulations, ws
from api.services.audit import log_event
from api.services.cache import close_redis
from api.services.db import get_async_session
from api.services.metrics import API_REQUEST_LATENCY, QUEUE_DEPTH
from api.services.queue import ARQ_QUEUE_NAME, close_arq_pool, get_arq_pool

logger = logging.getLogger(__name__)

# Vite falls back to 5174+ when 5173 is taken, so local dev allows a small range.
_DEFAULT_CORS_ORIGINS = ",".join(
    [f"http://localhost:{port}" for port in (5173, 5174, 5175, 5176, 5177, 3000)]
)
_AUDITED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

CallNext = Callable[[Request], Awaitable[Response]]


def _cors_origins() -> list[str]:
    """Allowed browser origins, from the comma-separated CORS_ORIGINS env var."""
    raw = os.getenv("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _route_template(request: Request) -> str:
    """Return the matched route template (e.g. /simulate/runs/{run_id}).

    Using the template instead of the raw path keeps Prometheus label
    cardinality bounded — raw paths embed UUIDs and would create one time
    series per resource.
    """
    route = request.scope.get("route")
    return getattr(route, "path", None) or "unmatched"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    assert_secure_config()
    try:
        await get_arq_pool()
    except Exception as exc:
        # The pool is created lazily on first enqueue, so a Redis blip at boot
        # should not keep read-only endpoints (and /health) from coming up.
        logger.warning("ARQ pool not available at startup (will retry lazily): %s", exc)
    logger.info("Synthetic Persona Sandbox API starting up (v%s).", __version__)
    yield
    await close_arq_pool()
    await close_redis()
    logger.info("Synthetic Persona Sandbox API shutting down.")


app = FastAPI(
    title="Synthetic Persona Sandbox API",
    description=(
        "AI-powered marketing simulation platform. Create synthetic digital twins of customer "
        "segments and test campaigns before spending on real ads.\n\n"
        "**Authentication:** Bearer JWT or `X-API-Key` header. "
        "Set `AUTH_REQUIRED=true` in production.\n\n"
        "**Interactive docs:** `/docs` (Swagger) · `/redoc` (ReDoc)\n\n"
        "**Full API reference:** [docs/api/README.md]"
        "(https://github.com/opb/synthetic-persona-sandbox/blob/main/docs/api/README.md)"
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": "OPB AI Mastery Lab",
        "url": "https://github.com/opb/synthetic-persona-sandbox",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://github.com/opb/synthetic-persona-sandbox/blob/main/LICENSE",
    },
    openapi_tags=[
        {"name": "admin", "description": "Seed and clear database — dev/staging only."},
        {"name": "health", "description": "Service liveness and readiness."},
        {"name": "auth", "description": "JWT issuance and API key management."},
        {"name": "org", "description": "Organization management, members, and audit log."},
        {"name": "segments", "description": "Customer segment CRUD."},
        {"name": "simulations", "description": "Simulation run lifecycle (async + sync)."},
        {"name": "campaigns", "description": "Campaign and ad variant management."},
        {"name": "profiles", "description": "Real-time user profile state (Kafka-backed)."},
        {"name": "websocket", "description": "WebSocket — live simulation progress stream."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def record_request_latency(request: Request, call_next: CallNext) -> Response:
    """Record per-route latency in the Prometheus histogram."""
    t0 = time.monotonic()
    response = await call_next(request)
    API_REQUEST_LATENCY.labels(
        method=request.method,
        path=_route_template(request),
        status_code=str(response.status_code),
    ).observe(time.monotonic() - t0)
    return response


@app.middleware("http")
async def audit_write_middleware(request: Request, call_next: CallNext) -> Response:
    """Write audit events for mutating requests after they complete."""
    response = await call_next(request)

    if request.method not in _AUDITED_METHODS:
        return response

    # Only audit when a claims object was attached by the auth dependency
    claims = getattr(request.state, "claims", None)
    if claims is None:
        return response

    try:
        async with get_async_session() as db:
            await log_event(
                db=db,
                claims=claims,
                action=f"{request.method.lower()}.{request.url.path.strip('/').replace('/', '.')}",
                request=request,
                status_code=response.status_code,
            )
            # This session is independent of the request's — without an explicit
            # commit the audit row is rolled back when the context exits.
            await db.commit()
    except Exception as exc:
        logger.warning("Audit middleware write failed (non-fatal): %s", exc)

    return response


app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(org.router)
app.include_router(health.router)
app.include_router(profiles.router)
app.include_router(segments.router)
app.include_router(simulations.router)
app.include_router(campaigns.router)
app.include_router(ws.router)


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:
    """Expose Prometheus metrics for scraping."""
    # Queue depth is read from Redis at scrape time. Tracking it with inc()/dec()
    # cannot work: the API enqueues and a separate worker process dequeues, and
    # each process has its own copy of the gauge.
    try:
        pool = await get_arq_pool()
        QUEUE_DEPTH.set(await pool.zcard(ARQ_QUEUE_NAME))
    except Exception as exc:
        logger.debug("Could not read ARQ queue depth: %s", exc)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
