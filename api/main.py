import logging
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.routers import auth, campaigns, health, org, profiles, segments, simulations, ws
from api.services.metrics import API_REQUEST_LATENCY
from api.services.queue import close_arq_pool, get_arq_pool

logger = logging.getLogger(__name__)

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
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "OPB AI Mastery Lab",
        "url": "https://github.com/opb/synthetic-persona-sandbox",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {"name": "health",      "description": "Service liveness and readiness."},
        {"name": "auth",        "description": "JWT issuance and API key management."},
        {"name": "org",         "description": "Organization management, members, and audit log."},
        {"name": "segments",    "description": "Customer segment CRUD."},
        {"name": "simulations", "description": "Simulation run lifecycle (async + sync)."},
        {"name": "campaigns",   "description": "Campaign and ad variant management."},
        {"name": "profiles",    "description": "Real-time user profile state (Kafka-backed)."},
        {"name": "ws",          "description": "WebSocket — live simulation progress stream."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def record_request_latency(request: Request, call_next: object) -> Response:
    """Record per-route latency in the Prometheus histogram."""
    t0 = time.monotonic()
    response: Response = await call_next(request)  # type: ignore[operator]
    elapsed = time.monotonic() - t0
    API_REQUEST_LATENCY.labels(
        method=request.method,
        path=request.url.path,
        status_code=str(response.status_code),
    ).observe(elapsed)
    return response


@app.middleware("http")
async def audit_write_middleware(request: Request, call_next: object) -> Response:
    """Write audit events for mutating requests after they complete."""
    response: Response = await call_next(request)  # type: ignore[operator]

    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return response

    # Only audit when a claims object was attached by auth dependency
    claims = getattr(request.state, "claims", None)
    if claims is None:
        return response

    try:
        from api.services.audit import log_event
        from api.services.db import get_async_session

        async with get_async_session() as db:
            await log_event(
                db=db,
                claims=claims,
                action=f"{request.method.lower()}.{request.url.path.strip('/').replace('/', '.')}",
                request=request,
                status_code=response.status_code,
            )
    except Exception as exc:
        logger.warning("Audit middleware write failed (non-fatal): %s", exc)

    return response


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
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.on_event("startup")
async def on_startup() -> None:
    await get_arq_pool()
    logger.info("Synthetic Persona Sandbox API starting up (v0.3.0).")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    from api.services.cache import close_redis
    await close_arq_pool()
    await close_redis()
    logger.info("Synthetic Persona Sandbox API shutting down.")
