"""WebSocket endpoint — streams simulation run progress to the dashboard.

Clients connect to /ws/simulations/{run_id} and receive JSON status updates
every second until the run reaches a terminal state (completed | failed).

Protocol:
  - On connect: immediate snapshot of current run state.
  - Every POLL_INTERVAL_S: updated snapshot.
  - On terminal state: final snapshot sent, connection closed gracefully.
  - On unknown run_id: {"error": "not_found"} sent, connection closed.

This polling approach is intentional for Sprint 5 MVP. Sprint 6 will replace
the DB poll loop with a Redis pub/sub channel for lower latency and zero DB load.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.simulation import SimulationRunORM
from api.services.db import get_async_session

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

POLL_INTERVAL_S = 1.0
_TERMINAL_STATES = {"completed", "failed"}


@router.websocket("/ws/simulations/{run_id}")
async def simulation_progress_ws(websocket: WebSocket, run_id: str) -> None:
    """Stream simulation run status updates until the run terminates."""
    await websocket.accept()
    logger.info("WS connected for run %s.", run_id)

    try:
        async with get_async_session() as db:
            while True:
                run = await _fetch_run(db, run_id)
                if run is None:
                    await websocket.send_json({"error": "not_found", "run_id": run_id})
                    break

                payload = _serialize_run(run)
                await websocket.send_json(payload)

                if run.status in _TERMINAL_STATES:
                    break

                await asyncio.sleep(POLL_INTERVAL_S)

    except WebSocketDisconnect:
        logger.info("WS client disconnected for run %s.", run_id)
    except Exception as exc:
        logger.error("WS error for run %s: %s", run_id, exc)
        try:
            await websocket.send_json({"error": "internal_error", "detail": str(exc)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("WS closed for run %s.", run_id)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _fetch_run(db: AsyncSession, run_id: str) -> SimulationRunORM | None:
    """Fetch run row; returns None if run_id is invalid or not found."""
    import uuid
    try:
        uid = uuid.UUID(run_id)
    except ValueError:
        return None

    result = await db.execute(
        select(SimulationRunORM).where(SimulationRunORM.id == uid)
    )
    return result.scalar_one_or_none()


def _serialize_run(run: SimulationRunORM) -> dict:
    def _fmt_dt(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None

    return {
        "run_id":                 str(run.id),
        "status":                 run.status,
        "segment_id":             str(run.segment_id),
        "stimulus_type":          run.stimulus.get("type") if run.stimulus else None,
        "sentiment":              run.sentiment,
        "likelihood_to_convert":  run.likelihood_to_convert,
        "conversion_score":       run.conversion_score,
        "verbatim_response":      run.verbatim_response,
        "key_factors":            (run.llm_metadata or {}).get("key_factors"),
        "latency_ms":             (run.llm_metadata or {}).get("latency_ms"),
        "created_at":             _fmt_dt(run.created_at),
        "completed_at":           _fmt_dt(run.completed_at),
    }
