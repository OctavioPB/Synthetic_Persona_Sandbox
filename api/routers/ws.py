"""WebSocket endpoint — streams simulation run progress to the dashboard.

Clients connect to /ws/simulations/{run_id} and receive JSON status updates
every second until the run reaches a terminal state (completed | failed).

Protocol:
  - On connect: immediate snapshot of current run state.
  - Every POLL_INTERVAL_S: updated snapshot.
  - On terminal state: final snapshot sent, connection closed gracefully.
  - On unknown run_id: {"error": "not_found"} sent, connection closed.

Authentication: browsers cannot set headers on a WebSocket handshake, so when
AUTH_REQUIRED=true the JWT is passed as a `?token=` query parameter (an
`Authorization: Bearer` header is also accepted for non-browser clients).
Runs are always scoped to the caller's organization.

Each poll uses a short-lived DB session: a long-lived one would both pin a
pooled connection for the whole stream and keep returning the first snapshot
from the ORM identity map instead of the row's current state.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select

from api.auth.dependencies import AUTH_REQUIRED
from api.auth.jwt_handler import GUEST_CLAIMS, TokenClaims, decode_token
from api.auth.rbac import Permission, has_permission
from api.models.simulation import SimulationRunORM
from api.services.db import get_async_session

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

POLL_INTERVAL_S = 1.0
_TERMINAL_STATES = {"completed", "failed"}


def _authenticate(websocket: WebSocket) -> TokenClaims | None:
    """Resolve the caller's claims, or None if the handshake must be rejected."""
    if not AUTH_REQUIRED:
        return GUEST_CLAIMS

    token = websocket.query_params.get("token")
    if not token:
        scheme, _, credentials = websocket.headers.get("authorization", "").partition(" ")
        token = credentials if scheme.lower() == "bearer" else None
    if not token:
        return None

    try:
        claims = decode_token(token)
    except InvalidTokenError as exc:
        logger.warning("WS JWT validation failed: %s", exc)
        return None
    return claims if has_permission(claims.role, Permission.SIMULATIONS_READ) else None


@router.websocket("/ws/simulations/{run_id}")
async def simulation_progress_ws(websocket: WebSocket, run_id: str) -> None:
    """Stream simulation run status updates until the run terminates."""
    claims = _authenticate(websocket)
    if claims is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    logger.info("WS connected for run %s.", run_id)

    try:
        while True:
            run = await _fetch_run(run_id, claims.org_id)
            if run is None:
                await websocket.send_json({"error": "not_found", "run_id": run_id})
                break

            await websocket.send_json(_serialize_run(run))

            if run.status in _TERMINAL_STATES:
                break

            await asyncio.sleep(POLL_INTERVAL_S)

    except WebSocketDisconnect:
        logger.info("WS client disconnected for run %s.", run_id)
    except Exception:
        logger.exception("WS error for run %s.", run_id)
        try:
            await websocket.send_json({"error": "internal_error", "run_id": run_id})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("WS closed for run %s.", run_id)


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _fetch_run(run_id: str, org_id: uuid.UUID) -> SimulationRunORM | None:
    """Fetch the org's run row; None if run_id is invalid or not found."""
    try:
        uid = uuid.UUID(run_id)
    except ValueError:
        return None

    async with get_async_session() as db:
        result = await db.execute(
            select(SimulationRunORM).where(
                SimulationRunORM.id == uid,
                SimulationRunORM.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()


def _serialize_run(run: SimulationRunORM) -> dict[str, Any]:
    metadata = run.llm_metadata or {}
    return {
        "run_id": str(run.id),
        "status": run.status,
        "segment_id": str(run.segment_id),
        "stimulus_type": run.stimulus.get("type") if run.stimulus else None,
        "sentiment": run.sentiment,
        "likelihood_to_convert": _as_float(run.likelihood_to_convert),
        "conversion_score": _as_float(run.conversion_score),
        "verbatim_response": run.verbatim_response,
        "key_factors": metadata.get("key_factors"),
        "latency_ms": metadata.get("latency_ms"),
        "error_detail": metadata.get("error"),
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


def _as_float(value: Any) -> float | None:
    """NUMERIC columns come back as Decimal, which json cannot serialize."""
    return float(value) if value is not None else None
