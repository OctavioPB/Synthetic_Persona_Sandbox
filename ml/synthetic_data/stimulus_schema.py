"""Stimulus schemas — the marketing inputs sent to a synthetic persona.

Three types are supported:
  - AdCopyStimulus: headline + body + CTA (most common)
  - PriceChangeStimulus: before/after pricing
  - PromoStimulus: discount code or flash offer

The discriminator field `type` drives FastAPI's discriminated-union validation
and is stored verbatim in `simulation_runs.stimulus` JSONB.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ── Type discriminator ─────────────────────────────────────────────────────────


class StimulusType:
    AD_COPY = "ad_copy"
    PRICE_CHANGE = "price_change"
    PROMO = "promo"


# What a stimulus is trying to get the persona to do. It sets how the persona
# prompt describes "likelihood_to_convert"; purchase is the original behaviour.
Goal = Literal["purchase", "click", "signup"]

# Where the persona meets the stimulus, e.g. "news headline" or "email subject
# line". Optional free text, one line. On Upworthy headlines, naming the medium
# was the main difference between the best and the shipped click wording.
Medium = Annotated[str, Field(min_length=1, max_length=60, pattern=r"^[^\r\n]+$")]
_MEDIUM_DESCRIPTION = "Where the stimulus is seen, e.g. 'news headline' or 'email subject line'"


def _blank_to_none(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


# ── Concrete stimulus models ───────────────────────────────────────────────────


class AdCopyStimulus(BaseModel):
    """A creative ad — headline, body copy, and call-to-action."""

    type: Literal["ad_copy"] = "ad_copy"
    stimulus_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    headline: str = Field(min_length=1, max_length=200)
    body_copy: str = Field(min_length=1, max_length=1000)
    cta: str = Field(min_length=1, max_length=100, description="Call-to-action text")
    product_name: str | None = None
    image_description: str | None = Field(
        default=None,
        description="Text description of the ad visual for context",
    )
    goal: Goal = Field(
        default="purchase",
        description="What counts as success: purchase (default), click or signup",
    )
    medium: Medium | None = Field(default=None, description=_MEDIUM_DESCRIPTION)
    created_at: datetime = Field(default_factory=_utcnow)

    _clean_medium = field_validator("medium", mode="before")(_blank_to_none)


class PriceChangeStimulus(BaseModel):
    """A price reduction or increase announcement."""

    type: Literal["price_change"] = "price_change"
    stimulus_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_name: str
    original_price: float = Field(gt=0)
    new_price: float = Field(gt=0)
    currency: str = "USD"
    goal: Goal = Field(
        default="purchase",
        description="What counts as success: purchase (default), click or signup",
    )
    medium: Medium | None = Field(default=None, description=_MEDIUM_DESCRIPTION)
    created_at: datetime = Field(default_factory=_utcnow)

    _clean_medium = field_validator("medium", mode="before")(_blank_to_none)

    @model_validator(mode="after")
    def check_prices_differ(self) -> PriceChangeStimulus:
        if self.new_price == self.original_price:
            raise ValueError("new_price and original_price must differ")
        return self

    @property
    def discount_pct(self) -> float:
        """Positive = price drop. Negative = price increase."""
        return (self.original_price - self.new_price) / self.original_price * 100

    @property
    def is_discount(self) -> bool:
        return self.new_price < self.original_price


class PromoStimulus(BaseModel):
    """A promotional offer — percentage or fixed discount."""

    type: Literal["promo"] = "promo"
    stimulus_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    promo_code: str
    discount_value: float = Field(gt=0)
    discount_type: Literal["percent", "fixed"]
    minimum_purchase: float | None = Field(default=None, ge=0)
    expiry_days: int | None = Field(default=None, ge=1)
    applicable_categories: list[str] = Field(default_factory=list)
    goal: Goal = Field(
        default="purchase",
        description="What counts as success: purchase (default), click or signup",
    )
    medium: Medium | None = Field(default=None, description=_MEDIUM_DESCRIPTION)
    created_at: datetime = Field(default_factory=_utcnow)

    _clean_medium = field_validator("medium", mode="before")(_blank_to_none)

    @model_validator(mode="after")
    def check_percent_range(self) -> PromoStimulus:
        if self.discount_type == "percent" and self.discount_value > 100:
            raise ValueError("percent discount_value cannot exceed 100")
        return self


# ── Union type used across the codebase ───────────────────────────────────────

AnyStimulus = Annotated[
    AdCopyStimulus | PriceChangeStimulus | PromoStimulus,
    Field(discriminator="type"),
]


# ── Text formatter for LLM prompts ────────────────────────────────────────────


def format_stimulus_prompt(stimulus: AdCopyStimulus | PriceChangeStimulus | PromoStimulus) -> str:
    """Convert a stimulus into a human-readable prompt block for the LLM.

    Args:
        stimulus: Any of the three supported stimulus types.

    Returns:
        A formatted multi-line string describing the stimulus.
    """
    if isinstance(stimulus, AdCopyStimulus):
        lines = [
            "## Marketing Stimulus — Ad Copy",
            f"**Headline:** {stimulus.headline}",
            f"**Body:** {stimulus.body_copy}",
            f"**Call to Action:** {stimulus.cta}",
        ]
        if stimulus.product_name:
            lines.append(f"**Product:** {stimulus.product_name}")
        if stimulus.image_description:
            lines.append(f"**Visual:** {stimulus.image_description}")
        return "\n".join(lines)

    if isinstance(stimulus, PriceChangeStimulus):
        direction = "discount" if stimulus.is_discount else "price increase"
        return "\n".join(
            [
                "## Marketing Stimulus — Price Change",
                f"**Product:** {stimulus.product_name}",
                f"**Original price:** {stimulus.currency}{stimulus.original_price:.2f}",
                f"**New price:** {stimulus.currency}{stimulus.new_price:.2f}",
                f"**Change:** {abs(stimulus.discount_pct):.1f}% {direction}",
            ]
        )

    if isinstance(stimulus, PromoStimulus):
        value_str = (
            f"{stimulus.discount_value:.0f}% off"
            if stimulus.discount_type == "percent"
            else f"${stimulus.discount_value:.2f} off"
        )
        lines = [
            "## Marketing Stimulus — Promotional Offer",
            f"**Promo code:** {stimulus.promo_code}",
            f"**Discount:** {value_str}",
        ]
        if stimulus.minimum_purchase:
            lines.append(f"**Minimum purchase:** ${stimulus.minimum_purchase:.2f}")
        if stimulus.expiry_days:
            lines.append(f"**Expires in:** {stimulus.expiry_days} days")
        if stimulus.applicable_categories:
            lines.append(f"**Valid for:** {', '.join(stimulus.applicable_categories)}")
        return "\n".join(lines)

    raise TypeError(f"Unknown stimulus type: {type(stimulus)}")
