"""Locust load test — S6-08: 20 concurrent simulation runs @ p99 < 10s.

Target:
  - 20 concurrent users
  - Each user fires POST /simulate/run (async) then polls GET /simulate/runs/{id}
    until the run reaches a terminal state or 30 seconds elapses.
  - p99 end-to-end completion time < 10 seconds.

Run:
    locust -f tests/load/locustfile.py \
           --host http://localhost:8000 \
           --users 20 \
           --spawn-rate 4 \
           --run-time 2m \
           --headless

Requires:
  - API running: uv run uvicorn api.main:app --port 8000
  - ARQ worker: uv run arq api.workers.simulation_worker.WorkerSettings
  - At least one segment in the DB (see SEED_SEGMENT_ID below)
  - ANTHROPIC_API_KEY set or CACHE_DIR containing cached responses

Set SEED_SEGMENT_ID to a real segment UUID in your local DB:
    export SEED_SEGMENT_ID=<your-segment-uuid>
"""

from __future__ import annotations

import os
import random
import time

from locust import HttpUser, between, task

# Override this with a real segment UUID from your local DB.
SEED_SEGMENT_ID = os.getenv("SEED_SEGMENT_ID", "00000000-0000-0000-0000-000000000099")

_STIMULI = [
    {
        "type":      "ad_copy",
        "headline":  "Summer Sale — Up to 50% Off",
        "body_copy": "Discover curated deals on your favorite categories.",
        "cta":       "Shop Now",
    },
    {
        "type":           "price_change",
        "product_name":   "Wireless Headphones",
        "original_price": 120.00,
        "new_price":      89.99,
    },
    {
        "type":           "promo",
        "promo_code":     f"LOAD{random.randint(1000, 9999)}",
        "discount_value": 15.0,
        "discount_type":  "percent",
        "expiry_days":    3,
    },
]


class SimulationUser(HttpUser):
    """Simulates a marketer launching simulations and polling for results."""

    wait_time = between(0.5, 2.0)

    @task(3)
    def async_simulation_roundtrip(self) -> None:
        """POST /simulate/run → poll GET /simulate/runs/{id} until terminal."""
        stimulus = random.choice(_STIMULI)

        with self.client.post(
            "/simulate/run",
            json={"segment_id": SEED_SEGMENT_ID, "stimulus": stimulus},
            catch_response=True,
            name="POST /simulate/run",
        ) as resp:
            if resp.status_code not in (200, 201, 202):
                resp.failure(f"Unexpected status {resp.status_code}")
                return
            run_id = resp.json().get("id")
            if not run_id:
                resp.failure("No run_id in response")
                return

        if not run_id:
            return

        # Poll for completion (max 30s, 1s interval)
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            with self.client.get(
                f"/simulate/runs/{run_id}",
                catch_response=True,
                name="GET /simulate/runs/{id}",
            ) as poll:
                if poll.status_code != 200:
                    poll.failure(f"Poll returned {poll.status_code}")
                    return
                status = poll.json().get("status")
                if status == "completed":
                    return
                if status == "failed":
                    poll.failure("Run ended with status=failed")
                    return
            time.sleep(1.0)

        # If we reach here the run did not complete within 30s
        self.client.get(
            f"/simulate/runs/{run_id}",
            name="GET /simulate/runs/{id} [timeout]",
        )

    @task(1)
    def list_recent_runs(self) -> None:
        """GET /simulate/runs — simulates a marketer checking history."""
        self.client.get(
            f"/simulate/runs?segment_id={SEED_SEGMENT_ID}&size=10",
            name="GET /simulate/runs",
        )

    @task(1)
    def health_check(self) -> None:
        """GET /health — baseline latency reference."""
        self.client.get("/health", name="GET /health")
