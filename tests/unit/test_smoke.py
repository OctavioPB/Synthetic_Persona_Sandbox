"""Smoke tests — S6-10: critical simulation path imports and instantiations.

These tests do not call external APIs, touch the database, or hit Redis.
They verify that:
  - All critical modules import cleanly (no syntax errors, missing deps).
  - Core classes instantiate without errors.
  - Key method signatures exist and are callable.

Run in < 2 seconds. Intended as a pre-push gate.
"""

from __future__ import annotations

import importlib


# ── Import smoke tests ─────────────────────────────────────────────────────────

def test_import_stimulus_schema() -> None:
    mod = importlib.import_module("ml.synthetic_data.stimulus_schema")
    assert hasattr(mod, "AdCopyStimulus")
    assert hasattr(mod, "format_stimulus_prompt")


def test_import_claude_client() -> None:
    mod = importlib.import_module("ml.synthetic_data.claude_client")
    assert hasattr(mod, "CachedClaudeClient")


def test_import_persona_context_builder() -> None:
    mod = importlib.import_module("ml.synthetic_data.persona_context_builder")
    assert hasattr(mod, "PersonaContextBuilder")


def test_import_persona_inference() -> None:
    mod = importlib.import_module("ml.synthetic_data.persona_inference")
    assert hasattr(mod, "PersonaInferenceService")
    assert hasattr(mod, "SyntheticResponse")


def test_import_conversion_scorer() -> None:
    mod = importlib.import_module("ml.synthetic_data.conversion_scorer")
    assert hasattr(mod, "ConversionScorer")


def test_import_holdout_evaluator() -> None:
    mod = importlib.import_module("ml.evaluation.holdout_evaluator")
    assert hasattr(mod, "HoldoutEvaluator")
    assert hasattr(mod, "HoldoutSample")


def test_import_drift_detector() -> None:
    mod = importlib.import_module("ml.evaluation.drift_detector")
    assert hasattr(mod, "DriftDetector")
    assert hasattr(mod, "DriftReport")
    assert hasattr(mod, "StaleSegment")


def test_import_simulation_errors() -> None:
    mod = importlib.import_module("api.services.simulation_errors")
    assert hasattr(mod, "ERROR_TAXONOMY")
    assert hasattr(mod, "SimulationError")


def test_import_metrics() -> None:
    mod = importlib.import_module("api.services.metrics")
    assert hasattr(mod, "SIMULATION_LATENCY")
    assert hasattr(mod, "SIMULATION_ERRORS")
    assert hasattr(mod, "QUEUE_DEPTH")


def test_import_rate_limiter() -> None:
    mod = importlib.import_module("api.services.rate_limiter")
    assert hasattr(mod, "check_simulation_rate_limit")


def test_import_queue() -> None:
    mod = importlib.import_module("api.services.queue")
    assert hasattr(mod, "get_arq_pool")
    assert hasattr(mod, "close_arq_pool")


def test_import_worker() -> None:
    mod = importlib.import_module("api.workers.simulation_worker")
    assert hasattr(mod, "run_simulation_job")
    assert hasattr(mod, "WorkerSettings")
    assert mod.WorkerSettings.max_jobs == 5


# ── Instantiation smoke tests ──────────────────────────────────────────────────

def test_persona_context_builder_instantiates() -> None:
    from ml.synthetic_data.persona_context_builder import PersonaContextBuilder
    builder = PersonaContextBuilder()
    assert hasattr(builder, "build_system_prompt")


def test_conversion_scorer_instantiates() -> None:
    from ml.synthetic_data.conversion_scorer import ConversionScorer
    scorer = ConversionScorer()
    assert hasattr(scorer, "score")
    assert hasattr(scorer, "score_batch")


def test_holdout_evaluator_instantiates() -> None:
    from ml.evaluation.holdout_evaluator import HoldoutEvaluator
    ev = HoldoutEvaluator()
    assert ev.MIN_SAMPLES_FOR_AUC == 10


def test_drift_detector_instantiates() -> None:
    from ml.evaluation.drift_detector import DriftDetector
    det = DriftDetector(threshold_days=7)
    assert det.threshold_days == 7


def test_stimulus_models_instantiate() -> None:
    from ml.synthetic_data.stimulus_schema import (
        AdCopyStimulus,
        PriceChangeStimulus,
        PromoStimulus,
    )
    ad = AdCopyStimulus(headline="H", body_copy="B", cta="Buy")
    assert ad.type == "ad_copy"

    pc = PriceChangeStimulus(product_name="P", original_price=100, new_price=80)
    assert pc.is_discount is True

    promo = PromoStimulus(promo_code="X", discount_value=10, discount_type="percent")
    assert promo.discount_type == "percent"


def test_synthetic_response_instantiates() -> None:
    from ml.synthetic_data.persona_inference import SyntheticResponse
    r = SyntheticResponse(
        segment_id="s",
        stimulus_id="t",
        verbatim_response="Test.",
        sentiment="neutral",
        likelihood_to_convert=0.5,
    )
    assert r.likelihood_to_convert == 0.5


def test_error_taxonomy_completeness() -> None:
    from api.services.simulation_errors import ERROR_TAXONOMY
    # All definitions must have non-empty error_code and valid HTTP status
    for key, defn in ERROR_TAXONOMY.items():
        assert defn.error_code == key, f"Key mismatch: {key} vs {defn.error_code}"
        assert defn.http_status in (200, 201, 202, 400, 404, 409, 422, 429, 500, 502, 503, 504)
        assert len(defn.description) > 20, f"{key} description too short"


def test_worker_settings_concurrency() -> None:
    """S6-01: verify max_jobs cap is enforced at the class level."""
    from api.workers.simulation_worker import WorkerSettings
    assert WorkerSettings.max_jobs == 5
    assert WorkerSettings.job_timeout == 120
