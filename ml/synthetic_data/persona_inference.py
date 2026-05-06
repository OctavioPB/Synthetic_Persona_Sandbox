"""Persona inference service — generates a synthetic persona response to a stimulus.

Given a segment's metadata and a marketing stimulus, this service:
  1. Builds a cacheable system prompt via PersonaContextBuilder.
  2. Formats the stimulus into a user-turn message via format_stimulus_prompt.
  3. Calls Claude through CachedClaudeClient.
  4. Parses and validates the JSON response.

The resulting SyntheticResponse is the atomic output of a simulation run.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from ml.synthetic_data.claude_client import CachedClaudeClient
from ml.synthetic_data.persona_context_builder import PersonaContextBuilder
from ml.synthetic_data.stimulus_schema import (
    AdCopyStimulus,
    AnyStimulus,
    PriceChangeStimulus,
    PromoStimulus,
    format_stimulus_prompt,
)

logger = logging.getLogger(__name__)

_VALID_SENTIMENTS = {"positive", "neutral", "negative"}


@dataclass
class SyntheticResponse:
    """Parsed output from a single persona-stimulus interaction."""

    segment_id: str
    stimulus_id: str
    verbatim_response: str
    sentiment: str                          # "positive" | "neutral" | "negative"
    likelihood_to_convert: float            # 0.0–1.0
    key_factors: list[str] = field(default_factory=list)
    raw_text: str = ""                      # unparsed LLM output for debugging
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0

    def __post_init__(self) -> None:
        if self.sentiment not in _VALID_SENTIMENTS:
            raise ValueError(f"Invalid sentiment '{self.sentiment}'. Must be one of {_VALID_SENTIMENTS}.")
        if not 0.0 <= self.likelihood_to_convert <= 1.0:
            raise ValueError(
                f"likelihood_to_convert must be in [0, 1], got {self.likelihood_to_convert}."
            )


class PersonaInferenceService:
    """Runs a persona against a marketing stimulus and returns a SyntheticResponse.

    Args:
        client:   CachedClaudeClient instance. Created automatically if not provided.
        builder:  PersonaContextBuilder instance. Created automatically if not provided.
        model:    Claude model ID override. Defaults to the client's DEFAULT_MODEL.
        temperature: Sampling temperature. Lower = more deterministic persona.
    """

    def __init__(
        self,
        client: CachedClaudeClient | None = None,
        builder: PersonaContextBuilder | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> None:
        self._client  = client or CachedClaudeClient()
        self._builder = builder or PersonaContextBuilder()
        self._model   = model
        self._temperature = temperature

    def generate(
        self,
        segment_id: str,
        segment_name: str,
        definition: dict[str, Any],
        stimulus: AdCopyStimulus | PriceChangeStimulus | PromoStimulus,
        feature_stats: dict[str, float] | None = None,
        user_count: int = 0,
        model: str | None = None,
        temperature: float | None = None,
    ) -> SyntheticResponse:
        """Generate a synthetic persona response to a marketing stimulus.

        Args:
            segment_id:    UUID string of the segment.
            segment_name:  Human-readable segment name.
            definition:    SegmentDefinition dict (age_range, geo, category_affinities, etc.).
            stimulus:      The marketing input to evaluate.
            feature_stats: Aggregate behavioral stats from SegmentFeatureMatrix.
            user_count:    Number of real users the stats represent.
            model:         Per-call model override. Falls back to instance default.
            temperature:   Per-call temperature override. Falls back to instance default.

        Returns:
            A fully populated SyntheticResponse.

        Raises:
            ValueError: If the LLM returns invalid JSON or an out-of-range value.
            anthropic.APIError: On unrecoverable API failures (not cached).
        """
        system_prompt = self._builder.build_system_prompt(
            segment_name=segment_name,
            definition=definition,
            feature_stats=feature_stats,
            user_count=user_count,
        )
        user_message = format_stimulus_prompt(stimulus)

        effective_model = model or self._model
        effective_temp  = temperature if temperature is not None else self._temperature

        kwargs: dict[str, Any] = {"temperature": effective_temp}
        if effective_model:
            kwargs["model"] = effective_model

        result = self._client.complete(
            system=system_prompt,
            user_message=user_message,
            **kwargs,
        )

        parsed = self._parse_response(result["text"], stimulus.stimulus_id)

        return SyntheticResponse(
            segment_id=segment_id,
            stimulus_id=stimulus.stimulus_id,
            verbatim_response=parsed["verbatim_response"],
            sentiment=parsed["sentiment"],
            likelihood_to_convert=float(parsed["likelihood_to_convert"]),
            key_factors=list(parsed.get("key_factors", [])),
            raw_text=result["text"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            latency_ms=result["latency_ms"],
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_response(text: str, stimulus_id: str) -> dict[str, Any]:
        """Parse and validate the LLM JSON output.

        Strips accidental markdown fences before attempting JSON decode.
        """
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Strip ```json ... ``` fences the model occasionally adds
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data: dict[str, Any] = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned non-JSON for stimulus {stimulus_id}: {exc}\nRaw: {text[:300]}"
            ) from exc

        required = {"verbatim_response", "sentiment", "likelihood_to_convert"}
        missing = required - data.keys()
        if missing:
            raise ValueError(
                f"LLM response missing required keys {missing} for stimulus {stimulus_id}."
            )

        ltc = data["likelihood_to_convert"]
        if not isinstance(ltc, (int, float)):
            raise ValueError(
                f"likelihood_to_convert must be numeric, got {type(ltc).__name__}."
            )
        data["likelihood_to_convert"] = max(0.0, min(1.0, float(ltc)))

        sentiment = data["sentiment"]
        if sentiment not in _VALID_SENTIMENTS:
            logger.warning(
                "Unexpected sentiment '%s' for stimulus %s — coercing to 'neutral'.",
                sentiment, stimulus_id,
            )
            data["sentiment"] = "neutral"

        return data
