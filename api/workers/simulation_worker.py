"""ARQ simulation worker — processes queued simulation jobs.

Each job runs PersonaInferenceService + ConversionScorer and writes the result
back to simulation_runs in PostgreSQL.

Run the worker:
    uv run python -m arq api.workers.simulation_worker.WorkerSettings

Concurrency (S6-01): up to SIMULATION_MAX_CONCURRENT jobs (default 5) run at
once. Inference is a blocking HTTP call, so each job runs it in a worker
thread — calling it directly would block the event loop and serialize every
job regardless of max_jobs.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import update

from api.models.simulation import SimulationRunORM
from api.services.db import get_async_session
from api.services.metrics import SIMULATION_ERRORS, SIMULATION_LATENCY
from api.services.queue import ARQ_REDIS_SETTINGS
from ml.synthetic_data.conversion_scorer import ConversionScorer
from ml.synthetic_data.persona_inference import PersonaInferenceService
from ml.synthetic_data.stimulus_schema import (
    AdCopyStimulus,
    AnyStimulus,
    PriceChangeStimulus,
    PromoStimulus,
)

logger = logging.getLogger(__name__)

_stimulus_adapter: TypeAdapter[AdCopyStimulus | PriceChangeStimulus | PromoStimulus] = TypeAdapter(
    AnyStimulus
)
_scorer = ConversionScorer()


@lru_cache(maxsize=1)
def _inference_service() -> PersonaInferenceService:
    """One inference service (and HTTP connection pool) per worker process."""
    return PersonaInferenceService()


async def run_simulation_job(
    ctx: dict[str, Any],
    *,
    run_id: str,
    segment_id: str,
    segment_name: str,
    definition: dict[str, Any],
    stimulus: dict[str, Any],
    temperature: float = 0.7,
    model: str | None = None,
) -> dict[str, Any]:
    """ARQ job: run persona inference and persist the result.

    Args:
        ctx:           ARQ context dict (contains job metadata).
        run_id:        UUID of the simulation run (pre-created in DB as 'pending').
        segment_id:    UUID of the target segment.
        segment_name:  Human-readable segment name.
        definition:    SegmentDefinition dict.
        stimulus:      Stimulus payload dict (type-discriminated).
        temperature:   LLM sampling temperature.
        model:         Optional model override.

    Returns:
        Dict with run_id and conversion_score for ARQ result storage.
    """
    t0 = time.monotonic()
    await _update_run(run_id, status="running")

    try:
        response = await asyncio.to_thread(
            _inference_service().generate,
            segment_id=segment_id,
            segment_name=segment_name,
            definition=definition,
            stimulus=_stimulus_adapter.validate_python(stimulus),
            temperature=temperature,
            model=model,
        )
        conversion_score = _scorer.score(response)

        await _update_run(
            run_id,
            verbatim_response=response.verbatim_response,
            sentiment=response.sentiment,
            likelihood_to_convert=response.likelihood_to_convert,
            conversion_score=conversion_score,
            llm_metadata={
                "key_factors": response.key_factors,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
            },
            status="completed",
            completed_at=datetime.now(UTC),
        )
    except asyncio.CancelledError:
        # ARQ cancels the task when job_timeout elapses. CancelledError is not an
        # Exception, so without this branch the run would stay 'running' forever.
        SIMULATION_ERRORS.labels(error_type="WORKER_TIMEOUT").inc()
        await asyncio.shield(_mark_failed(run_id, "WORKER_TIMEOUT"))
        logger.error("Job %s cancelled (timeout or shutdown).", run_id)
        raise
    except Exception as exc:
        SIMULATION_ERRORS.labels(error_type=type(exc).__name__).inc()
        await _mark_failed(run_id, str(exc))
        logger.error("Job %s failed: %s", run_id, exc)
        raise

    elapsed = time.monotonic() - t0
    SIMULATION_LATENCY.observe(elapsed)
    logger.info(
        "Job %s completed: score=%.4f sentiment=%s elapsed=%.2fs",
        run_id,
        conversion_score,
        response.sentiment,
        elapsed,
    )
    return {"run_id": run_id, "conversion_score": conversion_score}


async def _update_run(run_id: str, **values: Any) -> None:
    async with get_async_session() as db:
        await db.execute(
            update(SimulationRunORM)
            .where(SimulationRunORM.id == uuid.UUID(run_id))
            .values(**values)
        )
        await db.commit()


async def _mark_failed(run_id: str, error: str) -> None:
    """Record a failure; never raises so the original error is what propagates."""
    try:
        await _update_run(
            run_id,
            status="failed",
            llm_metadata={"error": error},
            completed_at=datetime.now(UTC),
        )
    except Exception as exc:
        logger.error("Could not mark run %s as failed: %s", run_id, exc)


# ── Startup / shutdown hooks ───────────────────────────────────────────────────


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("Simulation worker starting up.")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("Simulation worker shutting down.")


# ── ARQ WorkerSettings ─────────────────────────────────────────────────────────


class WorkerSettings:
    """ARQ worker configuration.

    max_jobs: concurrent simulation jobs (S6-01), from SIMULATION_MAX_CONCURRENT.
    job_timeout=120s: Claude inference should complete well within 2 minutes.
    keep_result=3600: retain job results for 1 hour for debugging.
    """

    functions = [run_simulation_job]
    redis_settings = ARQ_REDIS_SETTINGS
    max_jobs = int(os.getenv("SIMULATION_MAX_CONCURRENT", "5"))
    job_timeout = 120
    keep_result = 3600
    on_startup = startup
    on_shutdown = shutdown
