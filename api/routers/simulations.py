"""Simulations API — Sprint 4 (inline) → Sprint 6 (ARQ-queued) → S9-02 (auth).

POST /simulate/run        — enqueue async simulation job (202 Accepted)
POST /simulate/run/sync   — inline synchronous run (for testing / CI)
GET  /simulate/runs       — list simulation runs (paginated, with filters)
GET  /simulate/runs/{id}  — get a single run by ID
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import require
from api.auth.jwt_handler import TokenClaims
from api.auth.rbac import Permission
from api.models.segment import SegmentORM
from api.models.simulation import (
    SimulateRunRequest,
    SimulationRunListResponse,
    SimulationRunORM,
    SimulationRunResponse,
    SimulationStatus,
)
from api.services.cache import cache_run, get_cached_run
from api.services.db import get_db
from api.services.metrics import SIMULATION_TOTAL
from api.services.queue import QueueDep
from api.services.rate_limiter import RateLimitDep
from ml.synthetic_data.conversion_scorer import ConversionScorer
from ml.synthetic_data.persona_inference import PersonaInferenceService
from ml.synthetic_data.stimulus_schema import (
    AdCopyStimulus,
    AnyStimulus,
    PriceChangeStimulus,
    PromoStimulus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulate", tags=["simulations"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
RunClaims = Annotated[TokenClaims, Depends(require(Permission.SIMULATIONS_RUN))]
ReadClaims = Annotated[TokenClaims, Depends(require(Permission.SIMULATIONS_READ))]

_stimulus_adapter: TypeAdapter[AdCopyStimulus | PriceChangeStimulus | PromoStimulus] = TypeAdapter(
    AnyStimulus
)
_scorer = ConversionScorer()


@lru_cache(maxsize=1)
def _inference_service() -> PersonaInferenceService:
    """Build the inference service on first use rather than at import time."""
    return PersonaInferenceService()


def _parse_stimulus(
    data: dict[str, Any],
) -> AdCopyStimulus | PriceChangeStimulus | PromoStimulus:
    """Deserialize a raw stimulus dict via the discriminated union."""
    try:
        return _stimulus_adapter.validate_python(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid stimulus payload: {exc}") from exc


def _parse_uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {field} format") from exc


async def _get_segment_or_404(db: AsyncSession, segment_id: str, org_id: uuid.UUID) -> SegmentORM:
    segment_uid = _parse_uuid(segment_id, "segment_id")
    result = await db.execute(
        select(SegmentORM).where(SegmentORM.id == segment_uid, SegmentORM.org_id == org_id)
    )
    segment = result.scalar_one_or_none()
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


# ── Async (queued) endpoint — primary path ─────────────────────────────────────


@router.post("/run", response_model=SimulationRunResponse, status_code=202)
async def run_simulation_async(
    body: SimulateRunRequest,
    claims: RunClaims,
    db: DbDep,
    queue: QueueDep,
    _: RateLimitDep,
) -> SimulationRunResponse:
    """Enqueue a simulation job.

    Returns 202 Accepted with status='pending'. Poll via GET /simulate/runs/{id}
    or stream progress via WebSocket /ws/simulations/{id}.
    """
    segment = await _get_segment_or_404(db, body.segment_id, claims.org_id)
    stimulus = _parse_stimulus(body.stimulus)
    stimulus_payload = stimulus.model_dump(mode="json")

    run = SimulationRunORM(
        org_id=claims.org_id,
        segment_id=segment.id,
        stimulus=stimulus_payload,
        status="pending",
        model_id=body.model,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    response = SimulationRunResponse.from_orm(run)

    # Commit before enqueueing: the worker updates this row by id, and a fast
    # worker would otherwise race the request's end-of-request commit and
    # update zero rows.
    await db.commit()

    try:
        await queue.enqueue_job(
            "run_simulation_job",
            run_id=response.id,
            segment_id=str(segment.id),
            segment_name=segment.name,
            definition=segment.definition,
            stimulus=stimulus_payload,
            temperature=body.temperature,
            model=body.model,
            _job_id=response.id,
        )
    except Exception as exc:
        # Don't leave an orphan 'pending' row that no worker will ever pick up.
        run.status = "failed"
        run.llm_metadata = {"error": "QUEUE_UNAVAILABLE"}
        run.completed_at = datetime.now(UTC)
        await db.commit()
        logger.error("Could not enqueue simulation run %s: %s", response.id, exc)
        raise HTTPException(status_code=503, detail="Simulation queue unavailable") from exc

    SIMULATION_TOTAL.labels(stimulus_type=stimulus.type).inc()
    logger.info(
        "Enqueued simulation run %s for segment '%s' (stimulus=%s).",
        response.id,
        segment.name,
        stimulus.type,
    )
    return response


# ── Sync endpoint — used by integration tests and the Airflow DAG ─────────────


@router.post("/run/sync", response_model=SimulationRunResponse, status_code=201)
async def run_simulation_sync(
    body: SimulateRunRequest,
    claims: RunClaims,
    db: DbDep,
) -> SimulationRunResponse:
    """Run a simulation synchronously (the request blocks until it finishes).

    Intended for CI, integration tests, and the Airflow DAG.
    """
    segment = await _get_segment_or_404(db, body.segment_id, claims.org_id)
    stimulus = _parse_stimulus(body.stimulus)

    run = SimulationRunORM(
        org_id=claims.org_id,
        segment_id=segment.id,
        stimulus=stimulus.model_dump(mode="json"),
        status="running",
        model_id=body.model,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    try:
        # The inference client is synchronous (HTTP call + retries with sleeps);
        # run it in a worker thread so it doesn't stall the event loop.
        response = await asyncio.to_thread(
            _inference_service().generate,
            segment_id=str(segment.id),
            segment_name=segment.name,
            definition=segment.definition,
            stimulus=stimulus,
            model=body.model,
            temperature=body.temperature,
        )
    except Exception as exc:
        run.status = "failed"
        run.llm_metadata = {"error": str(exc)}
        run.completed_at = datetime.now(UTC)
        # Commit explicitly — raising below makes the session dependency roll
        # back, which would erase the record of the failed run.
        await db.commit()
        logger.error("Sync simulation run %s failed: %s", run.id, exc)
        raise HTTPException(status_code=502, detail=f"Persona inference failed: {exc}") from exc

    run.verbatim_response = response.verbatim_response
    run.sentiment = response.sentiment
    run.likelihood_to_convert = response.likelihood_to_convert
    run.conversion_score = _scorer.score(response)
    run.llm_metadata = {
        "key_factors": response.key_factors,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "latency_ms": response.latency_ms,
    }
    run.status = "completed"
    run.completed_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(run)
    logger.info(
        "Sync run %s completed: segment=%s score=%.3f",
        run.id,
        segment.name,
        run.conversion_score or 0.0,
    )
    return SimulationRunResponse.from_orm(run)


# ── Read endpoints ─────────────────────────────────────────────────────────────


@router.get("/runs", response_model=SimulationRunListResponse)
async def list_runs(
    claims: ReadClaims,
    db: DbDep,
    segment_id: str | None = Query(default=None),
    status: Annotated[SimulationStatus | None, Query(description="Filter by status.")] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> SimulationRunListResponse:
    """List simulation runs with optional filters."""
    filters = [SimulationRunORM.org_id == claims.org_id]
    if segment_id is not None:
        filters.append(SimulationRunORM.segment_id == _parse_uuid(segment_id, "segment_id"))
    if status is not None:
        filters.append(SimulationRunORM.status == status)

    total: int = (
        await db.execute(select(func.count()).select_from(SimulationRunORM).where(*filters))
    ).scalar_one()
    rows = await db.execute(
        select(SimulationRunORM)
        .where(*filters)
        .order_by(SimulationRunORM.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return SimulationRunListResponse(
        items=[SimulationRunResponse.from_orm(r) for r in rows.scalars().all()],
        total=total,
        page=page,
        size=size,
    )


@router.get("/runs/{run_id}", response_model=SimulationRunResponse)
async def get_run(
    run_id: str,
    claims: ReadClaims,
    db: DbDep,
) -> SimulationRunResponse:
    """Get a single simulation run by ID."""
    run_uid = _parse_uuid(run_id, "run_id")
    org_key, run_key = str(claims.org_id), str(run_uid)

    # Cache-aside: completed runs are immutable — serve from Redis when available.
    # The key is org-scoped, so a hit can never cross tenants.
    cached = await get_cached_run(org_key, run_key)
    if cached:
        return SimulationRunResponse(**cached)

    result = await db.execute(
        select(SimulationRunORM).where(
            SimulationRunORM.id == run_uid,
            SimulationRunORM.org_id == claims.org_id,
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    response = SimulationRunResponse.from_orm(run)
    await cache_run(org_key, run_key, response.model_dump(mode="json"), run.status)
    return response
