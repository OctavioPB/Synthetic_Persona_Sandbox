"""Campaign and CampaignVariant API models (Pydantic) and ORM models (SQLAlchemy).

A Campaign groups a set of ad variants to be competed against a single segment.
The variant_competition Airflow DAG runs all variants, then ranks them by
conversion_score and persists the ranking back into campaign_variants.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.services.db import Base


# ── SQLAlchemy ORM models ──────────────────────────────────────────────────────

class CampaignORM(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID]          = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    segment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    name: Mapped[str]              = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str]            = mapped_column(String, nullable=False, default="draft")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CampaignVariantORM(Base):
    __tablename__ = "campaign_variants"

    id: Mapped[uuid.UUID]          = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str]              = mapped_column(String, nullable=False)
    stimulus: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    rank: Mapped[int | None]       = mapped_column(Integer, nullable=True)
    score: Mapped[float | None]    = mapped_column(Numeric(5, 4), nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ── Pydantic request / response models ────────────────────────────────────────

class CampaignCreate(BaseModel):
    name:        str = Field(min_length=1, max_length=120)
    description: str | None = None
    segment_id:  str | None = Field(default=None, description="UUID of the target segment.")


class CampaignUpdate(BaseModel):
    name:        str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    segment_id:  str | None = None
    status:      Literal["draft", "running", "completed", "archived"] | None = None


class CampaignResponse(BaseModel):
    id:          str
    org_id:      str
    segment_id:  str | None
    name:        str
    description: str | None
    status:      str
    created_at:  datetime
    updated_at:  datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj: CampaignORM) -> CampaignResponse:
        return cls(
            id=str(obj.id),
            org_id=str(obj.org_id),
            segment_id=str(obj.segment_id) if obj.segment_id else None,
            name=obj.name,
            description=obj.description,
            status=obj.status,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int
    page:  int
    size:  int


# ── Variant models ─────────────────────────────────────────────────────────────

class VariantCreate(BaseModel):
    name:     str = Field(min_length=1, max_length=120)
    stimulus: dict[str, Any] = Field(description="Stimulus payload with 'type' discriminator.")


class VariantResponse(BaseModel):
    id:          str
    campaign_id: str
    name:        str
    stimulus:    dict[str, Any]
    rank:        int | None
    score:       float | None
    run_id:      str | None
    created_at:  datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj: CampaignVariantORM) -> VariantResponse:
        return cls(
            id=str(obj.id),
            campaign_id=str(obj.campaign_id),
            name=obj.name,
            stimulus=obj.stimulus,
            rank=obj.rank,
            score=float(obj.score) if obj.score is not None else None,
            run_id=str(obj.run_id) if obj.run_id else None,
            created_at=obj.created_at,
        )
