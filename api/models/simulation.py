"""Simulation run API models (Pydantic) and ORM model (SQLAlchemy).

The `simulation_runs` table was created in migrations/001_initial_schema.sql.
The ORM model here maps to that table.

A SimulationRun pairs one segment with one stimulus and stores the full
synthetic persona response alongside the final conversion score.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.services.db import Base


# ── SQLAlchemy ORM model ───────────────────────────────────────────────────────

class SimulationRunORM(Base):
    __tablename__ = "simulation_runs"

    id:         Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id:     Mapped[uuid.UUID | None]    = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    segment_id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), nullable=False)

    # The full stimulus object stored as JSONB so any type is supported
    stimulus: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Persona response fields
    verbatim_response: Mapped[str | None] = mapped_column(String, nullable=True)
    sentiment: Mapped[str | None]         = mapped_column(String, nullable=True)
    likelihood_to_convert: Mapped[float | None] = mapped_column(Float, nullable=True)
    conversion_score: Mapped[float | None]      = mapped_column(Float, nullable=True)

    # Full LLM response blob (key_factors, raw_text, token counts, latency)
    llm_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    status: Mapped[str]     = mapped_column(String, nullable=False, default="pending")
    model_id: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Pydantic request/response models ──────────────────────────────────────────

class SimulateRunRequest(BaseModel):
    """Request body for POST /simulate/run."""

    segment_id: str = Field(description="UUID of the segment to simulate.")
    stimulus: dict[str, Any] = Field(
        description="Stimulus object. Must include 'type' discriminator field."
    )
    model: str | None = Field(
        default=None,
        description="Claude model override. Defaults to claude-sonnet-4-6.",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


class SimulationRunResponse(BaseModel):
    """Response body for simulation run endpoints."""

    id: str
    segment_id: str
    stimulus: dict[str, Any]
    verbatim_response: str | None
    sentiment: str | None
    likelihood_to_convert: float | None
    conversion_score: float | None
    llm_metadata: dict[str, Any]
    status: str
    model_id: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj: SimulationRunORM) -> SimulationRunResponse:
        return cls(
            id=str(obj.id),
            segment_id=str(obj.segment_id),
            stimulus=obj.stimulus,
            verbatim_response=obj.verbatim_response,
            sentiment=obj.sentiment,
            likelihood_to_convert=obj.likelihood_to_convert,
            conversion_score=obj.conversion_score,
            llm_metadata=obj.llm_metadata,
            status=obj.status,
            model_id=obj.model_id,
            created_at=obj.created_at,
            completed_at=obj.completed_at,
        )


class SimulationRunListResponse(BaseModel):
    items: list[SimulationRunResponse]
    total: int
    page:  int
    size:  int


# ── Status literals ────────────────────────────────────────────────────────────

SimulationStatus = Literal["pending", "running", "completed", "failed"]
