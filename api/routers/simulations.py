"""Simulations API — Sprint 4 (inline) → Sprint 6 (ARQ-queued) → S9-02 (auth).

POST /simulate/run        — enqueue async simulation job (202 Accepted)
POST /simulate/run/sync   — inline synchronous run (for testing / CI)
GET  /simulate/runs       — list simulation runs (paginated, with filters)
GET  /simulate/runs/{id}  — get a single run by ID
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import CurrentUser, require
from api.auth.rbac import Permission
from api.models.segment import SegmentORM
from api.models.simulation import (
    SimulateRunRequest,
    SimulationRunListResponse,
    SimulationRunORM,
    SimulationRunResponse,
)
from api.services.db import get_db
from api.services.metrics import QUEUE_DEPTH, SIMULATION_TOTAL
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

_inference_service = PersonaInferenceService()
_scorer            = ConversionScorer()


def _parse_stimulus(
    data: dict[str, Any],
) -> AdCopyStimulus | PriceChangeStimulus | PromoStimulus:
    """Deserialize a raw stimulus dict via the discriminated union."""
    from pydantic import TypeAdapter
    adapter: TypeAdapter[AnyStimulus] = TypeAdapter(AnyStimulus)  # type: ignore[arg-type]
    try:
        return adapter.validate_python(data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid stimulus payload: {exc}") from exc


# ── Async (queued) endpoint — primary path ─────────────────────────────────────

@router.post("/run", response_model=SimulationRunResponse, status_code=202)
async def run_simulation_async(
    body:   SimulateRunRequest,
    claims: Annotated[object, Depends(require(Permission.SIMULATIONS_RUN))],
    db:     DbDep,
    queue:  QueueDep,
    _:      RateLimitDep,
) -> SimulationRunResponse:
    """Enqueue a simulation job.

    Returns 202 Accepted with status='pending'. Poll via GET /simulate/runs/{id}
    or stream progress via WebSocket /ws/simulations/{id}.
    """
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    try:
        segment_uid = uuid.UUID(body.segment_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid segment_id format") from exc

    seg_result = await db.execute(
        select(SegmentORM).where(
            SegmentORM.id == segment_uid,
            SegmentORM.org_id == claims_typed.org_id,
        )
    )
    segment = seg_result.scalar_one_or_none()
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")

    stimulus = _parse_stimulus(body.stimulus)

    run = SimulationRunORM(
        org_id=claims_typed.org_id,
        segment_id=segment_uid,
        stimulus=stimulus.model_dump(mode="json"),
        status="pending",
        model_id=body.model,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    await queue.enqueue_job(
        "run_simulation_job",
        run_id=str(run.id),
        segment_id=str(segment_uid),
        segment_name=segment.name,
        definition=segment.definition,
        stimulus=stimulus.model_dump(mode="json"),
        temperature=body.temperature,
        model=body.model,
        _job_id=str(run.id),
    )

    QUEUE_DEPTH.inc()
    SIMULATION_TOTAL.labels(stimulus_type=stimulus.type).inc()

    logger.info(
        "Enqueued simulation run %s for segment '%s' (stimulus=%s).",
        run.id, segment.name, stimulus.type,
    )
    return SimulationRunResponse.from_orm(run)


# ── Sync endpoint — used by integration tests and the Airflow DAG ─────────────

@router.post("/run/sync", response_model=SimulationRunResponse, status_code=201)
async def run_simulation_sync(
    body:   SimulateRunRequest,
    claims: Annotated[object, Depends(require(Permission.SIMULATIONS_RUN))],
    db:     DbDep,
) -> SimulationRunResponse:
    """Run a simulation synchronously (blocking).

    Intended for CI, integration tests, and the Airflow DAG.
    """
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    try:
        segment_uid = uuid.UUID(body.segment_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid segment_id format") from exc

    seg_result = await db.execute(
        select(SegmentORM).where(
            SegmentORM.id == segment_uid,
            SegmentORM.org_id == claims_typed.org_id,
        )
    )
    segment = seg_result.scalar_one_or_none()
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")

    stimulus = _parse_stimulus(body.stimulus)

    run = SimulationRunORM(
        org_id=claims_typed.org_id,
        segment_id=segment_uid,
        stimulus=stimulus.model_dump(mode="json"),
        status="running",
        model_id=body.model,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    try:
        response = _inference_service.generate(
            segment_id=str(segment_uid),
            segment_name=segment.name,
            definition=segment.definition,
            stimulus=stimulus,
            model=body.model,
            temperature=body.temperature,
        )
        conversion_score = _scorer.score(response)

        run.verbatim_response     = response.verbatim_response
        run.sentiment             = response.sentiment
        run.likelihood_to_convert = response.likelihood_to_convert
        run.conversion_score      = conversion_score
        run.llm_metadata = {
            "key_factors":   response.key_factors,
            "input_tokens":  response.input_tokens,
            "output_tokens": response.output_tokens,
            "latency_ms":    response.latency_ms,
        }
        run.status       = "completed"
        run.completed_at = datetime.now(timezone.utc)

    except Exception as exc:
        run.status       = "failed"
        run.llm_metadata = {"error": str(exc)}
        run.completed_at = datetime.now(timezone.utc)
        await db.flush()
        logger.error("Sync simulation run %s failed: %s", run.id, exc)
        raise HTTPException(status_code=502, detail=f"Persona inference failed: {exc}") from exc

    await db.flush()
    await db.refresh(run)
    logger.info(
        "Sync run %s completed: segment=%s score=%.3f",
        run.id, segment.name, run.conversion_score or 0.0,
    )
    return SimulationRunResponse.from_orm(run)


# ── Read endpoints ─────────────────────────────────────────────────────────────

@router.get("/runs", response_model=SimulationRunListResponse)
async def list_runs(
    claims:     Annotated[object, Depends(require(Permission.SIMULATIONS_READ))],
    db:         DbDep,
    segment_id: str | None = Query(default=None),
    status:     str | None = Query(default=None, description="Filter by status."),
    page:       int = Query(default=1, ge=1),
    size:       int = Query(default=20, ge=1, le=100),
) -> SimulationRunListResponse:
    """List simulation runs with optional filters."""
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    offset      = (page - 1) * size
    base_query  = select(SimulationRunORM).where(SimulationRunORM.org_id == claims_typed.org_id)
    count_query = select(func.count()).select_from(SimulationRunORM).where(
        SimulationRunORM.org_id == claims_typed.org_id
    )

    if segment_id is not None:
        try:
            seg_uid = uuid.UUID(segment_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid segment_id format") from exc
        base_query  = base_query.where(SimulationRunORM.segment_id == seg_uid)
        count_query = count_query.where(SimulationRunORM.segment_id == seg_uid)

    if status is not None:
        base_query  = base_query.where(SimulationRunORM.status == status)
        count_query = count_query.where(SimulationRunORM.status == status)

    total: int = (await db.execute(count_query)).scalar_one()
    rows = await db.execute(
        base_query.order_by(SimulationRunORM.created_at.desc()).offset(offset).limit(size)
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
    claims: Annotated[object, Depends(require(Permission.SIMULATIONS_READ))],
    db:     DbDep,
) -> SimulationRunResponse:
    """Get a single simulation run by ID."""
    from api.auth.jwt_handler import TokenClaims
    from api.services.cache import cache_run, get_cached_run
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    try:
        run_uid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid run_id format") from exc

    # Cache-aside: completed runs are immutable — serve from Redis when available
    cached = await get_cached_run(run_id)
    if cached and cached.get("org_id") == str(claims_typed.org_id):
        return SimulationRunResponse(**cached)

    result = await db.execute(
        select(SimulationRunORM).where(
            SimulationRunORM.id == run_uid,
            SimulationRunORM.org_id == claims_typed.org_id,
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    response = SimulationRunResponse.from_orm(run)
    await cache_run(run_id, response.model_dump(mode="json"), run.status)
    return response
