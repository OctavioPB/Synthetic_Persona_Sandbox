"""Auth endpoints — S9-01 / S9-04.

POST /auth/dev-token   — issue a dev JWT (only when AUTH_MODE=dev)
POST /auth/keys        — create an API key for the current org
GET  /auth/keys        — list active API keys for the current org
DELETE /auth/keys/{id} — revoke an API key
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import CurrentUser, require
from api.auth.jwt_handler import DEFAULT_ORG_ID, encode_token
from api.auth.rbac import Permission
from api.models.org import ApiKeyORM
from api.services.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_AUTH_MODE = os.getenv("AUTH_MODE", "dev").lower()

DbDep = Annotated[AsyncSession, Depends(get_db)]

# ── Pydantic models ───────────────────────────────────────────────────────────

class DevTokenRequest(BaseModel):
    email:  str = "dev@localhost"
    org_id: uuid.UUID = DEFAULT_ORG_ID
    role:   str = "admin"


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int


class ApiKeyCreate(BaseModel):
    name:        str
    role:        str = "marketer"
    expires_days: int | None = Field(None, ge=1, le=365)


class ApiKeyResponse(BaseModel):
    id:         uuid.UUID
    name:       str
    key_prefix: str
    role:       str
    expires_at: datetime | None
    created_at: datetime
    is_active:  bool
    raw_key:    str | None = None   # only set on creation, never again


class ApiKeyListResponse(BaseModel):
    items: list[ApiKeyResponse]
    total: int


# ── Dev token endpoint ────────────────────────────────────────────────────────

@router.post("/dev-token", response_model=TokenResponse)
async def issue_dev_token(body: DevTokenRequest) -> TokenResponse:
    """Issue a short-lived JWT for development use.

    Disabled in production (AUTH_MODE != 'dev').
    """
    if _AUTH_MODE != "dev":
        raise HTTPException(status_code=404, detail="Not found.")

    token = encode_token(
        sub=f"dev-{body.email}",
        email=body.email,
        org_id=body.org_id,
        role=body.role,
    )
    return TokenResponse(access_token=token, expires_in=3600)


# ── API key management ────────────────────────────────────────────────────────

@router.post("/keys", response_model=ApiKeyResponse, status_code=201)
async def create_api_key(
    body:   ApiKeyCreate,
    claims: Annotated[object, Depends(require(Permission.ORG_KEYS_MANAGE))],
    db:     DbDep,
) -> ApiKeyResponse:
    """Create an API key for the caller's organization."""
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    raw_key    = f"spb_{secrets.token_urlsafe(32)}"
    key_prefix = raw_key[:12]
    key_hash   = hashlib.sha256(raw_key.encode()).hexdigest()

    expires_at = None
    if body.expires_days:
        expires_at = datetime.now(tz=timezone.utc) + timedelta(days=body.expires_days)

    key_row = ApiKeyORM(
        org_id=claims_typed.org_id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        role=body.role,
        expires_at=expires_at,
        created_by=claims_typed.sub,
    )
    db.add(key_row)
    await db.flush()
    await db.refresh(key_row)

    logger.info("API key '%s' created for org %s.", body.name, claims_typed.org_id)
    return ApiKeyResponse(
        id=key_row.id,
        name=key_row.name,
        key_prefix=key_row.key_prefix,
        role=key_row.role,
        expires_at=key_row.expires_at,
        created_at=key_row.created_at,
        is_active=key_row.is_active,
        raw_key=raw_key,  # returned once on creation
    )


@router.get("/keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    claims: Annotated[object, Depends(require(Permission.ORG_KEYS_READ))],
    db:     DbDep,
) -> ApiKeyListResponse:
    """List active API keys for the caller's organization."""
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    result = await db.execute(
        select(ApiKeyORM)
        .where(ApiKeyORM.org_id == claims_typed.org_id, ApiKeyORM.is_active.is_(True))
        .order_by(ApiKeyORM.created_at.desc())
    )
    rows = result.scalars().all()
    items = [
        ApiKeyResponse(
            id=r.id,
            name=r.name,
            key_prefix=r.key_prefix,
            role=r.role,
            expires_at=r.expires_at,
            created_at=r.created_at,
            is_active=r.is_active,
        )
        for r in rows
    ]
    return ApiKeyListResponse(items=items, total=len(items))


@router.delete("/keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: uuid.UUID,
    claims: Annotated[object, Depends(require(Permission.ORG_KEYS_MANAGE))],
    db:     DbDep,
) -> None:
    """Revoke (deactivate) an API key."""
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    result = await db.execute(
        select(ApiKeyORM).where(
            ApiKeyORM.id == key_id,
            ApiKeyORM.org_id == claims_typed.org_id,
        )
    )
    key_row = result.scalar_one_or_none()
    if key_row is None:
        raise HTTPException(status_code=404, detail="API key not found.")

    key_row.is_active = False
    await db.flush()
    logger.info("API key %s revoked.", key_id)
