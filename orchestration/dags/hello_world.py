"""hello_world DAG — verifies that Airflow can schedule and execute tasks.

This DAG is the Sprint 1 smoke test for the orchestration layer.
It has no external dependencies and is safe to re-run at any time.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from airflow.decorators import dag, task

logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "spb-platform",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="hello_world",
    description="Sprint 1 smoke test — confirms Airflow scheduler is operational.",
    schedule=None,  # manual trigger only
    start_date=datetime(2026, 5, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["smoke-test", "sprint-1"],
)
def hello_world_dag() -> None:
    @task()
    def say_hello() -> str:
        msg = "Synthetic Persona Sandbox — Airflow is operational."
        logger.info(msg)
        return msg

    @task()
    def say_goodbye(greeting: str) -> None:
        logger.info("Received: %s", greeting)
        logger.info("hello_world DAG completed successfully.")

    say_goodbye(say_hello())


hello_world_dag()
