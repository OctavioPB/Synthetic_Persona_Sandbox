"""Unit tests for segment definition schemas and feature types."""

from datetime import datetime, timezone

import pytest

from ml.segment_models.segment_schema import (
    AVAILABLE_CATEGORIES,
    AgeRange,
    GeoFilter,
    SegmentDefinition,
    SegmentFeatureMatrix,
    UserFeatures,
)


# ── AgeRange ───────────────────────────────────────────────────────────────────

class TestAgeRange:
    def test_valid_range(self) -> None:
        r = AgeRange(min_age=18, max_age=35)
        assert r.min_age == 18 and r.max_age == 35

    def test_same_min_max_valid(self) -> None:
        r = AgeRange(min_age=25, max_age=25)
        assert r.min_age == r.max_age

    def test_inverted_range_raises(self) -> None:
        with pytest.raises(ValueError, match="min_age"):
            AgeRange(min_age=50, max_age=30)


# ── SegmentDefinition ──────────────────────────────────────────────────────────

class TestSegmentDefinition:
    def test_defaults(self) -> None:
        sd = SegmentDefinition()
        assert sd.purchase_history_days == 90
        assert sd.category_affinities   == []
        assert sd.age_range is None
        assert sd.geo is None

    def test_valid_categories(self) -> None:
        sd = SegmentDefinition(category_affinities=["Electronics", "Fashion"])
        assert len(sd.category_affinities) == 2

    def test_unknown_category_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown categories"):
            SegmentDefinition(category_affinities=["Crypto", "NFTs"])

    def test_full_definition(self) -> None:
        sd = SegmentDefinition(
            age_range=AgeRange(min_age=18, max_age=24),
            geo=GeoFilter(city="Madrid", country="Spain"),
            category_affinities=["Electronics", "Fashion"],
            purchase_history_days=60,
            min_purchase_count=1,
        )
        assert sd.geo is not None
        assert sd.geo.city == "Madrid"

    def test_json_roundtrip(self) -> None:
        sd = SegmentDefinition(
            age_range=AgeRange(min_age=18, max_age=35),
            category_affinities=["Books"],
            purchase_history_days=30,
        )
        restored = SegmentDefinition.model_validate_json(sd.model_dump_json())
        assert restored == sd


# ── UserFeatures computed properties ──────────────────────────────────────────

def _make_user(
    purchase_count: int = 5,
    page_view_count: int = 50,
    session_count: int = 10,
    total_spent: float = 250.0,
    category_diversity: int = 3,
    last_activity: datetime | None = None,
    window_days: int = 90,
) -> UserFeatures:
    return UserFeatures(
        user_id_hash="abc123",
        purchase_count=purchase_count,
        page_view_count=page_view_count,
        session_count=session_count,
        total_spent=total_spent,
        category_diversity=category_diversity,
        last_activity=last_activity,
        window_days=window_days,
    )


class TestUserFeatures:
    def test_purchase_frequency(self) -> None:
        u = _make_user(purchase_count=9, window_days=90)
        assert abs(u.purchase_frequency - 0.1) < 1e-9

    def test_avg_basket_size(self) -> None:
        u = _make_user(purchase_count=5, total_spent=250.0)
        assert abs(u.avg_basket_size - 50.0) < 1e-9

    def test_avg_basket_size_no_purchases(self) -> None:
        u = _make_user(purchase_count=0, total_spent=0.0)
        assert u.avg_basket_size == 0.0

    def test_conversion_rate(self) -> None:
        u = _make_user(purchase_count=5, session_count=10)
        assert abs(u.conversion_rate - 0.5) < 1e-9

    def test_conversion_rate_no_sessions(self) -> None:
        u = _make_user(purchase_count=3, session_count=0)
        assert u.conversion_rate == 3.0  # 3/max(0,1)

    def test_session_depth(self) -> None:
        u = _make_user(page_view_count=50, session_count=10)
        assert abs(u.session_depth - 5.0) < 1e-9

    def test_recency_days_no_activity(self) -> None:
        u = _make_user(last_activity=None, window_days=90)
        assert u.recency_days == 90.0

    def test_feature_vector_length(self) -> None:
        u = _make_user()
        assert len(u.to_feature_vector()) == 6

    def test_to_dict_roundtrip(self) -> None:
        u = _make_user(last_activity=datetime(2026, 5, 1, tzinfo=timezone.utc))
        d = u.to_dict()
        assert d["user_id_hash"] == "abc123"
        assert d["last_activity"] == "2026-05-01T00:00:00+00:00"


# ── SegmentFeatureMatrix ───────────────────────────────────────────────────────

class TestSegmentFeatureMatrix:
    def _make_matrix(self, n_users: int = 3) -> SegmentFeatureMatrix:
        users = [
            UserFeatures(
                user_id_hash=f"user-{i}",
                purchase_count=i + 1,
                page_view_count=(i + 1) * 5,
                session_count=i + 1,
                total_spent=(i + 1) * 100.0,
                category_diversity=i + 1,
                last_activity=None,
                window_days=90,
            )
            for i in range(n_users)
        ]
        return SegmentFeatureMatrix(
            segment_id="seg-001",
            segment_name="Test Segment",
            window_days=90,
            users=users,
        )

    def test_len(self) -> None:
        m = self._make_matrix(5)
        assert len(m) == 5

    def test_aggregate_stats_keys(self) -> None:
        m = self._make_matrix()
        stats = m.aggregate_stats()
        assert "purchase_frequency_mean" in stats
        assert "avg_basket_size_mean"    in stats
        assert "conversion_rate_mean"    in stats
        assert "session_depth_mean"      in stats
        assert "category_diversity_mean" in stats
        assert "recency_days_mean"       in stats

    def test_aggregate_stats_empty(self) -> None:
        m = SegmentFeatureMatrix(segment_id="s", segment_name="s", window_days=90, users=[])
        assert m.aggregate_stats() == {}

    def test_to_text_description_non_empty(self) -> None:
        m = self._make_matrix()
        text = m.to_text_description()
        assert "Test Segment" in text
        assert "users" in text.lower()

    def test_dict_roundtrip(self) -> None:
        m = self._make_matrix(2)
        restored = SegmentFeatureMatrix.from_dict(m.to_dict())
        assert restored.segment_id   == m.segment_id
        assert restored.segment_name == m.segment_name
        assert len(restored.users)   == len(m.users)
        assert restored.users[0].user_id_hash == m.users[0].user_id_hash
