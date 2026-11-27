"""Persona context builder — constructs the LLM system prompt for a segment.

The system prompt encodes the segment's behavioral profile so Claude can
simulate how that persona would react to a marketing stimulus. The prompt
is designed to be stable across multiple stimulus evaluations for the
same segment, which means Anthropic's prompt caching applies after the
first call (90% cost reduction on input tokens).
"""

from __future__ import annotations

import logging
from typing import Any

from ml.synthetic_data.stimulus_schema import Goal

logger = logging.getLogger(__name__)

_RESPONSE_SCHEMA = """\
{
  "verbatim_response": "A 2-3 sentence first-person reaction as this persona",
  "sentiment": "positive" | "neutral" | "negative",
  "likelihood_to_convert": <float 0.0-1.0>,
  "key_factors": ["<factor 1>", "<factor 2>"]
}"""

_SYSTEM_TEMPLATE = """\
You are a synthetic customer persona representing the "{name}" customer segment.
Your purpose is to simulate how a real customer in this segment would react to
marketing stimuli in order to help marketers test campaign effectiveness.

## Demographic Profile
{demographics}

## Behavioral Characteristics
These statistics are derived from {user_count} real users in this segment:
{behavioral_stats}

## Category Interests
{category_interests}

## Response Instructions
When presented with a marketing stimulus, react authentically as this persona.{goal_line}{medium_line}

Your response MUST be a single valid JSON object with exactly this structure:
{schema}

Guidelines for calibration:
- "likelihood_to_convert" of 0.9-1.0 = {top}
- "likelihood_to_convert" of 0.6-0.8 = {high}
- "likelihood_to_convert" of 0.3-0.5 = somewhat interested but unconvinced
- "likelihood_to_convert" of 0.0-0.2 = {low}
- Calibrate against the persona's behavioral profile: {profile}
- {skeptic}
- Match "sentiment" with the tone of "verbatim_response".
- List 1-2 specific factors that most influenced your reaction in "key_factors".

Return ONLY the JSON object — no markdown fencing, no preamble, no explanation.\
"""


# Wording per goal. "purchase" reproduces the original prompt byte for byte.
# Why it matters: on Upworthy headline tests, where clicks are the real outcome,
# the purchase wording picked the winner less often than a click rewording
# (Qwen 3 4B, 200 tests: 27.8% vs 36.0%). That rewording was close to, not the
# same as, the "click" text here; scripts/evaluate_upworthy.py measures this one
# as the goal_click arm.
_GOAL_WORDING: dict[str, dict[str, str]] = {
    "purchase": {
        "goal_line": "",
        "top": "extremely likely to purchase immediately",
        "high": "interested, may convert with follow-up",
        "low": "unlikely to convert, may disengage",
        "profile": "a high-purchase-frequency,\n  high-basket-size persona responds better "
        "to premium/quality messaging.",
        "skeptic": "A low-conversion-rate persona is naturally skeptical; require compelling value.",
    },
    "click": {
        "goal_line": '\nThe goal is a click: "likelihood_to_convert" is the probability that you '
        "click the stimulus to see more.",
        "top": "extremely likely to click right away",
        "high": "interested, likely to click",
        "low": "unlikely to click, would scroll past",
        "profile": "react as a typical member\n  of this segment would.",
        "skeptic": "People skip content that feels generic; require a compelling reason to click.",
    },
    "signup": {
        "goal_line": '\nThe goal is a sign-up: "likelihood_to_convert" is the probability that '
        "you sign up (for example a newsletter, an account or a trial).",
        "top": "extremely likely to sign up right away",
        "high": "interested, likely to sign up",
        "low": "unlikely to sign up, would ignore it",
        "profile": "react as a typical member\n  of this segment would.",
        "skeptic": "People avoid sign-ups that ask a lot for little; require a clear benefit.",
    },
}


class PersonaContextBuilder:
    """Builds cacheable system prompts from segment metadata and feature stats.

    The same builder instance can be reused for multiple segments.
    """

    def build_system_prompt(
        self,
        segment_name: str,
        definition: dict[str, Any],
        feature_stats: dict[str, float] | None = None,
        user_count: int = 0,
        goal: Goal = "purchase",
        medium: str | None = None,
    ) -> str:
        """Construct the full system prompt for a persona.

        Args:
            segment_name:  Human-readable segment name.
            definition:    SegmentDefinition as a dict (from segment.definition).
            feature_stats: Aggregate stats from SegmentFeatureMatrix.aggregate_stats().
                           If None, behavioral section uses generic language.
            user_count:    Number of users the stats were computed from.
            goal:          What counts as success for the stimulus; sets how the
                           calibration scale is described.
            medium:        Where the stimulus is seen (e.g. "news headline"). None
                           leaves the prompt exactly as without it.

        Returns:
            A multi-paragraph system prompt string, ready for the Claude API.
        """
        demographics = self._format_demographics(definition)
        behavioral_stats = self._format_behavioral(feature_stats, user_count)
        category_interests = self._format_categories(definition.get("category_affinities", []))

        prompt = _SYSTEM_TEMPLATE.format(
            name=segment_name,
            demographics=demographics,
            user_count=user_count if user_count > 0 else "an unknown number of",
            behavioral_stats=behavioral_stats,
            category_interests=category_interests,
            schema=_RESPONSE_SCHEMA,
            medium_line=f"\nThe stimulus is shown to you as: {medium}." if medium else "",
            **_GOAL_WORDING[goal],
        )
        logger.debug(
            "Built system prompt for '%s' (~%d tokens).",
            segment_name,
            len(prompt) // 4,
        )
        return prompt

    # ── Private formatters ─────────────────────────────────────────────────────

    @staticmethod
    def _format_demographics(definition: dict[str, Any]) -> str:
        lines = []
        age_range = definition.get("age_range")
        geo = definition.get("geo")
        window = definition.get("purchase_history_days", 90)

        if age_range:
            lines.append(
                f"- Age range: {age_range.get('min_age', '?')}–{age_range.get('max_age', '?')} years"
            )
        if geo:
            location = ", ".join(
                filter(None, [geo.get("city"), geo.get("region"), geo.get("country")])
            )
            if location:
                lines.append(f"- Location: {location}")
        if not lines:
            lines.append("- No specific demographic filters defined")
        lines.append(f"- Behavioral data window: last {window} days")
        return "\n".join(lines)

    @staticmethod
    def _format_behavioral(stats: dict[str, float] | None, user_count: int) -> str:
        if not stats:
            return "- Behavioral data not yet available (segment needs training)"

        freq = stats.get("purchase_frequency_mean", 0)
        bask = stats.get("avg_basket_size_mean", 0)
        sess = stats.get("session_depth_mean", 0)
        conv = stats.get("conversion_rate_mean", 0)
        div = stats.get("category_diversity_mean", 0)
        rec = stats.get("recency_days_mean", 0)

        return "\n".join(
            [
                f"- Purchase frequency: {freq:.3f} purchases/day ({freq * 30:.1f}/month)",
                f"- Average basket size: ${bask:.2f}",
                f"- Session depth: {sess:.1f} pages per visit",
                f"- Conversion rate: {conv:.1%} of sessions lead to purchase",
                f"- Category diversity: explores {div:.1f} different categories on average",
                f"- Recency: last active {rec:.0f} days ago on average",
            ]
        )

    @staticmethod
    def _format_categories(categories: list[str]) -> str:
        if not categories:
            return "No specific category preference — general shopper."
        return f"Strong affinity for: {', '.join(categories)}."
