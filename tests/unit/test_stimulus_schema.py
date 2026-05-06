"""Unit tests for ml/synthetic_data/stimulus_schema.py."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from ml.synthetic_data.stimulus_schema import (
    AdCopyStimulus,
    AnyStimulus,
    PriceChangeStimulus,
    PromoStimulus,
    format_stimulus_prompt,
)


# ── AdCopyStimulus ─────────────────────────────────────────────────────────────

def test_ad_copy_stimulus_defaults() -> None:
    s = AdCopyStimulus(headline="H", body_copy="B", cta="Buy now")
    assert s.type == "ad_copy"
    assert s.stimulus_id != ""
    assert s.product_name is None


def test_ad_copy_stimulus_requires_headline() -> None:
    with pytest.raises(ValidationError):
        AdCopyStimulus(headline="", body_copy="B", cta="Buy")


def test_ad_copy_format_includes_all_fields() -> None:
    s = AdCopyStimulus(
        headline="Amazing Deal",
        body_copy="This is the body.",
        cta="Shop Now",
        product_name="Widget",
        image_description="A red widget on white background",
    )
    prompt = format_stimulus_prompt(s)
    assert "Amazing Deal" in prompt
    assert "This is the body." in prompt
    assert "Shop Now" in prompt
    assert "Widget" in prompt
    assert "A red widget on white background" in prompt


def test_ad_copy_format_without_optional_fields() -> None:
    s = AdCopyStimulus(headline="H", body_copy="B", cta="Buy")
    prompt = format_stimulus_prompt(s)
    assert "Product" not in prompt
    assert "Visual" not in prompt


# ── PriceChangeStimulus ────────────────────────────────────────────────────────

def test_price_change_discount_pct() -> None:
    s = PriceChangeStimulus(product_name="Widget", original_price=100.0, new_price=80.0)
    assert s.discount_pct == pytest.approx(20.0)
    assert s.is_discount is True


def test_price_increase_negative_pct() -> None:
    s = PriceChangeStimulus(product_name="Widget", original_price=80.0, new_price=100.0)
    assert s.discount_pct == pytest.approx(-25.0)
    assert s.is_discount is False


def test_price_change_same_price_invalid() -> None:
    with pytest.raises(ValidationError):
        PriceChangeStimulus(product_name="Widget", original_price=50.0, new_price=50.0)


def test_price_change_format_shows_direction() -> None:
    s = PriceChangeStimulus(product_name="Widget", original_price=100.0, new_price=75.0)
    prompt = format_stimulus_prompt(s)
    assert "discount" in prompt.lower()
    assert "Widget" in prompt
    assert "25.0%" in prompt


# ── PromoStimulus ──────────────────────────────────────────────────────────────

def test_promo_percent_valid() -> None:
    s = PromoStimulus(promo_code="SAVE20", discount_value=20.0, discount_type="percent")
    assert s.discount_value == 20.0


def test_promo_percent_exceeds_100_invalid() -> None:
    with pytest.raises(ValidationError):
        PromoStimulus(promo_code="X", discount_value=110.0, discount_type="percent")


def test_promo_fixed_over_100_allowed() -> None:
    s = PromoStimulus(promo_code="BIGDEAL", discount_value=150.0, discount_type="fixed")
    assert s.discount_value == 150.0


def test_promo_format_includes_minimum() -> None:
    s = PromoStimulus(
        promo_code="VIP50",
        discount_value=50.0,
        discount_type="percent",
        minimum_purchase=100.0,
        expiry_days=7,
        applicable_categories=["Electronics"],
    )
    prompt = format_stimulus_prompt(s)
    assert "VIP50" in prompt
    assert "50%" in prompt
    assert "$100.00" in prompt
    assert "7 days" in prompt
    assert "Electronics" in prompt


# ── Discriminated union ────────────────────────────────────────────────────────

def test_any_stimulus_dispatches_ad_copy() -> None:
    adapter: TypeAdapter[AnyStimulus] = TypeAdapter(AnyStimulus)  # type: ignore[arg-type]
    parsed = adapter.validate_python({"type": "ad_copy", "headline": "H", "body_copy": "B", "cta": "Buy"})
    assert isinstance(parsed, AdCopyStimulus)


def test_any_stimulus_dispatches_promo() -> None:
    adapter: TypeAdapter[AnyStimulus] = TypeAdapter(AnyStimulus)  # type: ignore[arg-type]
    parsed = adapter.validate_python({"type": "promo", "promo_code": "X", "discount_value": 10.0, "discount_type": "percent"})
    assert isinstance(parsed, PromoStimulus)


def test_any_stimulus_unknown_type_invalid() -> None:
    adapter: TypeAdapter[AnyStimulus] = TypeAdapter(AnyStimulus)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "banner", "headline": "H"})


def test_format_stimulus_unknown_type_raises() -> None:
    with pytest.raises(TypeError):
        format_stimulus_prompt("not a stimulus")  # type: ignore[arg-type]
