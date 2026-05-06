"""ARQ simulation worker — processes queued simulation jobs.

Each job runs PersonaInferenceService + ConversionScorer and writes the result
back to simulation_runs in PostgreSQL.

Run the worker:
    uv run python -m arq api.workers.simulation_worker.WorkerSettings

WorkerSettings.max_jobs = 5 satisfies the S6-01 concurrency requirement:
up to 5 simultaneous simulation jobs without degradation.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2
from arq.connections import RedisSettings

from api.services.metrics import (
    SIMULATION_ERRORS,
    SIMULATION_LATENCY,
    QUEUE_DEPTH,
)

logger = logging.getLogger(__name__)

ARQ_REDIS_SETTINGS = RedisSettings(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    database=int(os.getenv("REDIS_DB", "0")),
    password=os.getenv("REDIS_PASSWORD") or None,
)


def _pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "synthetic_persona"),
        user=os.getenv("POSTGRES_USER", "spb_user"),
        password=os.getenv("POSTGRES_PASSWORD", "changeme"),
    )


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
    import time

    t0 = time.monotonic()
    QUEUE_DEPTH.dec()

    _set_run_status(run_id, "running")

    try:
        from ml.synthetic_data.conversion_scorer import ConversionScorer
        from ml.synthetic_data.persona_inference import PersonaInferenceService
        from ml.synthetic_data.stimulus_schema import AnyStimulus
        from pydantic import TypeAdapter

        adapter: TypeAdapter[AnyStimulus] = TypeAdapter(AnyStimulus)  # type: ignore[arg-type]
        typed_stimulus = adapter.validate_python(stimulus)

        response = PersonaInferenceService().generate(
            segment_id=segment_id,
            segment_name=segment_name,
            definition=definition,
            stimulus=typed_stimulus,
            temperature=temperature,
            model=model,
        )
        conversion_score = ConversionScorer().score(response)
        now = datetime.now(timezone.utc).isoformat()

        conn = _pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE simulation_runs SET
                        verbatim_response     = %s,
                        sentiment             = %s,
                        likelihood_to_convert = %s,
                        conversion_score      = %s,
                        llm_metadata          = %s::jsonb,
                        status                = 'completed',
                        completed_at          = %s
                    WHERE id = %s
                    """,
                    (
                        response.verbatim_response,
                        response.sentiment,
                        response.likelihood_to_convert,
                        conversion_score,
                        json.dumps({
                            "key_factors":   response.key_factors,
                            "input_tokens":  response.input_tokens,
                            "output_tokens": response.output_tokens,
                            "latency_ms":    response.latency_ms,
                        }),
                        now,
                        run_id,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

        elapsed = time.monotonic() - t0
        SIMULATION_LATENCY.observe(elapsed)
        logger.info(
            "Job %s completed: score=%.4f sentiment=%s elapsed=%.2fs",
            run_id, conversion_score, response.sentiment, elapsed,
        )
        return {"run_id": run_id, "conversion_score": conversion_score}

    except Exception as exc:
        SIMULATION_ERRORS.labels(error_type=type(exc).__name__).inc()
        _set_run_status(run_id, "failed", error=str(exc))
        logger.error("Job %s failed: %s", run_id, exc)
        raise


def _set_run_status(run_id: str, status: str, error: str | None = None) -> None:
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            if error:
                cur.execute(
                    "UPDATE simulation_runs SET status = %s, llm_metadata = jsonb_set(COALESCE(llm_metadata,'{}'), '{error}', %s) WHERE id = %s",
                    (status, json.dumps(error), run_id),
                )
            else:
                cur.execute(
                    "UPDATE simulation_runs SET status = %s WHERE id = %s",
                    (status, run_id),
                )
        conn.commit()
    finally:
        conn.close()


# ── Startup / shutdown hooks ───────────────────────────────────────────────────

async def startup(ctx: dict[str, Any]) -> None:
    logger.info("Simulation worker starting up.")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("Simulation worker shutting down.")


# ── ARQ WorkerSettings ─────────────────────────────────────────────────────────

class WorkerSettings:
    """ARQ worker configuration.

    max_jobs=5 satisfies S6-01: up to 5 concurrent simulation jobs.
    job_timeout=120s: Claude inference should complete well within 2 minutes.
    keep_result=3600: retain job results for 1 hour for debugging.
    """

    functions     = [run_simulation_job]
    redis_settings = ARQ_REDIS_SETTINGS
    max_jobs      = 5
    job_timeout   = 120
    keep_result   = 3600
    on_startup    = startup
    on_shutdown   = shutdown
