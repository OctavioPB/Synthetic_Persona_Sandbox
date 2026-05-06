"""Feature engineering pipeline.

Queries `behavioral_events` in PostgreSQL and computes per-user behavioral
features for a given segment definition. Runs synchronously (called from
Airflow tasks, not FastAPI).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg2
import psycopg2.extras

from ml.segment_models.segment_schema import (
    SegmentDefinition,
    SegmentFeatureMatrix,
    UserFeatures,
)

logger = logging.getLogger(__name__)

# ── SQL query ──────────────────────────────────────────────────────────────────
# Computes per-user behavioral aggregates filtered by:
#   1. Time window (purchase_history_days)
#   2. Category affinity overlap (optional)
#
# ON CONFLICT idempotency is handled upstream; this query is read-only.

_FEATURE_SQL = """
SELECT
    user_id_hash,
    COUNT(CASE WHEN event_type = 'page_view' THEN 1 END)::int       AS page_view_count,
    COUNT(CASE WHEN event_type = 'purchase'  THEN 1 END)::int       AS purchase_count,
    COUNT(CASE WHEN event_type = 'session'   THEN 1 END)::int       AS session_count,
    COALESCE(
        SUM(CASE WHEN event_type = 'purchase'
                 THEN (payload->>'amount')::float ELSE 0 END), 0.0
    )                                                                AS total_spent,
    COUNT(DISTINCT
        CASE WHEN payload->>'category' IS NOT NULL
             THEN payload->>'category' END
    )::int                                                           AS category_diversity,
    MAX(timestamp)                                                   AS last_activity
FROM behavioral_events
WHERE timestamp >= %(since)s
  AND (
      %(categories)s::text[] IS NULL
      OR payload->>'category' = ANY(%(categories)s::text[])
  )
GROUP BY user_id_hash
HAVING COUNT(*) > 0
"""

_MIN_PURCHASE_FILTER = " AND purchase_count >= %(min_purchase_count)s"
_MIN_PAGEVIEW_FILTER = " AND page_view_count >= %(min_page_views)s"


def _build_query(definition: SegmentDefinition) -> tuple[str, dict[str, Any]]:
    """Build the feature extraction SQL and its parameter dict."""
    sql    = _FEATURE_SQL
    params: dict[str, Any] = {
        "since":      datetime.now(tz=timezone.utc) - timedelta(days=definition.purchase_history_days),
        "categories": definition.category_affinities or None,
    }
    # Wrap in a subquery when post-aggregate filters are needed
    if definition.min_purchase_count is not None or definition.min_page_views is not None:
        inner = f"SELECT * FROM ({sql}) AS agg WHERE 1=1"
        if definition.min_purchase_count is not None:
            inner += " AND purchase_count >= %(min_purchase_count)s"
            params["min_purchase_count"] = definition.min_purchase_count
        if definition.min_page_views is not None:
            inner += " AND page_view_count >= %(min_page_views)s"
            params["min_page_views"] = definition.min_page_views
        sql = inner
    return sql, params


def _pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "synthetic_persona"),
        user=os.getenv("POSTGRES_USER", "spb_user"),
        password=os.getenv("POSTGRES_PASSWORD", "changeme"),
    )


class FeatureEngineeringPipeline:
    """Extracts and computes behavioral features for a segment.

    Args:
        conn: Optional psycopg2 connection. If None, opens a new one from env vars.
    """

    def __init__(self, conn: psycopg2.extensions.connection | None = None) -> None:
        self._conn = conn or _pg_conn()
        self._owns_conn = conn is None

    def run(self, segment_id: str, segment_name: str, definition: SegmentDefinition) -> SegmentFeatureMatrix:
        """Execute the feature extraction pipeline for one segment.

        Args:
            segment_id:   UUID of the segment (for matrix metadata).
            segment_name: Human-readable segment name.
            definition:   SegmentDefinition with filters.

        Returns:
            SegmentFeatureMatrix with one UserFeatures row per matched user.
        """
        sql, params = _build_query(definition)
        logger.info(
            "Extracting features for segment '%s' (window=%dd, categories=%s)",
            segment_name,
            definition.purchase_history_days,
            definition.category_affinities or "all",
        )

        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        users = [
            UserFeatures(
                user_id_hash=row["user_id_hash"],
                page_view_count=row["page_view_count"],
                purchase_count=row["purchase_count"],
                session_count=row["session_count"],
                total_spent=float(row["total_spent"]),
                category_diversity=row["category_diversity"],
                last_activity=row["last_activity"],
                window_days=definition.purchase_history_days,
            )
            for row in rows
        ]

        matrix = SegmentFeatureMatrix(
            segment_id=segment_id,
            segment_name=segment_name,
            window_days=definition.purchase_history_days,
            users=users,
        )
        logger.info("Segment '%s': %d users extracted.", segment_name, len(users))
        return matrix

    def close(self) -> None:
        if self._owns_conn:
            self._conn.close()

    def __enter__(self) -> FeatureEngineeringPipeline:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
