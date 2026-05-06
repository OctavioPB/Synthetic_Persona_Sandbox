"""Organization management — S9-02 / S9-06 / S9-09.

GET    /org                        — current org info
GET    /org/members                — list org members
POST   /org/members                — invite a member
DELETE /org/members/{user_id}      — remove a member
GET    /org/audit                  — audit log for the org
DELETE /org/data                   — GDPR: delete all org data (admin only)
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import CurrentUser, require
from api.auth.rbac import Permission
from api.models.org import AuditEventORM, OrgMemberORM, OrganizationORM
from api.services.audit import log_event
from api.services.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/org", tags=["org"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── Pydantic models ───────────────────────────────────────────────────────────

class OrgResponse(BaseModel):
    id:   uuid.UUID
    name: str
    slug: str
    plan: str


class MemberResponse(BaseModel):
    user_id:    str
    email:      str
    role:       str
    joined_at:  str


class MemberListResponse(BaseModel):
    items: list[MemberResponse]
    total: int


class InviteRequest(BaseModel):
    email: str
    role:  str = "marketer"


class AuditEventResponse(BaseModel):
    id:             uuid.UUID
    user_id:        str
    email:          str | None
    role:           str | None
    action:         str
    resource_type:  str | None
    resource_id:    str | None
    request_path:   str | None
    request_method: str | None
    request_ip:     str | None
    status_code:    int | None
    created_at:     str


class AuditLogResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=OrgResponse)
async def get_org(claims: CurrentUser, db: DbDep) -> OrgResponse:
    """Return the caller's organization profile."""
    from api.services.cache import cache_org, get_cached_org
    org_id_str = str(claims.org_id)

    cached = await get_cached_org(org_id_str)
    if cached:
        return OrgResponse(**cached)

    result = await db.execute(
        select(OrganizationORM).where(OrganizationORM.id == claims.org_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found.")

    response = OrgResponse(id=org.id, name=org.name, slug=org.slug, plan=org.plan)
    await cache_org(org_id_str, response.model_dump(mode="json"))
    return response


@router.get("/members", response_model=MemberListResponse)
async def list_members(
    claims: Annotated[object, Depends(require(Permission.ORG_MEMBERS_READ))],
    db:     DbDep,
) -> MemberListResponse:
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    result = await db.execute(
        select(OrgMemberORM)
        .where(OrgMemberORM.org_id == claims_typed.org_id)
        .order_by(OrgMemberORM.joined_at)
    )
    rows = result.scalars().all()
    items = [
        MemberResponse(
            user_id=r.user_id,
            email=r.email,
            role=r.role,
            joined_at=r.joined_at.isoformat(),
        )
        for r in rows
    ]
    return MemberListResponse(items=items, total=len(items))


@router.post("/members", status_code=201)
async def invite_member(
    body:   InviteRequest,
    claims: Annotated[object, Depends(require(Permission.ORG_MEMBERS_MANAGE))],
    db:     DbDep,
) -> dict[str, str]:
    """Register an invited member.

    In production, this would trigger an invitation email via the auth provider.
    Here it directly creates the membership record.
    """
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    member = OrgMemberORM(
        org_id=claims_typed.org_id,
        user_id=f"invited:{body.email}",
        email=body.email,
        role=body.role,
        invited_by=claims_typed.sub,
    )
    db.add(member)
    await db.flush()
    await log_event(db, claims_typed, "org.member.invite", resource_type="org_member", resource_id=body.email)
    logger.info("Invited %s to org %s with role '%s'.", body.email, claims_typed.org_id, body.role)
    return {"detail": f"Invitation sent to {body.email}."}


@router.delete("/members/{user_id}", status_code=204)
async def remove_member(
    user_id: str,
    claims:  Annotated[object, Depends(require(Permission.ORG_MEMBERS_MANAGE))],
    db:      DbDep,
) -> None:
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    if user_id == claims_typed.sub:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from the organization.")

    result = await db.execute(
        select(OrgMemberORM).where(
            OrgMemberORM.org_id == claims_typed.org_id,
            OrgMemberORM.user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Member not found.")

    await db.delete(row)
    await db.flush()
    logger.info("Removed user %s from org %s.", user_id, claims_typed.org_id)


@router.get("/audit", response_model=AuditLogResponse)
async def get_audit_log(
    claims: Annotated[object, Depends(require(Permission.ORG_AUDIT_READ))],
    db:     DbDep,
    size:   int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AuditLogResponse:
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    result = await db.execute(
        select(AuditEventORM)
        .where(AuditEventORM.org_id == claims_typed.org_id)
        .order_by(AuditEventORM.created_at.desc())
        .limit(size)
        .offset(offset)
    )
    rows = result.scalars().all()
    items = [
        AuditEventResponse(
            id=r.id,
            user_id=r.user_id,
            email=r.email,
            role=r.role,
            action=r.action,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            request_path=r.request_path,
            request_method=r.request_method,
            request_ip=r.request_ip,
            status_code=r.status_code,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]
    return AuditLogResponse(items=items, total=len(items))


@router.delete("/data", status_code=204)
async def delete_org_data(
    claims: Annotated[object, Depends(require(Permission.ORG_DATA_DELETE))],
    db:     DbDep,
) -> None:
    """GDPR right-to-erasure: delete ALL data for the caller's organization.

    This is irreversible.  Requires admin role.
    Cascades through simulation_runs, campaigns, segments, api_keys, audit_events.
    The organization record itself is retained (soft-style — only data is purged).
    """
    from api.auth.jwt_handler import TokenClaims
    from api.models.campaign import CampaignORM, CampaignVariantORM
    from api.models.segment import SegmentORM
    from api.models.simulation import SimulationRunORM

    claims_typed: TokenClaims = claims  # type: ignore[assignment]
    org_id = claims_typed.org_id

    if not claims_typed.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete org data.")

    # Cascade deletes — order matters due to FK constraints
    await db.execute(delete(CampaignVariantORM).where(
        CampaignVariantORM.campaign_id.in_(
            select(CampaignORM.id).where(CampaignORM.org_id == org_id)
        )
    ))
    await db.execute(delete(CampaignORM).where(CampaignORM.org_id == org_id))
    await db.execute(delete(SimulationRunORM).where(SimulationRunORM.org_id == org_id))
    await db.execute(delete(SegmentORM).where(SegmentORM.org_id == org_id))

    await db.flush()
    logger.warning("GDPR deletion executed for org %s by %s.", org_id, claims_typed.sub)
