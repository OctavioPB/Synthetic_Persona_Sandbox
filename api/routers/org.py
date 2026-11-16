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
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import CurrentUser, require
from api.auth.jwt_handler import TokenClaims
from api.auth.rbac import Permission, Role
from api.models.campaign import CampaignORM, CampaignVariantORM
from api.models.org import AuditEventORM, OrganizationORM, OrgMemberORM
from api.models.segment import SegmentORM
from api.models.simulation import SimulationRunORM
from api.services.audit import log_event
from api.services.cache import cache_org, get_cached_org, invalidate_org_runs
from api.services.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/org", tags=["org"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── Pydantic models ───────────────────────────────────────────────────────────


class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str


class MemberResponse(BaseModel):
    user_id: str
    email: str
    role: str
    joined_at: str


class MemberListResponse(BaseModel):
    items: list[MemberResponse]
    total: int


class InviteRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: Role = "marketer"


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    user_id: str
    email: str | None
    role: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    request_path: str | None
    request_method: str | None
    request_ip: str | None
    status_code: int | None
    created_at: str


class AuditLogResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", response_model=OrgResponse)
async def get_org(claims: CurrentUser, db: DbDep) -> OrgResponse:
    """Return the caller's organization profile."""
    org_id_str = str(claims.org_id)

    cached = await get_cached_org(org_id_str)
    if cached:
        return OrgResponse(**cached)

    result = await db.execute(select(OrganizationORM).where(OrganizationORM.id == claims.org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found.")

    response = OrgResponse(id=org.id, name=org.name, slug=org.slug, plan=org.plan)
    await cache_org(org_id_str, response.model_dump(mode="json"))
    return response


@router.get("/members", response_model=MemberListResponse)
async def list_members(
    claims: Annotated[TokenClaims, Depends(require(Permission.ORG_MEMBERS_READ))],
    db: DbDep,
) -> MemberListResponse:

    result = await db.execute(
        select(OrgMemberORM)
        .where(OrgMemberORM.org_id == claims.org_id)
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
    body: InviteRequest,
    claims: Annotated[TokenClaims, Depends(require(Permission.ORG_MEMBERS_MANAGE))],
    db: DbDep,
) -> dict[str, str]:
    """Register an invited member.

    In production, this would trigger an invitation email via the auth provider.
    Here it directly creates the membership record.
    """

    member = OrgMemberORM(
        org_id=claims.org_id,
        user_id=f"invited:{body.email}",
        email=body.email,
        role=body.role,
        invited_by=claims.sub,
    )
    db.add(member)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409, detail=f"{body.email} is already a member of this organization."
        ) from exc
    await log_event(
        db, claims, "org.member.invite", resource_type="org_member", resource_id=body.email
    )
    logger.info("Invited %s to org %s with role '%s'.", body.email, claims.org_id, body.role)
    return {"detail": f"Invitation sent to {body.email}."}


@router.delete("/members/{user_id}", status_code=204)
async def remove_member(
    user_id: str,
    claims: Annotated[TokenClaims, Depends(require(Permission.ORG_MEMBERS_MANAGE))],
    db: DbDep,
) -> None:

    if user_id == claims.sub:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from the organization.")

    result = await db.execute(
        select(OrgMemberORM).where(
            OrgMemberORM.org_id == claims.org_id,
            OrgMemberORM.user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Member not found.")

    await db.delete(row)
    await db.flush()
    logger.info("Removed user %s from org %s.", user_id, claims.org_id)


@router.get("/audit", response_model=AuditLogResponse)
async def get_audit_log(
    claims: Annotated[TokenClaims, Depends(require(Permission.ORG_AUDIT_READ))],
    db: DbDep,
    size: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AuditLogResponse:

    result = await db.execute(
        select(AuditEventORM)
        .where(AuditEventORM.org_id == claims.org_id)
        .order_by(AuditEventORM.created_at.desc())
        .limit(size)
        .offset(offset)
    )
    rows = result.scalars().all()
    total: int = (
        await db.execute(
            select(func.count())
            .select_from(AuditEventORM)
            .where(AuditEventORM.org_id == claims.org_id)
        )
    ).scalar_one()
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
    return AuditLogResponse(items=items, total=total)


@router.delete("/data", status_code=204)
async def delete_org_data(
    claims: Annotated[TokenClaims, Depends(require(Permission.ORG_DATA_DELETE))],
    db: DbDep,
) -> None:
    """GDPR right-to-erasure: delete ALL data for the caller's organization.

    This is irreversible.  Requires admin role.
    Purges campaign variants, campaigns, simulation runs and segments, plus the
    cached run results of the org. The organization record, its members, API
    keys and the audit trail are retained.
    """
    org_id = claims.org_id

    if not claims.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete org data.")

    # Cascade deletes — order matters due to FK constraints
    await db.execute(
        delete(CampaignVariantORM).where(
            CampaignVariantORM.campaign_id.in_(
                select(CampaignORM.id).where(CampaignORM.org_id == org_id)
            )
        )
    )
    await db.execute(delete(CampaignORM).where(CampaignORM.org_id == org_id))
    await db.execute(delete(SimulationRunORM).where(SimulationRunORM.org_id == org_id))
    await db.execute(delete(SegmentORM).where(SegmentORM.org_id == org_id))

    await db.flush()
    await invalidate_org_runs(str(org_id))
    await log_event(
        db, claims, "org.data.delete", resource_type="organization", resource_id=str(org_id)
    )
    logger.warning("GDPR deletion executed for org %s by %s.", org_id, claims.sub)
