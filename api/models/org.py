"""ORM models for org, membership, API keys, and audit events — S9-01/03/04/06."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.services.db import Base


class OrganizationORM(Base):
    __tablename__ = "organizations"

    id:         Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:       Mapped[str]          = mapped_column(Text, nullable=False)
    slug:       Mapped[str]          = mapped_column(Text, nullable=False, unique=True)
    plan:       Mapped[str]          = mapped_column(Text, nullable=False, default="free")
    created_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class OrgMemberORM(Base):
    __tablename__ = "org_members"

    id:         Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id:     Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id:    Mapped[str]          = mapped_column(Text, nullable=False)   # provider sub
    email:      Mapped[str]          = mapped_column(Text, nullable=False)
    role:       Mapped[str]          = mapped_column(Text, nullable=False, default="viewer")
    invited_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    joined_at:  Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("uq_org_member", "org_id", "user_id", unique=True),
    )


class ApiKeyORM(Base):
    __tablename__ = "api_keys"

    id:           Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id:       Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name:         Mapped[str]                 = mapped_column(Text, nullable=False)
    key_hash:     Mapped[str]                 = mapped_column(Text, nullable=False, unique=True)
    key_prefix:   Mapped[str]                 = mapped_column(Text, nullable=False)
    role:         Mapped[str]                 = mapped_column(Text, nullable=False, default="marketer")
    expires_at:   Mapped[Optional[datetime]]  = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[Optional[datetime]]  = mapped_column(DateTime(timezone=True), nullable=True)
    created_by:   Mapped[str]                 = mapped_column(Text, nullable=False)
    created_at:   Mapped[datetime]            = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active:    Mapped[bool]                = mapped_column(Boolean, nullable=False, default=True)


class AuditEventORM(Base):
    __tablename__ = "audit_events"

    id:             Mapped[uuid.UUID]          = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id:         Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    user_id:        Mapped[str]                = mapped_column(Text, nullable=False)
    email:          Mapped[Optional[str]]      = mapped_column(Text, nullable=True)
    role:           Mapped[Optional[str]]      = mapped_column(Text, nullable=True)
    action:         Mapped[str]                = mapped_column(Text, nullable=False)
    resource_type:  Mapped[Optional[str]]      = mapped_column(Text, nullable=True)
    resource_id:    Mapped[Optional[str]]      = mapped_column(Text, nullable=True)
    request_path:   Mapped[Optional[str]]      = mapped_column(Text, nullable=True)
    request_method: Mapped[Optional[str]]      = mapped_column(Text, nullable=True)
    request_ip:     Mapped[Optional[str]]      = mapped_column(Text, nullable=True)
    user_agent:     Mapped[Optional[str]]      = mapped_column(Text, nullable=True)
    status_code:    Mapped[Optional[int]]      = mapped_column(nullable=True)
    created_at:     Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
