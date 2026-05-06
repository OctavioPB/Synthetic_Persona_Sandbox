"""Unit tests for the simulation API layer (Sprint 4).

These tests are unit-level: they mock the PersonaInferenceService and
ConversionScorer so no real Claude API calls are made.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from ml.synthetic_data.persona_inference import SyntheticResponse
from api.models.simulation import (
    SimulateRunRequest,
    SimulationRunResponse,
    SimulationRunORM,
)


# ── SimulateRunRequest validation ──────────────────────────────────────────────

def test_simulate_run_request_defaults() -> None:
    req = SimulateRunRequest(
        segment_id=str(uuid.uuid4()),
        stimulus={"type": "ad_copy", "headline": "H", "body_copy": "B", "cta": "Buy"},
    )
    assert req.temperature == 0.7
    assert req.model is None


def test_simulate_run_request_temperature_out_of_range() -> None:
    with pytest.raises(ValidationError):
        SimulateRunRequest(
            segment_id=str(uuid.uuid4()),
            stimulus={"type": "promo"},
            temperature=1.5,
        )


# ── SimulationRunResponse serialization ───────────────────────────────────────

def test_simulation_run_response_from_orm() -> None:
    run = SimulationRunORM()
    run.id                     = uuid.uuid4()
    run.segment_id             = uuid.uuid4()
    run.stimulus               = {"type": "ad_copy", "headline": "H", "body_copy": "B", "cta": "Go"}
    run.verbatim_response      = "Looks great!"
    run.sentiment              = "positive"
    run.likelihood_to_convert  = 0.75
    run.conversion_score       = 0.80
    run.llm_metadata           = {"key_factors": ["price"], "latency_ms": 520.0}
    run.status                 = "completed"
    run.model_id               = "claude-sonnet-4-6"
    run.created_at             = datetime.now(timezone.utc)
    run.completed_at           = datetime.now(timezone.utc)

    resp = SimulationRunResponse.from_orm(run)
    assert resp.sentiment == "positive"
    assert resp.conversion_score == pytest.approx(0.80)
    assert resp.status == "completed"
    assert resp.llm_metadata["key_factors"] == ["price"]


# ── SyntheticResponse validation ───────────────────────────────────────────────

def test_synthetic_response_valid() -> None:
    r = SyntheticResponse(
        segment_id="seg-1",
        stimulus_id="stim-1",
        verbatim_response="Interesting offer.",
        sentiment="neutral",
        likelihood_to_convert=0.4,
        key_factors=["value"],
    )
    assert r.likelihood_to_convert == 0.4


def test_synthetic_response_invalid_sentiment() -> None:
    with pytest.raises(ValueError, match="Invalid sentiment"):
        SyntheticResponse(
            segment_id="s",
            stimulus_id="t",
            verbatim_response="X",
            sentiment="excited",
            likelihood_to_convert=0.5,
        )


def test_synthetic_response_out_of_range_ltc() -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        SyntheticResponse(
            segment_id="s",
            stimulus_id="t",
            verbatim_response="X",
            sentiment="positive",
            likelihood_to_convert=1.5,
        )


# ── PersonaInferenceService JSON parsing ──────────────────────────────────────

def test_parse_response_strips_markdown_fences() -> None:
    from ml.synthetic_data.persona_inference import PersonaInferenceService
    svc = PersonaInferenceService.__new__(PersonaInferenceService)

    raw = '```json\n{"verbatim_response": "Hello", "sentiment": "positive", "likelihood_to_convert": 0.8, "key_factors": ["price"]}\n```'
    result = svc._parse_response(raw, "stim-1")
    assert result["verbatim_response"] == "Hello"
    assert result["sentiment"] == "positive"


def test_parse_response_coerces_bad_sentiment_to_neutral() -> None:
    from ml.synthetic_data.persona_inference import PersonaInferenceService
    svc = PersonaInferenceService.__new__(PersonaInferenceService)

    raw = '{"verbatim_response": "Hmm", "sentiment": "excited", "likelihood_to_convert": 0.5}'
    result = svc._parse_response(raw, "stim-1")
    assert result["sentiment"] == "neutral"


def test_parse_response_clamps_ltc() -> None:
    from ml.synthetic_data.persona_inference import PersonaInferenceService
    svc = PersonaInferenceService.__new__(PersonaInferenceService)

    raw = '{"verbatim_response": "X", "sentiment": "positive", "likelihood_to_convert": 1.5}'
    result = svc._parse_response(raw, "stim-1")
    assert result["likelihood_to_convert"] == pytest.approx(1.0)


def test_parse_response_raises_on_invalid_json() -> None:
    from ml.synthetic_data.persona_inference import PersonaInferenceService
    svc = PersonaInferenceService.__new__(PersonaInferenceService)

    with pytest.raises(ValueError, match="non-JSON"):
        svc._parse_response("Not JSON at all", "stim-1")


def test_parse_response_raises_on_missing_keys() -> None:
    from ml.synthetic_data.persona_inference import PersonaInferenceService
    svc = PersonaInferenceService.__new__(PersonaInferenceService)

    raw = '{"verbatim_response": "X", "sentiment": "positive"}'
    with pytest.raises(ValueError, match="missing required keys"):
        svc._parse_response(raw, "stim-1")
