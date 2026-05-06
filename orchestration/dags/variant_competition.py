"""variant_competition DAG — Sprint 5.

Runs all variants of a campaign against the campaign's target segment in parallel,
then ranks them by conversion_score (descending) and persists the ranking.

Flow:
  1. Fetch campaign + variants + segment from PostgreSQL.
  2. Dynamic task mapping: run one simulation per variant (fan-out).
  3. Collect all scores and rank variants (fan-in).
  4. Write ranks back to campaign_variants; update campaign status = 'completed'.

Idempotency: variants that already have a score are not re-simulated. The ranking
step always recomputes from the current scores in the DB, so re-running the DAG
after a partial failure will only re-simulate the missing variants.

Trigger via Airflow UI with config:
    { "campaign_id": "<uuid>" }
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg2
from airflow.decorators import dag, task
from airflow.models.param import Param

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner":           "spb-ml",
    "depends_on_past": False,
    "retries":         1,
    "retry_delay":     timedelta(minutes=5),
}


def _pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "synthetic_persona"),
        user=os.getenv("POSTGRES_USER", "spb_user"),
        password=os.getenv("POSTGRES_PASSWORD", "changeme"),
    )


@dag(
    dag_id="variant_competition",
    description="Compete N campaign variants against a segment; rank by conversion score.",
    schedule=None,
    start_date=datetime(2026, 5, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    params={
        "campaign_id": Param(
            type="string",
            description="UUID of the campaign whose variants will be competed.",
        ),
        "temperature": Param(type="number", default=0.7),
    },
    tags=["ml", "campaigns", "sprint-5"],
)
def variant_competition_dag() -> None:

    @task()
    def fetch_campaign(**context: object) -> dict:  # type: ignore[type-arg]
        """Load campaign, all its variants, and the segment from PostgreSQL."""
        campaign_id = str(context["params"]["campaign_id"])  # type: ignore[index]
        temperature = float(context["params"].get("temperature", 0.7))  # type: ignore[index]

        conn = _pg_conn()
        try:
            with conn.cursor() as cur:
                # Campaign + segment
                cur.execute(
                    """
                    SELECT c.id::text, c.name, c.segment_id::text,
                           s.name, s.definition
                    FROM   campaigns c
                    LEFT JOIN segments s ON s.id = c.segment_id
                    WHERE  c.id = %s
                    """,
                    (campaign_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError(f"Campaign '{campaign_id}' not found.")
                if row[2] is None:
                    raise ValueError(f"Campaign '{campaign_id}' has no target segment.")

                # All variants
                cur.execute(
                    "SELECT id::text, name, stimulus FROM campaign_variants WHERE campaign_id = %s",
                    (campaign_id,),
                )
                variants = [
                    {"variant_id": v[0], "variant_name": v[1], "stimulus": v[2]}
                    for v in cur.fetchall()
                ]
        finally:
            conn.close()

        if not variants:
            raise ValueError(f"Campaign '{campaign_id}' has no variants to compete.")

        logger.info(
            "Competing %d variants for campaign '%s' on segment '%s'.",
            len(variants), row[1], row[3],
        )
        return {
            "campaign_id":   campaign_id,
            "campaign_name": row[1],
            "segment_id":    row[2],
            "segment_name":  row[3],
            "definition":    json.dumps(row[4]),
            "variants":      variants,
            "temperature":   temperature,
        }

    @task()
    def simulate_variant(variant_spec: dict) -> dict:  # type: ignore[type-arg]
        """Run persona inference for a single variant.

        This task is invoked via dynamic task mapping — one instance per variant.
        Idempotent: if the variant already has a score in the DB, returns early.

        Args:
            variant_spec: Dict with keys: variant_id, variant_name, stimulus,
                          segment_id, segment_name, definition, temperature.
        """
        variant_id = variant_spec["variant_id"]

        # Idempotency: skip if already scored
        conn = _pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT score FROM campaign_variants WHERE id = %s AND score IS NOT NULL",
                    (variant_id,),
                )
                existing = cur.fetchone()
        finally:
            conn.close()

        if existing is not None:
            logger.info("Variant %s already scored (%.4f) — skipping.", variant_id, existing[0])
            return {"variant_id": variant_id, "score": float(existing[0]), "skipped": True}

        from ml.synthetic_data.conversion_scorer import ConversionScorer
        from ml.synthetic_data.persona_inference import PersonaInferenceService
        from ml.synthetic_data.stimulus_schema import AnyStimulus
        from pydantic import TypeAdapter

        adapter: TypeAdapter[AnyStimulus] = TypeAdapter(AnyStimulus)  # type: ignore[arg-type]
        stimulus = adapter.validate_python(variant_spec["stimulus"])

        response = PersonaInferenceService().generate(
            segment_id=variant_spec["segment_id"],
            segment_name=variant_spec["segment_name"],
            definition=json.loads(variant_spec["definition"]),
            stimulus=stimulus,
            temperature=variant_spec["temperature"],
        )
        score = ConversionScorer().score(response)

        # Persist simulation run and link to variant
        run_id = str(uuid.uuid4())
        now    = datetime.now(timezone.utc).isoformat()
        conn   = _pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO simulation_runs
                        (id, segment_id, stimulus, verbatim_response, sentiment,
                         likelihood_to_convert, conversion_score, llm_metadata,
                         status, completed_at)
                    VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, 'completed', %s)
                    """,
                    (
                        run_id, variant_spec["segment_id"],
                        json.dumps(variant_spec["stimulus"]),
                        response.verbatim_response, response.sentiment,
                        response.likelihood_to_convert, score,
                        json.dumps({"key_factors": response.key_factors}),
                        now,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

        logger.info(
            "Variant '%s' scored: %.4f (sentiment=%s).",
            variant_spec["variant_name"], score, response.sentiment,
        )
        return {"variant_id": variant_id, "score": score, "run_id": run_id, "skipped": False}

    @task()
    def rank_and_persist(campaign_data: dict, results: list[dict]) -> None:  # type: ignore[type-arg]
        """Sort variants by score and write ranks + run_ids back to PostgreSQL."""
        campaign_id = campaign_data["campaign_id"]

        # Sort descending by score; stable sort preserves insertion order on ties
        ranked = sorted(results, key=lambda r: r["score"], reverse=True)

        conn = _pg_conn()
        try:
            with conn.cursor() as cur:
                for rank, result in enumerate(ranked, start=1):
                    run_id = result.get("run_id")
                    cur.execute(
                        """
                        UPDATE campaign_variants
                        SET rank   = %s,
                            score  = %s,
                            run_id = %s
                        WHERE id = %s
                        """,
                        (rank, result["score"], run_id, result["variant_id"]),
                    )

                cur.execute(
                    "UPDATE campaigns SET status = 'completed' WHERE id = %s",
                    (campaign_id,),
                )

            conn.commit()
            logger.info(
                "Ranked %d variants for campaign '%s'. #1: variant=%s score=%.4f.",
                len(ranked), campaign_id,
                ranked[0]["variant_id"], ranked[0]["score"],
            )
        finally:
            conn.close()

    # ── Task wiring — dynamic mapping ────────────────────────────────────────

    campaign_data = fetch_campaign()

    # Expand simulate_variant over each variant dict.
    # Each variant_spec needs segment context, so we merge it in here.
    @task()
    def build_variant_specs(campaign_data: dict) -> list[dict]:  # type: ignore[type-arg]
        """Inject shared segment context into each variant dict for fan-out."""
        shared = {
            "segment_id":   campaign_data["segment_id"],
            "segment_name": campaign_data["segment_name"],
            "definition":   campaign_data["definition"],
            "temperature":  campaign_data["temperature"],
        }
        return [{**v, **shared} for v in campaign_data["variants"]]

    variant_specs = build_variant_specs(campaign_data)

    # Dynamic task mapping: one task instance per variant
    results = simulate_variant.expand(variant_spec=variant_specs)

    rank_and_persist(campaign_data, results)


variant_competition_dag()
