"""Simulations API — Sprint 4.

POST /simulate/run  — run a persona simulation for a segment + stimulus
GET  /simulate/runs — list simulation runs (paginated)
GET  /simulate/runs/{run_id} — get a single run by ID
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.segment import SegmentORM
from api.models.simulation import (
    SimulateRunRequest,
    SimulationRunListResponse,
    SimulationRunORM,
    SimulationRunResponse,
)
from api.services.db import get_db
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
    """Deserialize a raw stimulus dict into the correct model.

    Uses Pydantic's discriminated union via the 'type' field.
    """
    from pydantic import TypeAdapter
    adapter: TypeAdapter[AnyStimulus] = TypeAdapter(AnyStimulus)  # type: ignore[arg-type]
    try:
        return adapter.validate_python(data)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid stimulus payload: {exc}",
        ) from exc


@router.post("/run", response_model=SimulationRunResponse, status_code=201)
async def run_simulation(body: SimulateRunRequest, db: DbDep) -> SimulationRunResponse:
    """Run a synthetic persona simulation for a segment against a marketing stimulus.

    Fetches segment metadata from PostgreSQL, calls Claude via PersonaInferenceService,
    scores the response, and persists the full result to `simulation_runs`.
    """
    try:
        segment_uid = uuid.UUID(body.segment_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid segment_id format") from exc

    seg_result = await db.execute(select(SegmentORM).where(SegmentORM.id == segment_uid))
    segment = seg_result.scalar_one_or_none()
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")

    stimulus = _parse_stimulus(body.stimulus)

    run = SimulationRunORM(
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

        run.verbatim_response      = response.verbatim_response
        run.sentiment              = response.sentiment
        run.likelihood_to_convert  = response.likelihood_to_convert
        run.conversion_score       = conversion_score
        run.llm_metadata = {
            "key_factors":    response.key_factors,
            "input_tokens":   response.input_tokens,
            "output_tokens":  response.output_tokens,
            "latency_ms":     response.latency_ms,
        }
        run.status       = "completed"
        run.completed_at = datetime.now(timezone.utc)

    except Exception as exc:
        run.status      = "failed"
        run.llm_metadata = {"error": str(exc)}
        run.completed_at = datetime.now(timezone.utc)
        await db.flush()
        logger.error("Simulation run %s failed: %s", run.id, exc)
        raise HTTPException(status_code=502, detail=f"Persona inference failed: {exc}") from exc

    await db.flush()
    await db.refresh(run)
    logger.info(
        "Simulation run %s completed: segment=%s sentiment=%s score=%.3f",
        run.id, segment.name, run.sentiment, run.conversion_score or 0.0,
    )
    return SimulationRunResponse.from_orm(run)


@router.get("/runs", response_model=SimulationRunListResponse)
async def list_runs(
    db: DbDep,
    segment_id: str | None = Query(default=None, description="Filter by segment UUID."),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> SimulationRunListResponse:
    """List simulation runs, optionally filtered by segment."""
    offset = (page - 1) * size

    base_query = select(SimulationRunORM)
    count_query = select(func.count()).select_from(SimulationRunORM)

    if segment_id is not None:
        try:
            seg_uid = uuid.UUID(segment_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid segment_id format") from exc
        base_query  = base_query.where(SimulationRunORM.segment_id == seg_uid)
        count_query = count_query.where(SimulationRunORM.segment_id == seg_uid)

    total_result = await db.execute(count_query)
    total: int = total_result.scalar_one()

    rows = await db.execute(
        base_query
        .order_by(SimulationRunORM.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    runs = rows.scalars().all()

    return SimulationRunListResponse(
        items=[SimulationRunResponse.from_orm(r) for r in runs],
        total=total,
        page=page,
        size=size,
    )


@router.get("/runs/{run_id}", response_model=SimulationRunResponse)
async def get_run(run_id: str, db: DbDep) -> SimulationRunResponse:
    """Get a single simulation run by ID."""
    try:
        run_uid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid run_id format") from exc

    result = await db.execute(select(SimulationRunORM).where(SimulationRunORM.id == run_uid))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return SimulationRunResponse.from_orm(run)
