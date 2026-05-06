"""Audit log service — S9-06.

Records who triggered which action and when.  Writes are fire-and-forget;
failures are logged but never propagate to the caller.

Usage:
    from api.services.audit import log_event

    await log_event(
        db=db,
        claims=claims,
        action="simulation.run",
        resource_type="simulation_run",
        resource_id=str(run.id),
        request=request,
        status_code=202,
    )
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from fastapi import Request

    from api.auth.jwt_handler import TokenClaims

logger = logging.getLogger(__name__)


async def log_event(
    db:            AsyncSession,
    claims:        "TokenClaims",
    action:        str,
    resource_type: str | None = None,
    resource_id:   str | None = None,
    request:       "Request | None" = None,
    status_code:   int | None = None,
) -> None:
    """Insert an audit event.  Silently swallows all errors."""
    from api.models.org import AuditEventORM

    try:
        event = AuditEventORM(
            org_id=claims.org_id,
            user_id=claims.sub,
            email=claims.email,
            role=claims.role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_path=str(request.url.path) if request else None,
            request_method=request.method if request else None,
            request_ip=_get_client_ip(request),
            user_agent=request.headers.get("user-agent") if request else None,
            status_code=status_code,
        )
        db.add(event)
        await db.flush()
    except Exception as exc:
        logger.warning("Audit log write failed (non-fatal): %s", exc)


def _get_client_ip(request: "Request | None") -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
