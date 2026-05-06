"""Prometheus metrics for the simulation API.

Instruments:
  - SIMULATION_LATENCY  — Histogram of end-to-end job duration (seconds)
  - SIMULATION_ERRORS   — Counter of failed simulation jobs, labeled by error type
  - SIMULATION_TOTAL    — Counter of all simulation requests enqueued
  - QUEUE_DEPTH         — Gauge tracking pending jobs in the ARQ queue
  - API_REQUEST_LATENCY — Histogram of FastAPI handler latency

The /metrics endpoint in api/main.py exposes these for Prometheus scraping.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

SIMULATION_LATENCY = Histogram(
    "spb_simulation_latency_seconds",
    "End-to-end simulation job duration from queue to completion.",
    buckets=(1, 2, 3, 5, 10, 15, 20, 30, 60),
)

SIMULATION_ERRORS = Counter(
    "spb_simulation_errors_total",
    "Number of simulation jobs that failed.",
    labelnames=["error_type"],
)

SIMULATION_TOTAL = Counter(
    "spb_simulation_requests_total",
    "Total simulation jobs enqueued.",
    labelnames=["stimulus_type"],
)

QUEUE_DEPTH = Gauge(
    "spb_simulation_queue_depth",
    "Number of simulation jobs currently pending in the ARQ queue.",
)

API_REQUEST_LATENCY = Histogram(
    "spb_api_request_latency_seconds",
    "FastAPI handler latency by route.",
    labelnames=["method", "path", "status_code"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
