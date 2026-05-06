"""Pydantic models for the Profile State API."""

from __future__ import annotations

from pydantic import BaseModel


class ProfileState(BaseModel):
    """Real-time behavioral profile for one anonymized user.

    All fields reflect the aggregated state from processed Kafka events.
    Counts and amounts start at zero for users with no ingested events.
    """

    user_id_hash: str
    page_views_total: int = 0
    purchase_count: int = 0
    purchase_total_amount: float = 0.0
    session_count: int = 0
    categories_viewed: list[str] = []
    last_seen: str | None = None
