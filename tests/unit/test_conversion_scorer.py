"""Unit tests for ml/synthetic_data/conversion_scorer.py."""

from __future__ import annotations

import pytest

from ml.synthetic_data.conversion_scorer import ConversionScorer
from ml.synthetic_data.persona_inference import SyntheticResponse


def _make_response(
    sentiment: str,
    likelihood: float,
    segment_id: str = "seg-1",
    stimulus_id: str = "stim-1",
) -> SyntheticResponse:
    return SyntheticResponse(
        segment_id=segment_id,
        stimulus_id=stimulus_id,
        verbatim_response="Test response.",
        sentiment=sentiment,
        likelihood_to_convert=likelihood,
        key_factors=["price"],
    )


@pytest.fixture()
def scorer() -> ConversionScorer:
    return ConversionScorer()


# ── Sentiment nudge behavior ───────────────────────────────────────────────────

def test_positive_nudge_increases_score(scorer) -> None:
    response = _make_response("positive", 0.6)
    result = scorer.score(response)
    assert result > 0.6


def test_negative_nudge_decreases_score(scorer) -> None:
    response = _make_response("negative", 0.6)
    result = scorer.score(response)
    assert result < 0.6


def test_neutral_no_change(scorer) -> None:
    response = _make_response("neutral", 0.55)
    result = scorer.score(response)
    assert result == pytest.approx(0.55)


def test_positive_nudge_value(scorer) -> None:
    response = _make_response("positive", 0.5)
    result = scorer.score(response)
    assert result == pytest.approx(0.55)


def test_negative_nudge_value(scorer) -> None:
    response = _make_response("negative", 0.5)
    result = scorer.score(response)
    assert result == pytest.approx(0.42)


# ── Clamping behavior ──────────────────────────────────────────────────────────

def test_clamp_above_1(scorer) -> None:
    response = _make_response("positive", 0.99)
    result = scorer.score(response)
    assert result == pytest.approx(1.0)


def test_clamp_below_0(scorer) -> None:
    response = _make_response("negative", 0.03)
    result = scorer.score(response)
    assert result == pytest.approx(0.0)


def test_output_always_in_range(scorer) -> None:
    for sentiment in ("positive", "neutral", "negative"):
        for ltc in (0.0, 0.1, 0.5, 0.9, 1.0):
            result = scorer.score(_make_response(sentiment, ltc))
            assert 0.0 <= result <= 1.0


# ── Batch scoring ──────────────────────────────────────────────────────────────

def test_score_batch_preserves_order(scorer) -> None:
    responses = [
        _make_response("positive", 0.5, stimulus_id="s1"),
        _make_response("negative", 0.5, stimulus_id="s2"),
        _make_response("neutral",  0.5, stimulus_id="s3"),
    ]
    scores = scorer.score_batch(responses)
    assert len(scores) == 3
    assert scores[0] > scores[2] > scores[1]


def test_score_batch_empty_returns_empty(scorer) -> None:
    assert scorer.score_batch([]) == []
