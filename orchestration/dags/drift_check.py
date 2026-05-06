"""drift_check DAG — Sprint 6.

Runs daily to detect and flag segments whose behavioral data has grown stale
(last_trained_at older than SEGMENT_STALE_THRESHOLD_DAYS, default 7 days).

Stale segments are marked with is_stale=TRUE in PostgreSQL. A downstream
process (or manual trigger of extract_segment_data) should retrain them
before they are used in new simulation runs.

Schedule: daily at 03:00 UTC (low-traffic window).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from airflow.decorators import dag, task

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner":           "spb-ml",
    "depends_on_past": False,
    "retries":         1,
    "retry_delay":     timedelta(minutes=10),
}


@dag(
    dag_id="drift_check",
    description="Daily scan to detect and flag stale persona segments.",
    schedule="0 3 * * *",           # 03:00 UTC daily
    start_date=datetime(2026, 5, 6),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["ml", "drift", "sprint-6"],
)
def drift_check_dag() -> None:

    @task()
    def scan_and_mark_stale() -> dict:  # type: ignore[type-arg]
        """Run DriftDetector.scan_and_mark() and return a summary dict."""
        from ml.evaluation.drift_detector import DriftDetector

        detector = DriftDetector()
        report   = detector.scan_and_mark()

        logger.info(str(report))

        return {
            "scanned_count": report.scanned_count,
            "stale_count":   report.stale_count,
            "marked_count":  report.marked_count,
            "threshold_days": report.threshold_days,
            "stale_segments": [
                {"id": s.id, "name": s.name, "days_since_trained": s.days_since_trained}
                for s in report.stale_segments
            ],
        }

    @task()
    def trigger_retraining(drift_summary: dict) -> None:  # type: ignore[type-arg]
        """Trigger extract_segment_data for each stale segment.

        Uses Airflow's REST API to enqueue DAG runs so each segment is
        retrained without blocking the drift_check DAG itself.

        In environments where the Airflow REST API is not available, this
        task logs the stale segments and exits cleanly — retraining can be
        triggered manually via the Airflow UI.
        """
        import os
        import json
        import urllib.request

        stale = drift_summary.get("stale_segments", [])
        if not stale:
            logger.info("No stale segments — no retraining needed.")
            return

        airflow_base = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
        api_user     = os.getenv("AIRFLOW_API_USER", "admin")
        api_pass     = os.getenv("AIRFLOW_API_PASS", "admin")

        triggered = []
        failed    = []

        for seg in stale:
            payload = json.dumps({
                "conf": {"segment_id": seg["id"]},
            }).encode()
            url = f"{airflow_base}/api/v1/dags/extract_segment_data/dagRuns"

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            # Basic auth
            import base64
            credentials = base64.b64encode(f"{api_user}:{api_pass}".encode()).decode()
            req.add_header("Authorization", f"Basic {credentials}")

            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status in (200, 201):
                        triggered.append(seg["name"])
                        logger.info("Triggered retraining for segment '%s'.", seg["name"])
                    else:
                        failed.append(seg["name"])
            except Exception as exc:
                failed.append(seg["name"])
                logger.warning(
                    "Could not trigger retraining for segment '%s': %s",
                    seg["name"], exc,
                )

        if failed:
            logger.warning(
                "%d segments need manual retraining: %s", len(failed), ", ".join(failed)
            )
        logger.info(
            "Retraining triggered for %d/%d stale segments.",
            len(triggered), len(stale),
        )

    summary = scan_and_mark_stale()
    trigger_retraining(summary)


drift_check_dag()
