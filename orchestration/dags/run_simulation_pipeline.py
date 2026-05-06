"""run_simulation_pipeline DAG — Sprint 5.

Full end-to-end simulation pipeline for a single (segment, stimulus) pair:

  1. [task] Extract params and enforce idempotency (skip if run already completed).
  2. [task] Wait for Kafka consumer lag to drain (behavioral data is current).
  3. [task] Fetch segment definition from PostgreSQL.
  4. [task] Run feature engineering.
  5. [task] Run persona inference via Claude (PersonaInferenceService).
  6. [task] Score and persist the completed SimulationRun.

Idempotency: if run_id is provided and the row already has status='completed',
tasks 2-6 become no-ops — the DAG exits cleanly after step 1.

Trigger via Airflow UI with config:
    {
        "segment_id":  "<uuid>",
        "stimulus":    { "type": "ad_copy", "headline": "...", "body_copy": "...", "cta": "..." },
        "run_id":      "<uuid>",    -- optional; auto-generated if omitted
        "temperature": 0.7          -- optional
    }
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
    "retries":         2,
    "retry_delay":     timedelta(minutes=3),
}

_KAFKA_TOPIC    = "events.purchases"
_KAFKA_GROUP_ID = "behavioral-consumer-group"
_MAX_LAG        = 10    # tolerate up to 10 messages of lag before proceeding
_LAG_POLL_SECS  = 6
_LAG_MAX_POLLS  = 10


def _pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "synthetic_persona"),
        user=os.getenv("POSTGRES_USER", "spb_user"),
        password=os.getenv("POSTGRES_PASSWORD", "changeme"),
    )


@dag(
    dag_id="run_simulation_pipeline",
    description="End-to-end simulation: segment features → Claude inference → score storage.",
    schedule=None,
    start_date=datetime(2026, 5, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    params={
        "segment_id": Param(type="string", description="UUID of the segment."),
        "stimulus":   Param(type="object", description="Stimulus payload with 'type' discriminator."),
        "run_id":     Param(type=["string", "null"], default=None, description="Reuse existing run_id for idempotency."),
        "temperature": Param(type="number", default=0.7),
    },
    tags=["ml", "simulation", "sprint-5"],
)
def run_simulation_pipeline_dag() -> None:

    @task()
    def init_run(**context: object) -> dict:  # type: ignore[type-arg]
        """Normalize params and enforce idempotency.

        Returns a state dict with 'skip=True' if the run is already completed.
        """
        params     = context["params"]  # type: ignore[index]
        segment_id = str(params["segment_id"])
        stimulus   = params["stimulus"]
        run_id     = str(params["run_id"]) if params.get("run_id") else str(uuid.uuid4())
        temperature = float(params.get("temperature", 0.7))

        conn = _pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT status FROM simulation_runs WHERE id = %s", (run_id,))
                row = cur.fetchone()
        finally:
            conn.close()

        already_done = row is not None and row[0] == "completed"
        if already_done:
            logger.info("Run %s is already completed — pipeline will skip.", run_id)

        return {
            "segment_id":  segment_id,
            "stimulus":    stimulus,
            "run_id":      run_id,
            "temperature": temperature,
            "skip":        already_done,
        }

    @task()
    def wait_for_kafka_drain(state: dict) -> dict:  # type: ignore[type-arg]
        """Poll Kafka consumer group lag until it drains or we time out."""
        if state["skip"]:
            return state

        import time

        from orchestration.plugins.kafka_lag_sensor import KafkaConsumerLagSensor

        sensor = KafkaConsumerLagSensor(
            task_id="_inline_lag_check",
            topic=_KAFKA_TOPIC,
            group_id=_KAFKA_GROUP_ID,
            max_lag=_MAX_LAG,
        )

        for attempt in range(1, _LAG_MAX_POLLS + 1):
            if sensor.poke({}):
                logger.info("Kafka lag drained after %d poll(s).", attempt)
                return state
            logger.debug("Lag still above threshold on poll %d/%d.", attempt, _LAG_MAX_POLLS)
            time.sleep(_LAG_POLL_SECS)

        logger.warning(
            "Kafka lag did not drain within %ds — proceeding with potentially stale data.",
            _LAG_POLL_SECS * _LAG_MAX_POLLS,
        )
        return state

    @task()
    def fetch_segment(state: dict) -> dict:  # type: ignore[type-arg]
        """Load segment name and definition from PostgreSQL."""
        if state["skip"]:
            return state

        conn = _pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text, name, definition FROM segments WHERE id = %s",
                    (state["segment_id"],),
                )
                row = cur.fetchone()
        finally:
            conn.close()

        if row is None:
            raise ValueError(f"Segment '{state['segment_id']}' not found.")

        logger.info("Fetched segment '%s'.", row[1])
        return {**state, "segment_name": row[1], "definition": json.dumps(row[2])}

    @task()
    def run_feature_engineering(state: dict) -> dict:  # type: ignore[type-arg]
        """Compute aggregate behavioral feature stats for the segment."""
        if state["skip"]:
            return state

        from ml.segment_models.feature_engineering import FeatureEngineeringPipeline
        from ml.segment_models.segment_schema import SegmentDefinition

        definition = SegmentDefinition.model_validate_json(state["definition"])

        with FeatureEngineeringPipeline() as pipeline:
            matrix = pipeline.run(
                segment_id=state["segment_id"],
                segment_name=state["segment_name"],
                definition=definition,
            )

        agg = matrix.aggregate_stats()
        logger.info("Feature engineering done: %d users.", matrix.user_count)
        return {**state, "feature_stats": agg, "user_count": matrix.user_count}

    @task()
    def run_inference(state: dict) -> dict:  # type: ignore[type-arg]
        """Generate synthetic persona response via Claude."""
        if state["skip"]:
            return state

        from ml.synthetic_data.persona_inference import PersonaInferenceService
        from ml.synthetic_data.stimulus_schema import AnyStimulus
        from pydantic import TypeAdapter

        adapter: TypeAdapter[AnyStimulus] = TypeAdapter(AnyStimulus)  # type: ignore[arg-type]
        stimulus = adapter.validate_python(state["stimulus"])

        response = PersonaInferenceService().generate(
            segment_id=state["segment_id"],
            segment_name=state["segment_name"],
            definition=json.loads(state["definition"]),
            stimulus=stimulus,
            feature_stats=state.get("feature_stats"),
            user_count=state.get("user_count", 0),
            temperature=state["temperature"],
        )

        logger.info(
            "Inference: sentiment=%s ltc=%.3f latency=%.0fms",
            response.sentiment, response.likelihood_to_convert, response.latency_ms,
        )
        return {
            **state,
            "verbatim_response":     response.verbatim_response,
            "sentiment":             response.sentiment,
            "likelihood_to_convert": response.likelihood_to_convert,
            "key_factors":           response.key_factors,
            "input_tokens":          response.input_tokens,
            "output_tokens":         response.output_tokens,
            "latency_ms":            response.latency_ms,
        }

    @task()
    def score_and_persist(state: dict) -> str:  # type: ignore[type-arg]
        """Compute final conversion score and upsert the simulation run."""
        if state["skip"]:
            logger.info("Skipping persist — run %s already done.", state["run_id"])
            return state["run_id"]

        from ml.synthetic_data.conversion_scorer import ConversionScorer
        from ml.synthetic_data.persona_inference import SyntheticResponse

        synthetic = SyntheticResponse(
            segment_id=state["segment_id"],
            stimulus_id=str(state["stimulus"].get("stimulus_id", "")),
            verbatim_response=state["verbatim_response"],
            sentiment=state["sentiment"],
            likelihood_to_convert=state["likelihood_to_convert"],
            key_factors=state.get("key_factors", []),
        )
        conversion_score = ConversionScorer().score(synthetic)
        now = datetime.now(timezone.utc).isoformat()

        conn = _pg_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO simulation_runs
                        (id, segment_id, stimulus, verbatim_response, sentiment,
                         likelihood_to_convert, conversion_score, llm_metadata,
                         status, completed_at)
                    VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, 'completed', %s)
                    ON CONFLICT (id) DO UPDATE SET
                        verbatim_response     = EXCLUDED.verbatim_response,
                        sentiment             = EXCLUDED.sentiment,
                        likelihood_to_convert = EXCLUDED.likelihood_to_convert,
                        conversion_score      = EXCLUDED.conversion_score,
                        llm_metadata          = EXCLUDED.llm_metadata,
                        status                = 'completed',
                        completed_at          = EXCLUDED.completed_at
                    """,
                    (
                        state["run_id"],
                        state["segment_id"],
                        json.dumps(state["stimulus"]),
                        synthetic.verbatim_response,
                        synthetic.sentiment,
                        synthetic.likelihood_to_convert,
                        conversion_score,
                        json.dumps({
                            "key_factors":   state.get("key_factors", []),
                            "input_tokens":  state.get("input_tokens", 0),
                            "output_tokens": state.get("output_tokens", 0),
                            "latency_ms":    state.get("latency_ms", 0.0),
                        }),
                        now,
                    ),
                )
            conn.commit()
            logger.info("Run %s persisted: score=%.4f.", state["run_id"], conversion_score)
        finally:
            conn.close()

        return state["run_id"]

    # ── Task wiring ──────────────────────────────────────────────────────────

    s0 = init_run()
    s1 = wait_for_kafka_drain(s0)
    s2 = fetch_segment(s1)
    s3 = run_feature_engineering(s2)
    s4 = run_inference(s3)
    score_and_persist(s4)


run_simulation_pipeline_dag()
