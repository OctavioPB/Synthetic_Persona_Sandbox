"""FastAPI auth dependencies — S9-01 / S9-02 / S9-04.

Usage:
    # Require authentication (fail 401 when AUTH_REQUIRED=true and no token)
    CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]

    # Require a specific permission
    @router.post("/simulate/run")
    async def run(claims: Annotated[TokenClaims, Depends(require(Permission.SIMULATIONS_RUN))]):
        ...

Environment variables:
    AUTH_REQUIRED   false (default) — skip auth entirely; true — enforce JWT/API key
"""

from __future__ import annotations

import hashlib
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.jwt_handler import GUEST_CLAIMS, TokenClaims, decode_token
from api.auth.rbac import Permission, has_permission
from api.services.db import get_db

logger = logging.getLogger(__name__)

AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "false").lower() == "true"

_bearer_scheme = HTTPBearer(auto_error=False)


# ── Core authentication dependency ────────────────────────────────────────────


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,  # type: ignore[assignment]
) -> TokenClaims:
    """Resolve the caller's identity from a Bearer JWT or X-API-Key header.

    When AUTH_REQUIRED is false (dev default) returns GUEST_CLAIMS so that
    all existing tests and routes continue to work without modification.
    """
    if not AUTH_REQUIRED:
        return GUEST_CLAIMS

    # ── Try Bearer JWT ────────────────────────────────────────────────────────
    if credentials and credentials.credentials:
        try:
            claims = decode_token(credentials.credentials)
            request.state.claims = claims
            return claims
        except InvalidTokenError as exc:
            logger.warning("JWT validation failed: %s", exc)
            raise HTTPException(status_code=401, detail="Invalid or expired token.") from exc

    # ── Try X-API-Key header ──────────────────────────────────────────────────
    if x_api_key:
        key_claims = await _validate_api_key(x_api_key, db)
        if key_claims:
            request.state.claims = key_claims
            return key_claims
        raise HTTPException(status_code=401, detail="Invalid or inactive API key.")

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide a Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _validate_api_key(raw_key: str, db: AsyncSession) -> TokenClaims | None:
    """Look up an API key by its SHA-256 hash, return TokenClaims if valid."""
    from api.models.org import ApiKeyORM

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    result = await db.execute(
        select(ApiKeyORM).where(
            ApiKeyORM.key_hash == key_hash,
            ApiKeyORM.is_active.is_(True),
        )
    )
    key_row = result.scalar_one_or_none()
    if key_row is None:
        return None

    now = datetime.now(tz=UTC)
    if key_row.expires_at and key_row.expires_at < now:
        return None

    # Best-effort usage stamp; persisted when the request's session commits.
    key_row.last_used_at = now

    return TokenClaims(
        sub=f"apikey:{key_row.id}",
        email=f"apikey:{key_row.key_prefix}",
        org_id=key_row.org_id,
        role=key_row.role,
    )


# ── Permission guard factory ──────────────────────────────────────────────────


def require(permission: Permission) -> Callable[..., Awaitable[TokenClaims]]:
    """Return a FastAPI dependency that enforces `permission` on the caller."""

    async def _check(
        claims: Annotated[TokenClaims, Depends(get_current_user)],
    ) -> TokenClaims:
        if not has_permission(claims.role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{claims.role}' lacks permission '{permission}'.",
            )
        return claims

    return _check


# ── Convenience type aliases ──────────────────────────────────────────────────

CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]
