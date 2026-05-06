"""Segment definition models and computed feature types.

SegmentDefinition is the canonical descriptor of a customer segment.
UserFeatures and SegmentFeatureMatrix are the outputs of the feature
engineering pipeline.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Available category values (must match ingestion/schemas/events.py) ─────────
AVAILABLE_CATEGORIES: list[str] = [
    "Electronics",
    "Fashion",
    "Home & Garden",
    "Sports",
    "Books",
    "Food & Beverage",
]


# ── Segment definition (stored as JSONB in segments.definition) ────────────────

class AgeRange(BaseModel):
    """Inclusive age range for demographic filtering."""

    min_age: int = Field(ge=0, le=120)
    max_age: int = Field(ge=0, le=120)

    @model_validator(mode="after")
    def check_range(self) -> AgeRange:
        if self.min_age > self.max_age:
            raise ValueError(f"min_age ({self.min_age}) must be <= max_age ({self.max_age})")
        return self


class GeoFilter(BaseModel):
    """Geographic filter for a segment."""

    country: str | None = None
    city:    str | None = None
    region:  str | None = None


class SegmentDefinition(BaseModel):
    """Full descriptor for a customer segment.

    All filters are optional; an empty definition matches all users.
    `category_affinities` drives behavioral event filtering in the
    `extract_segment_data` Airflow DAG.
    """

    age_range:             AgeRange | None = None
    geo:                   GeoFilter | None = None
    category_affinities:   list[str] = Field(default_factory=list)
    purchase_history_days: int = Field(default=90, ge=1, le=365,
                                       description="Lookback window for behavioral events")
    min_purchase_count:    int | None = Field(default=None, ge=0)
    min_page_views:        int | None = Field(default=None, ge=0)

    @field_validator("category_affinities")
    @classmethod
    def validate_categories(cls, v: list[str]) -> list[str]:
        unknown = set(v) - set(AVAILABLE_CATEGORIES)
        if unknown:
            raise ValueError(f"Unknown categories: {unknown}. Valid: {AVAILABLE_CATEGORIES}")
        return v


# ── Computed feature types (output of feature_engineering.py) ─────────────────

@dataclass
class UserFeatures:
    """Per-user behavioral features extracted from behavioral_events.

    Computed over a rolling window defined by `SegmentDefinition.purchase_history_days`.
    """

    user_id_hash:      str
    page_view_count:   int
    purchase_count:    int
    session_count:     int
    total_spent:       float
    category_diversity: int
    last_activity:     datetime | None
    window_days:       int

    @property
    def purchase_frequency(self) -> float:
        """Purchases per day over the lookback window."""
        return self.purchase_count / max(self.window_days, 1)

    @property
    def avg_basket_size(self) -> float:
        """Average purchase amount (0 if no purchases)."""
        return self.total_spent / max(self.purchase_count, 1)

    @property
    def conversion_rate(self) -> float:
        """Purchase count divided by session count (0 if no sessions)."""
        return self.purchase_count / max(self.session_count, 1)

    @property
    def session_depth(self) -> float:
        """Average page views per session (0 if no sessions)."""
        return self.page_view_count / max(self.session_count, 1)

    @property
    def recency_days(self) -> float:
        """Days since the user's last event (window_days if never seen)."""
        if self.last_activity is None:
            return float(self.window_days)
        delta = datetime.utcnow() - self.last_activity.replace(tzinfo=None)
        return max(delta.total_seconds() / 86_400, 0.0)

    def to_feature_vector(self) -> list[float]:
        """Return a fixed-length numeric feature vector for embedding input."""
        return [
            self.purchase_frequency,
            self.avg_basket_size,
            self.conversion_rate,
            self.session_depth,
            float(self.category_diversity),
            self.recency_days,
        ]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["last_activity"] = self.last_activity.isoformat() if self.last_activity else None
        return d


@dataclass
class SegmentFeatureMatrix:
    """Aggregate feature matrix for all users matching a segment definition.

    Designed to be serialized via JSON for Airflow XCom inter-task transport.
    """

    segment_id:   str
    segment_name: str
    window_days:  int
    users:        list[UserFeatures] = field(default_factory=list)
    computed_at:  datetime = field(default_factory=datetime.utcnow)

    def __len__(self) -> int:
        return len(self.users)

    def aggregate_stats(self) -> dict[str, float]:
        """Return mean and std of each feature across all users in this segment."""
        if not self.users:
            return {}

        import statistics

        vectors = [u.to_feature_vector() for u in self.users]
        feature_names = [
            "purchase_frequency", "avg_basket_size", "conversion_rate",
            "session_depth", "category_diversity", "recency_days",
        ]
        stats: dict[str, float] = {}
        for i, name in enumerate(feature_names):
            vals = [v[i] for v in vectors]
            stats[f"{name}_mean"] = statistics.mean(vals)
            stats[f"{name}_std"]  = statistics.stdev(vals) if len(vals) > 1 else 0.0
        return stats

    def to_text_description(self) -> str:
        """Produce a natural-language summary for embedding generation."""
        stats = self.aggregate_stats()
        if not stats:
            return f"Segment: {self.segment_name}. No behavioral data available."
        return (
            f"Segment: {self.segment_name}. "
            f"Users: {len(self.users)}. "
            f"Avg purchase frequency: {stats.get('purchase_frequency_mean', 0):.2f}/day. "
            f"Avg basket size: ${stats.get('avg_basket_size_mean', 0):.2f}. "
            f"Avg session depth: {stats.get('session_depth_mean', 0):.1f} pages/session. "
            f"Avg category diversity: {stats.get('category_diversity_mean', 0):.1f} categories. "
            f"Avg conversion rate: {stats.get('conversion_rate_mean', 0):.3f}."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id":   self.segment_id,
            "segment_name": self.segment_name,
            "window_days":  self.window_days,
            "users":        [u.to_dict() for u in self.users],
            "computed_at":  self.computed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SegmentFeatureMatrix:
        users = []
        for u in d["users"]:
            u = dict(u)
            if u.get("last_activity"):
                u["last_activity"] = datetime.fromisoformat(u["last_activity"])
            users.append(UserFeatures(**u))
        return cls(
            segment_id=d["segment_id"],
            segment_name=d["segment_name"],
            window_days=d["window_days"],
            users=users,
            computed_at=datetime.fromisoformat(d["computed_at"]),
        )
