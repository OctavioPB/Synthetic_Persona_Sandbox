"""Simulation error taxonomy — S6-09.

Defines every failure class the simulation pipeline can produce, with:
  - error_code:    machine-readable string (logged, stored in llm_metadata)
  - http_status:   HTTP status code for API responses
  - retryable:     True if the worker should retry (exponential backoff)
  - description:   Human-readable explanation for the error taxonomy docs

Usage:
    from api.services.simulation_errors import SimulationError, ERROR_TAXONOMY

    raise SimulationError(ERROR_TAXONOMY["SEGMENT_NOT_FOUND"])
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ErrorDefinition:
    """Static definition of a simulation failure type."""

    error_code:  str
    http_status: int
    retryable:   bool
    description: str


class SimulationError(Exception):
    """Raised by the simulation pipeline with a structured error definition."""

    def __init__(self, definition: ErrorDefinition, detail: str = "") -> None:
        self.definition = definition
        self.detail     = detail
        super().__init__(f"[{definition.error_code}] {detail or definition.description}")


# ── Error taxonomy ─────────────────────────────────────────────────────────────
# Keys are stable identifiers stored in simulation_runs.llm_metadata.error_code.

ERROR_TAXONOMY: Final[dict[str, ErrorDefinition]] = {

    # ── Input validation errors (4xx, not retryable) ──────────────────────────

    "SEGMENT_NOT_FOUND": ErrorDefinition(
        error_code="SEGMENT_NOT_FOUND",
        http_status=404,
        retryable=False,
        description=(
            "The requested segment_id does not exist in the database. "
            "Create the segment first via POST /segments."
        ),
    ),

    "INVALID_STIMULUS_TYPE": ErrorDefinition(
        error_code="INVALID_STIMULUS_TYPE",
        http_status=422,
        retryable=False,
        description=(
            "The stimulus payload has an unknown or missing 'type' discriminator. "
            "Valid types: 'ad_copy', 'price_change', 'promo'."
        ),
    ),

    "INVALID_STIMULUS_SCHEMA": ErrorDefinition(
        error_code="INVALID_STIMULUS_SCHEMA",
        http_status=422,
        retryable=False,
        description=(
            "The stimulus payload failed Pydantic validation. "
            "Check required fields for the stimulus type."
        ),
    ),

    "RATE_LIMIT_EXCEEDED": ErrorDefinition(
        error_code="RATE_LIMIT_EXCEEDED",
        http_status=429,
        retryable=True,
        description=(
            "The organization has exceeded the per-minute simulation request limit. "
            "Retry after the window resets (see Retry-After header)."
        ),
    ),

    # ── LLM inference errors (5xx, retryable) ─────────────────────────────────

    "LLM_API_UNAVAILABLE": ErrorDefinition(
        error_code="LLM_API_UNAVAILABLE",
        http_status=502,
        retryable=True,
        description=(
            "The Anthropic API is unreachable or returned a connection error. "
            "The job will be retried with exponential backoff (up to 3 attempts)."
        ),
    ),

    "LLM_RATE_LIMITED": ErrorDefinition(
        error_code="LLM_RATE_LIMITED",
        http_status=502,
        retryable=True,
        description=(
            "The Anthropic API returned 429 (rate limit). "
            "Retried automatically with exponential backoff."
        ),
    ),

    "LLM_INTERNAL_ERROR": ErrorDefinition(
        error_code="LLM_INTERNAL_ERROR",
        http_status=502,
        retryable=True,
        description=(
            "The Anthropic API returned 5xx. "
            "Retried automatically; escalate if failure persists after 3 attempts."
        ),
    ),

    "LLM_INVALID_JSON_RESPONSE": ErrorDefinition(
        error_code="LLM_INVALID_JSON_RESPONSE",
        http_status=502,
        retryable=True,
        description=(
            "The LLM returned text that could not be parsed as the expected JSON schema. "
            "May be transient. Retried once; if it persists, inspect the system prompt."
        ),
    ),

    "LLM_MISSING_REQUIRED_FIELDS": ErrorDefinition(
        error_code="LLM_MISSING_REQUIRED_FIELDS",
        http_status=502,
        retryable=True,
        description=(
            "The LLM returned valid JSON but missing required fields "
            "('verbatim_response', 'sentiment', 'likelihood_to_convert'). "
            "Usually transient; inspect system prompt if recurring."
        ),
    ),

    # ── Infrastructure errors (5xx, retryable) ────────────────────────────────

    "DATABASE_WRITE_FAILED": ErrorDefinition(
        error_code="DATABASE_WRITE_FAILED",
        http_status=503,
        retryable=True,
        description=(
            "Failed to persist the simulation result to PostgreSQL. "
            "Check DB connectivity and disk space."
        ),
    ),

    "QUEUE_UNAVAILABLE": ErrorDefinition(
        error_code="QUEUE_UNAVAILABLE",
        http_status=503,
        retryable=False,
        description=(
            "The ARQ/Redis queue is unavailable and the job could not be enqueued. "
            "Check Redis connectivity."
        ),
    ),

    "WORKER_TIMEOUT": ErrorDefinition(
        error_code="WORKER_TIMEOUT",
        http_status=504,
        retryable=True,
        description=(
            "The simulation job exceeded the 120-second ARQ job_timeout. "
            "This may indicate Claude API latency spikes. Check LLM response times."
        ),
    ),

    # ── Data quality errors (5xx, not retryable) ──────────────────────────────

    "SEGMENT_NO_BEHAVIORAL_DATA": ErrorDefinition(
        error_code="SEGMENT_NO_BEHAVIORAL_DATA",
        http_status=422,
        retryable=False,
        description=(
            "The segment has no behavioral events in the training window. "
            "Run the extract_segment_data DAG to populate features, or "
            "use a segment with a longer purchase_history_days window."
        ),
    ),

    "SEGMENT_STALE": ErrorDefinition(
        error_code="SEGMENT_STALE",
        http_status=422,
        retryable=False,
        description=(
            "The segment's last_trained_at exceeds the staleness threshold. "
            "Simulation is allowed but results may not reflect current behavior. "
            "Re-trigger extract_segment_data to refresh."
        ),
    ),
}
