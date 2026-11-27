"""The stimulus goal (purchase, click, signup) and how it reaches the persona prompt."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from ml.synthetic_data.persona_context_builder import PersonaContextBuilder
from ml.synthetic_data.persona_inference import PersonaInferenceService
from ml.synthetic_data.stimulus_schema import AdCopyStimulus, AnyStimulus

DEFINITION = {"geo": {"country": "Spain"}, "category_affinities": ["Books"]}


def _prompt(**kwargs: Any) -> str:
    return PersonaContextBuilder().build_system_prompt("Seg", DEFINITION, None, 0, **kwargs)


def test_goal_defaults_to_purchase_for_every_stimulus_type() -> None:
    adapter: TypeAdapter[Any] = TypeAdapter(AnyStimulus)
    payloads = [
        {"type": "ad_copy", "headline": "H", "body_copy": "B", "cta": "Go"},
        {"type": "price_change", "product_name": "P", "original_price": 10, "new_price": 8},
        {"type": "promo", "promo_code": "X", "discount_value": 5, "discount_type": "fixed"},
    ]
    assert [adapter.validate_python(p).goal for p in payloads] == ["purchase"] * 3


def test_unknown_goal_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AdCopyStimulus(headline="H", body_copy="B", cta="Go", goal="share")  # type: ignore[arg-type]


def test_default_prompt_is_unchanged_by_the_goal_parameter() -> None:
    assert _prompt() == _prompt(goal="purchase")
    assert "extremely likely to purchase immediately" in _prompt()
    assert "The goal is" not in _prompt()


@pytest.mark.parametrize(
    ("goal", "expected"),
    [("click", "likely to click"), ("signup", "likely to sign up")],
)
def test_other_goals_replace_the_purchase_wording(goal: str, expected: str) -> None:
    prompt = _prompt(goal=goal)
    assert expected in prompt
    assert "purchase immediately" not in prompt
    assert "basket-size" not in prompt


class _RecordingClient:
    def __init__(self) -> None:
        self.system = ""

    def complete(self, system: str, user_message: str, **_: Any) -> dict[str, Any]:
        self.system = system
        text = '{"verbatim_response": "ok", "sentiment": "neutral", "likelihood_to_convert": 0.5}'
        return {"text": text, "input_tokens": 1, "output_tokens": 1, "latency_ms": 1.0}


def test_inference_passes_the_stimulus_goal_to_the_prompt() -> None:
    client = _RecordingClient()
    service = PersonaInferenceService(client=client)  # type: ignore[arg-type]
    stimulus = AdCopyStimulus(headline="H", body_copy="B", cta="Go", goal="signup")
    service.generate("id", "Seg", DEFINITION, stimulus)
    assert "The goal is a sign-up" in client.system
