"""Campaigns + Variants CRUD API — Sprint 5 / S9-02.

POST   /campaigns                   — create campaign
GET    /campaigns                   — list campaigns (paginated)
GET    /campaigns/{id}              — get campaign
PUT    /campaigns/{id}              — update campaign
DELETE /campaigns/{id}              — delete campaign

POST   /campaigns/{id}/variants     — add a variant to a campaign
GET    /campaigns/{id}/variants     — list variants for a campaign
DELETE /campaigns/{id}/variants/{vid} — remove a variant
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import require
from api.auth.rbac import Permission
from api.models.campaign import (
    CampaignCreate,
    CampaignListResponse,
    CampaignORM,
    CampaignResponse,
    CampaignUpdate,
    CampaignVariantORM,
    VariantCreate,
    VariantResponse,
)
from api.services.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/campaigns", tags=["campaigns"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── Campaign CRUD ──────────────────────────────────────────────────────────────

@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    body:   CampaignCreate,
    claims: Annotated[object, Depends(require(Permission.CAMPAIGNS_WRITE))],
    db:     DbDep,
) -> CampaignResponse:
    """Create a new campaign."""
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    segment_uid: uuid.UUID | None = None
    if body.segment_id:
        try:
            segment_uid = uuid.UUID(body.segment_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid segment_id format") from exc

    campaign = CampaignORM(
        org_id=claims_typed.org_id,
        segment_id=segment_uid,
        name=body.name,
        description=body.description,
    )
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    logger.info("Created campaign '%s' (id=%s).", campaign.name, campaign.id)
    return CampaignResponse.from_orm(campaign)


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    claims: Annotated[object, Depends(require(Permission.CAMPAIGNS_READ))],
    db:     DbDep,
    page:   int = Query(default=1, ge=1),
    size:   int = Query(default=20, ge=1, le=100),
) -> CampaignListResponse:
    """List campaigns for the current org, paginated."""
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    offset = (page - 1) * size

    total = (await db.execute(
        select(func.count()).select_from(CampaignORM).where(CampaignORM.org_id == claims_typed.org_id)
    )).scalar_one()

    rows = await db.execute(
        select(CampaignORM)
        .where(CampaignORM.org_id == claims_typed.org_id)
        .order_by(CampaignORM.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    campaigns = rows.scalars().all()

    return CampaignListResponse(
        items=[CampaignResponse.from_orm(c) for c in campaigns],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    claims:      Annotated[object, Depends(require(Permission.CAMPAIGNS_READ))],
    db:          DbDep,
) -> CampaignResponse:
    """Get a single campaign by ID."""
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    campaign = await _get_or_404(campaign_id, claims_typed.org_id, db)
    return CampaignResponse.from_orm(campaign)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    body:        CampaignUpdate,
    claims:      Annotated[object, Depends(require(Permission.CAMPAIGNS_WRITE))],
    db:          DbDep,
) -> CampaignResponse:
    """Update a campaign's metadata or status."""
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    campaign = await _get_or_404(campaign_id, claims_typed.org_id, db)

    if body.name is not None:
        campaign.name = body.name
    if body.description is not None:
        campaign.description = body.description
    if body.status is not None:
        campaign.status = body.status
    if body.segment_id is not None:
        try:
            campaign.segment_id = uuid.UUID(body.segment_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid segment_id format") from exc

    await db.flush()
    await db.refresh(campaign)
    return CampaignResponse.from_orm(campaign)


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: str,
    claims:      Annotated[object, Depends(require(Permission.CAMPAIGNS_WRITE))],
    db:          DbDep,
) -> None:
    """Delete a campaign and all its variants (CASCADE)."""
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    campaign = await _get_or_404(campaign_id, claims_typed.org_id, db)
    await db.delete(campaign)
    logger.info("Deleted campaign '%s'.", campaign_id)


# ── Variant sub-resource ───────────────────────────────────────────────────────

@router.post("/{campaign_id}/variants", response_model=VariantResponse, status_code=201)
async def add_variant(
    campaign_id: str,
    body:        VariantCreate,
    claims:      Annotated[object, Depends(require(Permission.CAMPAIGNS_WRITE))],
    db:          DbDep,
) -> VariantResponse:
    """Add an ad variant to a campaign."""
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    campaign = await _get_or_404(campaign_id, claims_typed.org_id, db)

    if "type" not in body.stimulus:
        raise HTTPException(status_code=422, detail="stimulus must include a 'type' field.")

    variant = CampaignVariantORM(
        campaign_id=campaign.id,
        name=body.name,
        stimulus=body.stimulus,
    )
    db.add(variant)
    await db.flush()
    await db.refresh(variant)
    logger.info("Added variant '%s' to campaign '%s'.", variant.name, campaign_id)
    return VariantResponse.from_orm(variant)


@router.get("/{campaign_id}/variants", response_model=list[VariantResponse])
async def list_variants(
    campaign_id: str,
    claims:      Annotated[object, Depends(require(Permission.CAMPAIGNS_READ))],
    db:          DbDep,
) -> list[VariantResponse]:
    """List all variants for a campaign, ordered by rank (nulls last)."""
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    campaign = await _get_or_404(campaign_id, claims_typed.org_id, db)

    rows = await db.execute(
        select(CampaignVariantORM)
        .where(CampaignVariantORM.campaign_id == campaign.id)
        .order_by(
            CampaignVariantORM.rank.asc().nulls_last(),
            CampaignVariantORM.created_at.asc(),
        )
    )
    return [VariantResponse.from_orm(v) for v in rows.scalars().all()]


@router.delete("/{campaign_id}/variants/{variant_id}", status_code=204)
async def delete_variant(
    campaign_id: str,
    variant_id:  str,
    claims:      Annotated[object, Depends(require(Permission.CAMPAIGNS_WRITE))],
    db:          DbDep,
) -> None:
    """Remove a variant from a campaign."""
    from api.auth.jwt_handler import TokenClaims
    claims_typed: TokenClaims = claims  # type: ignore[assignment]

    campaign = await _get_or_404(campaign_id, claims_typed.org_id, db)

    try:
        vid = uuid.UUID(variant_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid variant_id format") from exc

    result = await db.execute(
        select(CampaignVariantORM).where(
            CampaignVariantORM.id == vid,
            CampaignVariantORM.campaign_id == campaign.id,
        )
    )
    variant = result.scalar_one_or_none()
    if variant is None:
        raise HTTPException(status_code=404, detail="Variant not found")

    await db.delete(variant)
    logger.info("Deleted variant '%s'.", variant_id)


# ── Helper ─────────────────────────────────────────────────────────────────────

async def _get_or_404(campaign_id: str, org_id: uuid.UUID, db: AsyncSession) -> CampaignORM:
    try:
        uid = uuid.UUID(campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid campaign_id format") from exc

    result = await db.execute(
        select(CampaignORM).where(
            CampaignORM.id == uid,
            CampaignORM.org_id == org_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign
