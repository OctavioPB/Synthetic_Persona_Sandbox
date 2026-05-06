"""Persona drift detector — flags segments whose behavioral data is stale.

A segment is considered stale if:
  a) last_trained_at IS NULL  (never trained), or
  b) last_trained_at < NOW() - STALE_THRESHOLD_DAYS

Stale segments should be re-trained via the extract_segment_data Airflow DAG
before being used in simulation runs, otherwise their personas reflect
outdated behavioral patterns.

Used by:
  - orchestration/dags/drift_check.py  (scheduled daily)
  - API health checks (future Sprint 9)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import psycopg2

logger = logging.getLogger(__name__)

STALE_THRESHOLD_DAYS = int(os.getenv("SEGMENT_STALE_THRESHOLD_DAYS", "7"))


@dataclass
class StaleSegment:
    """Metadata about a segment that has exceeded the staleness threshold."""

    id:              str
    name:            str
    last_trained_at: datetime | None
    days_since_trained: float


@dataclass
class DriftReport:
    """Summary of a drift detection scan."""

    scanned_count: int
    stale_count:   int
    stale_segments: list[StaleSegment] = field(default_factory=list)
    marked_count:   int = 0
    threshold_days: int = STALE_THRESHOLD_DAYS

    def __str__(self) -> str:
        lines = [
            f"DriftReport: scanned={self.scanned_count} stale={self.stale_count} "
            f"marked={self.marked_count} threshold={self.threshold_days}d"
        ]
        for seg in self.stale_segments:
            trained = (
                f"{seg.days_since_trained:.1f} days ago"
                if seg.last_trained_at
                else "never"
            )
            lines.append(f"  - {seg.name} ({seg.id}): last trained {trained}")
        return "\n".join(lines)


class DriftDetector:
    """Detects and marks stale segments in PostgreSQL.

    Uses a sync psycopg2 connection (compatible with Airflow tasks).
    """

    def __init__(
        self,
        threshold_days: int = STALE_THRESHOLD_DAYS,
        host: str | None = None,
        port: int | None = None,
        dbname: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.threshold_days = threshold_days
        self._conn_params = {
            "host":     host     or os.getenv("POSTGRES_HOST", "localhost"),
            "port":     port     or int(os.getenv("POSTGRES_PORT", "5432")),
            "dbname":   dbname   or os.getenv("POSTGRES_DB", "synthetic_persona"),
            "user":     user     or os.getenv("POSTGRES_USER", "spb_user"),
            "password": password or os.getenv("POSTGRES_PASSWORD", "changeme"),
        }

    def scan(self) -> DriftReport:
        """Identify stale segments without modifying any data.

        Returns:
            DriftReport listing all stale segments.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.threshold_days)

        conn = psycopg2.connect(**self._conn_params)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM segments")
                total: int = cur.fetchone()[0]  # type: ignore[index]

                cur.execute(
                    """
                    SELECT id::text, name, last_trained_at
                    FROM   segments
                    WHERE  last_trained_at IS NULL
                       OR  last_trained_at < %s
                    ORDER BY last_trained_at ASC NULLS FIRST
                    """,
                    (cutoff,),
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        now = datetime.now(timezone.utc)
        stale: list[StaleSegment] = []
        for row in rows:
            seg_id, name, trained_at = row
            days = (
                (now - trained_at.replace(tzinfo=timezone.utc)).total_seconds() / 86400
                if trained_at else float("inf")
            )
            stale.append(StaleSegment(
                id=seg_id,
                name=name,
                last_trained_at=trained_at,
                days_since_trained=days,
            ))

        report = DriftReport(
            scanned_count=total,
            stale_count=len(stale),
            stale_segments=stale,
            threshold_days=self.threshold_days,
        )
        logger.info(
            "Drift scan: %d/%d segments are stale (threshold=%dd).",
            len(stale), total, self.threshold_days,
        )
        return report

    def mark_stale(self, segment_ids: list[str]) -> int:
        """Set is_stale=TRUE for the given segment IDs.

        Args:
            segment_ids: List of UUID strings to mark stale.

        Returns:
            Number of rows updated.
        """
        if not segment_ids:
            return 0

        conn = psycopg2.connect(**self._conn_params)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE segments SET is_stale = TRUE WHERE id = ANY(%s::uuid[])",
                    (segment_ids,),
                )
                updated: int = cur.rowcount
            conn.commit()
        finally:
            conn.close()

        logger.info("Marked %d segments as stale.", updated)
        return updated

    def scan_and_mark(self) -> DriftReport:
        """Scan for stale segments and mark them all in one operation.

        Returns:
            DriftReport with marked_count populated.
        """
        report = self.scan()
        if report.stale_segments:
            ids = [s.id for s in report.stale_segments]
            report.marked_count = self.mark_stale(ids)
        return report
