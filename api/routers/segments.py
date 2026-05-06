"""Segments CRUD API — Sprint 3."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.segment import (
    SegmentCreate,
    SegmentListResponse,
    SegmentORM,
    SegmentResponse,
    SegmentUpdate,
)
from api.services.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/segments", tags=["segments"])

# Hardcoded org_id for Sprint 3 — replaced by Auth in Sprint 9
_DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=SegmentResponse, status_code=201)
async def create_segment(body: SegmentCreate, db: DbDep) -> SegmentResponse:
    """Create a new segment definition.

    The segment starts as stale (no embedding yet). Trigger the
    `extract_segment_data` Airflow DAG to generate its embedding.
    """
    segment = SegmentORM(
        org_id=_DEFAULT_ORG_ID,
        name=body.name,
        description=body.description,
        definition=body.definition.model_dump(),
        is_stale=True,
    )
    db.add(segment)
    await db.flush()
    await db.refresh(segment)
    logger.info("Created segment '%s' (id=%s).", segment.name, segment.id)
    return SegmentResponse.from_orm(segment)


@router.get("", response_model=SegmentListResponse)
async def list_segments(
    db: DbDep,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> SegmentListResponse:
    """List segments for the current org, paginated."""
    offset = (page - 1) * size

    total_result = await db.execute(
        select(func.count()).select_from(SegmentORM).where(SegmentORM.org_id == _DEFAULT_ORG_ID)
    )
    total: int = total_result.scalar_one()

    rows = await db.execute(
        select(SegmentORM)
        .where(SegmentORM.org_id == _DEFAULT_ORG_ID)
        .order_by(SegmentORM.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    segments = rows.scalars().all()

    return SegmentListResponse(
        items=[SegmentResponse.from_orm(s) for s in segments],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{segment_id}", response_model=SegmentResponse)
async def get_segment(segment_id: str, db: DbDep) -> SegmentResponse:
    """Get a single segment by ID."""
    try:
        uid = uuid.UUID(segment_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid segment_id format") from exc

    result = await db.execute(
        select(SegmentORM).where(SegmentORM.id == uid, SegmentORM.org_id == _DEFAULT_ORG_ID)
    )
    segment = result.scalar_one_or_none()
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")
    return SegmentResponse.from_orm(segment)


@router.put("/{segment_id}", response_model=SegmentResponse)
async def update_segment(segment_id: str, body: SegmentUpdate, db: DbDep) -> SegmentResponse:
    """Update a segment's name, description, or definition.

    Changing the definition marks the segment as stale — re-trigger
    `extract_segment_data` to refresh the embedding.
    """
    try:
        uid = uuid.UUID(segment_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid segment_id format") from exc

    result = await db.execute(
        select(SegmentORM).where(SegmentORM.id == uid, SegmentORM.org_id == _DEFAULT_ORG_ID)
    )
    segment = result.scalar_one_or_none()
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")

    if body.name is not None:
        segment.name = body.name
    if body.description is not None:
        segment.description = body.description
    if body.definition is not None:
        segment.definition = body.definition.model_dump()
        segment.is_stale = True  # definition changed → embedding is outdated

    await db.flush()
    await db.refresh(segment)
    logger.info("Updated segment '%s'.", segment.id)
    return SegmentResponse.from_orm(segment)


@router.delete("/{segment_id}", status_code=204)
async def delete_segment(segment_id: str, db: DbDep) -> None:
    """Delete a segment and its Qdrant embedding."""
    try:
        uid = uuid.UUID(segment_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid segment_id format") from exc

    result = await db.execute(
        select(SegmentORM).where(SegmentORM.id == uid, SegmentORM.org_id == _DEFAULT_ORG_ID)
    )
    segment = result.scalar_one_or_none()
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")

    if segment.qdrant_id:
        try:
            from ml.segment_models.qdrant_setup import QdrantSegmentStore
            QdrantSegmentStore().delete_segment(segment.qdrant_id)
        except Exception as exc:
            # Log but do not block deletion if Qdrant is unavailable
            logger.warning("Could not delete Qdrant point for segment %s: %s", segment_id, exc)

    await db.delete(segment)
    logger.info("Deleted segment '%s'.", segment_id)
