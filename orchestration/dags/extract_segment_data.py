"""extract_segment_data DAG — Sprint 3.

Pulls behavioral events for a segment, computes features, generates
an embedding, and stores it in Qdrant. Updates the segment's
`last_trained_at` timestamp in PostgreSQL on completion.

Trigger via Airflow UI with config:
    {"segment_id": "<uuid>"}

The DAG is idempotent: re-running with the same segment_id overwrites
the existing Qdrant point rather than creating a duplicate.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta

import psycopg2
from airflow.decorators import dag, task
from airflow.models.param import Param

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner":           "spb-ml",
    "depends_on_past": False,
    "retries":         2,
    "retry_delay":     timedelta(minutes=5),
}


@dag(
    dag_id="extract_segment_data",
    description="Feature engineering + embedding for one segment.",
    schedule=None,
    start_date=datetime(2026, 5, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    params={
        "segment_id": Param(
            type="string",
            description="UUID of the segment to process.",
        )
    },
    tags=["ml", "segments", "sprint-3"],
)
def extract_segment_data_dag() -> None:

    @task()
    def fetch_segment(segment_id: str) -> dict:  # type: ignore[type-arg]
        """Load segment definition from PostgreSQL.

        Returns:
            Dict with keys: id, name, definition (as JSON string).
        """
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", "synthetic_persona"),
            user=os.getenv("POSTGRES_USER", "spb_user"),
            password=os.getenv("POSTGRES_PASSWORD", "changeme"),
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text, name, definition FROM segments WHERE id = %s",
                    (segment_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError(f"Segment '{segment_id}' not found in PostgreSQL.")
            logger.info("Fetched segment '%s' (id=%s).", row[1], row[0])
            return {"id": row[0], "name": row[1], "definition": json.dumps(row[2])}
        finally:
            conn.close()

    @task()
    def run_feature_engineering(segment_info: dict) -> dict:  # type: ignore[type-arg]
        """Extract behavioral features for the segment.

        Returns:
            Serialized SegmentFeatureMatrix dict (XCom-safe JSON).
        """
        from ml.segment_models.feature_engineering import FeatureEngineeringPipeline
        from ml.segment_models.segment_schema import SegmentDefinition

        definition = SegmentDefinition.model_validate_json(segment_info["definition"])

        with FeatureEngineeringPipeline() as pipeline:
            matrix = pipeline.run(
                segment_id=segment_info["id"],
                segment_name=segment_info["name"],
                definition=definition,
            )

        logger.info(
            "Feature engineering complete: %d users for segment '%s'.",
            len(matrix),
            segment_info["name"],
        )
        return matrix.to_dict()

    @task()
    def generate_embedding(segment_info: dict, matrix_dict: dict) -> str:  # type: ignore[type-arg]
        """Encode the feature matrix and store the embedding in Qdrant.

        Returns:
            The segment_id (passed through for the update_segment task).
        """
        from ml.segment_models.embedding_service import SegmentEmbeddingService
        from ml.segment_models.segment_schema import (
            SegmentDefinition,
            SegmentFeatureMatrix,
        )

        definition = SegmentDefinition.model_validate_json(segment_info["definition"])
        matrix     = SegmentFeatureMatrix.from_dict(matrix_dict)

        service = SegmentEmbeddingService()
        service.encode_and_store(matrix, definition)

        logger.info("Embedding stored for segment '%s'.", matrix.segment_name)
        return segment_info["id"]

    @task()
    def update_segment_metadata(segment_id: str) -> None:
        """Mark the segment as freshly trained in PostgreSQL."""
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", "synthetic_persona"),
            user=os.getenv("POSTGRES_USER", "spb_user"),
            password=os.getenv("POSTGRES_PASSWORD", "changeme"),
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE segments SET last_trained_at = NOW(), is_stale = FALSE WHERE id = %s",
                    (segment_id,),
                )
            conn.commit()
            logger.info("Updated last_trained_at for segment '%s'.", segment_id)
        finally:
            conn.close()

    # ── Task wiring ──────────────────────────────────────────────────────────
    # Airflow passes dag run params as context; access via Jinja or Python.

    @task()
    def get_segment_id(**context: object) -> str:
        return str(context["params"]["segment_id"])  # type: ignore[index]

    sid           = get_segment_id()
    segment_info  = fetch_segment(sid)
    matrix_dict   = run_feature_engineering(segment_info)
    segment_id    = generate_embedding(segment_info, matrix_dict)
    update_segment_metadata(segment_id)


extract_segment_data_dag()
