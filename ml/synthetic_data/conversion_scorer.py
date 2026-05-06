"""Conversion scorer — adjusts raw likelihood_to_convert with sentiment signal.

The LLM already provides a calibrated likelihood_to_convert (0–1).  This scorer
applies a small sentiment-driven nudge to account for cases where the model's
tone in verbatim_response diverges from the numeric score.

Design rationale:
  - Positive sentiment → nudge score upward  (+0.05)
  - Negative sentiment → nudge score downward (-0.08, asymmetric because
    expressed negativity is a stronger conversion signal than positivity)
  - Neutral sentiment  → no adjustment
  - Final score is clamped to [0, 1].

The nudge values are intentionally small so the LLM's own calibration dominates.
"""

from __future__ import annotations

import logging

from ml.synthetic_data.persona_inference import SyntheticResponse

logger = logging.getLogger(__name__)

_SENTIMENT_NUDGE: dict[str, float] = {
    "positive": +0.05,
    "neutral":   0.00,
    "negative": -0.08,
}


class ConversionScorer:
    """Computes a final conversion probability from a SyntheticResponse.

    The scorer is stateless — instantiate once and reuse freely.
    """

    def score(self, response: SyntheticResponse) -> float:
        """Apply sentiment adjustment to likelihood_to_convert.

        Args:
            response: A SyntheticResponse produced by PersonaInferenceService.

        Returns:
            Adjusted conversion probability in [0.0, 1.0].
        """
        nudge = _SENTIMENT_NUDGE.get(response.sentiment, 0.0)
        adjusted = response.likelihood_to_convert + nudge
        final = max(0.0, min(1.0, adjusted))

        if nudge != 0.0:
            logger.debug(
                "ConversionScorer: base=%.3f sentiment=%s nudge=%+.2f → final=%.3f",
                response.likelihood_to_convert, response.sentiment, nudge, final,
            )

        return final

    def score_batch(self, responses: list[SyntheticResponse]) -> list[float]:
        """Score a list of responses.

        Returns scores in the same order as the input list.
        """
        return [self.score(r) for r in responses]
