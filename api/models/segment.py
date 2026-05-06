"""Segment API models (Pydantic) and ORM model (SQLAlchemy).

The `segments` table was created in migrations/001_initial_schema.sql.
The ORM model here maps to that table — do not change column names without
a corresponding migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.services.db import Base
from ml.segment_models.segment_schema import SegmentDefinition


# ── SQLAlchemy ORM model ───────────────────────────────────────────────────────

class SegmentORM(Base):
    __tablename__ = "segments"

    id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str]           = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    qdrant_id: Mapped[str | None]      = mapped_column(String, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String, nullable=True)
    is_stale: Mapped[bool]             = mapped_column(Boolean, nullable=False, default=False)
    last_trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None]     = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ── Pydantic request/response models ──────────────────────────────────────────

class SegmentCreate(BaseModel):
    name:        str = Field(min_length=1, max_length=120)
    description: str | None = None
    definition:  SegmentDefinition = Field(default_factory=SegmentDefinition)


class SegmentUpdate(BaseModel):
    name:        str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    definition:  SegmentDefinition | None = None


class SegmentResponse(BaseModel):
    id:              str
    org_id:          str
    name:            str
    description:     str | None
    definition:      SegmentDefinition
    qdrant_id:       str | None
    embedding_model: str | None
    is_stale:        bool
    last_trained_at: datetime | None
    created_at:      datetime
    updated_at:      datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj: SegmentORM) -> SegmentResponse:
        return cls(
            id=str(obj.id),
            org_id=str(obj.org_id),
            name=obj.name,
            description=obj.description,
            definition=SegmentDefinition.model_validate(obj.definition),
            qdrant_id=obj.qdrant_id,
            embedding_model=obj.embedding_model,
            is_stale=obj.is_stale,
            last_trained_at=obj.last_trained_at,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


class SegmentListResponse(BaseModel):
    items: list[SegmentResponse]
    total: int
    page:  int
    size:  int
