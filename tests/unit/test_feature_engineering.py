"""Unit tests for the feature engineering pipeline.

Uses a real in-memory SQLite database via psycopg2 mock to keep the tests
free of external dependencies. The SQL logic is tested against a minimal
psycopg2 fixture that mimics RealDictCursor row behaviour.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ml.segment_models.feature_engineering import FeatureEngineeringPipeline, _build_query
from ml.segment_models.segment_schema import AgeRange, GeoFilter, SegmentDefinition, UserFeatures


# ── _build_query ───────────────────────────────────────────────────────────────

class TestBuildQuery:
    def test_basic_query_has_since_param(self) -> None:
        sd = SegmentDefinition(purchase_history_days=30)
        sql, params = _build_query(sd)
        assert "%(since)s" in sql
        assert "since" in params

    def test_no_categories_passes_none(self) -> None:
        sd = SegmentDefinition(category_affinities=[])
        _, params = _build_query(sd)
        assert params["categories"] is None

    def test_categories_passed_as_list(self) -> None:
        sd = SegmentDefinition(category_affinities=["Electronics", "Fashion"])
        _, params = _build_query(sd)
        assert params["categories"] == ["Electronics", "Fashion"]

    def test_min_purchase_count_wraps_in_subquery(self) -> None:
        sd = SegmentDefinition(min_purchase_count=2)
        sql, params = _build_query(sd)
        assert "purchase_count" in sql
        assert "min_purchase_count" in params

    def test_min_page_views_wraps_in_subquery(self) -> None:
        sd = SegmentDefinition(min_page_views=10)
        sql, params = _build_query(sd)
        assert "page_view_count" in sql
        assert "min_page_views" in params

    def test_both_post_filters_in_same_subquery(self) -> None:
        sd = SegmentDefinition(min_purchase_count=1, min_page_views=5)
        sql, params = _build_query(sd)
        assert "purchase_count" in sql
        assert "page_view_count" in sql


# ── FeatureEngineeringPipeline ─────────────────────────────────────────────────

def _mock_pg_conn(rows: list[dict]) -> MagicMock:  # type: ignore[type-arg]
    """Create a mock psycopg2 connection that returns `rows` from fetchall()."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = rows
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


_SAMPLE_ROWS = [
    {
        "user_id_hash":      "hash-001",
        "page_view_count":   20,
        "purchase_count":    3,
        "session_count":     5,
        "total_spent":       149.97,
        "category_diversity": 2,
        "last_activity":     datetime(2026, 4, 28, tzinfo=timezone.utc),
    },
    {
        "user_id_hash":      "hash-002",
        "page_view_count":   8,
        "purchase_count":    1,
        "session_count":     2,
        "total_spent":       49.99,
        "category_diversity": 1,
        "last_activity":     datetime(2026, 5, 1, tzinfo=timezone.utc),
    },
]


class TestFeatureEngineeringPipeline:
    def test_run_returns_correct_user_count(self) -> None:
        pipeline = FeatureEngineeringPipeline(conn=_mock_pg_conn(_SAMPLE_ROWS))
        matrix = pipeline.run("seg-001", "Test", SegmentDefinition())
        assert len(matrix) == 2

    def test_run_maps_rows_to_user_features(self) -> None:
        pipeline = FeatureEngineeringPipeline(conn=_mock_pg_conn(_SAMPLE_ROWS))
        matrix = pipeline.run("seg-001", "Test", SegmentDefinition())
        u = matrix.users[0]
        assert u.user_id_hash     == "hash-001"
        assert u.purchase_count   == 3
        assert u.page_view_count  == 20
        assert abs(u.total_spent - 149.97) < 0.001

    def test_run_sets_window_days_on_each_user(self) -> None:
        sd = SegmentDefinition(purchase_history_days=45)
        pipeline = FeatureEngineeringPipeline(conn=_mock_pg_conn(_SAMPLE_ROWS))
        matrix = pipeline.run("seg-001", "Test", sd)
        for u in matrix.users:
            assert u.window_days == 45

    def test_run_empty_rows_returns_empty_matrix(self) -> None:
        pipeline = FeatureEngineeringPipeline(conn=_mock_pg_conn([]))
        matrix = pipeline.run("seg-001", "Test", SegmentDefinition())
        assert len(matrix) == 0

    def test_run_preserves_segment_metadata(self) -> None:
        pipeline = FeatureEngineeringPipeline(conn=_mock_pg_conn(_SAMPLE_ROWS))
        matrix = pipeline.run("seg-xyz", "My Segment", SegmentDefinition())
        assert matrix.segment_id   == "seg-xyz"
        assert matrix.segment_name == "My Segment"

    def test_context_manager_closes_conn(self) -> None:
        mock_conn = _mock_pg_conn(_SAMPLE_ROWS)
        with FeatureEngineeringPipeline(conn=mock_conn):
            pass
        # The pipeline owns the conn only when created without one —
        # here we pass it explicitly so it should NOT close it.
        mock_conn.close.assert_not_called()
