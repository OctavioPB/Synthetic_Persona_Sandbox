"""Unit tests for ml/synthetic_data/persona_context_builder.py."""

from __future__ import annotations

import pytest

from ml.synthetic_data.persona_context_builder import PersonaContextBuilder


@pytest.fixture()
def builder() -> PersonaContextBuilder:
    return PersonaContextBuilder()


@pytest.fixture()
def full_definition() -> dict:
    return {
        "age_range": {"min_age": 18, "max_age": 24},
        "geo": {"city": "Madrid", "region": "Community of Madrid", "country": "Spain"},
        "category_affinities": ["Electronics", "Fashion"],
        "purchase_history_days": 90,
    }


@pytest.fixture()
def feature_stats() -> dict:
    return {
        "purchase_frequency_mean": 0.12,
        "avg_basket_size_mean": 45.50,
        "session_depth_mean": 4.3,
        "conversion_rate_mean": 0.08,
        "category_diversity_mean": 3.2,
        "recency_days_mean": 5.0,
    }


# ── Core structure ─────────────────────────────────────────────────────────────

def test_build_system_prompt_returns_string(builder, full_definition, feature_stats) -> None:
    prompt = builder.build_system_prompt(
        segment_name="Gen Z Madrid",
        definition=full_definition,
        feature_stats=feature_stats,
        user_count=1200,
    )
    assert isinstance(prompt, str)
    assert len(prompt) > 100


def test_prompt_contains_segment_name(builder, full_definition, feature_stats) -> None:
    prompt = builder.build_system_prompt("Gen Z Madrid", full_definition, feature_stats, 1200)
    assert "Gen Z Madrid" in prompt


def test_prompt_contains_demographics(builder, full_definition, feature_stats) -> None:
    prompt = builder.build_system_prompt("Seg", full_definition, feature_stats, 0)
    assert "18" in prompt
    assert "24" in prompt
    assert "Madrid" in prompt


def test_prompt_contains_behavioral_stats(builder, full_definition, feature_stats) -> None:
    prompt = builder.build_system_prompt("Seg", full_definition, feature_stats, 500)
    assert "0.120" in prompt    # purchase_frequency formatted to 3 decimal places
    assert "$45.50" in prompt
    assert "8.0%" in prompt     # conversion_rate as percentage


def test_prompt_contains_categories(builder, full_definition, feature_stats) -> None:
    prompt = builder.build_system_prompt("Seg", full_definition, feature_stats, 100)
    assert "Electronics" in prompt
    assert "Fashion" in prompt


def test_prompt_contains_json_schema(builder, full_definition, feature_stats) -> None:
    prompt = builder.build_system_prompt("Seg", full_definition, feature_stats, 100)
    assert "verbatim_response" in prompt
    assert "likelihood_to_convert" in prompt
    assert "key_factors" in prompt


# ── Edge cases ─────────────────────────────────────────────────────────────────

def test_no_feature_stats_returns_fallback_text(builder, full_definition) -> None:
    prompt = builder.build_system_prompt("Seg", full_definition, None, 0)
    assert "not yet available" in prompt


def test_no_category_affinities_returns_generic(builder) -> None:
    definition = {"purchase_history_days": 30}
    prompt = builder.build_system_prompt("Seg", definition, None, 0)
    assert "general shopper" in prompt.lower()


def test_no_demographic_filters_returns_no_specific(builder) -> None:
    prompt = builder.build_system_prompt("Seg", {}, None, 0)
    assert "No specific demographic" in prompt


def test_unknown_user_count_uses_readable_fallback(builder, full_definition, feature_stats) -> None:
    prompt = builder.build_system_prompt("Seg", full_definition, feature_stats, 0)
    assert "unknown number" in prompt


def test_geo_partial_city_only(builder) -> None:
    definition = {
        "geo": {"city": "Barcelona"},
        "purchase_history_days": 60,
    }
    prompt = builder.build_system_prompt("Seg", definition, None, 0)
    assert "Barcelona" in prompt


def test_reusable_across_segments(builder, feature_stats) -> None:
    defn_a = {"category_affinities": ["Sports"]}
    defn_b = {"category_affinities": ["Beauty"]}
    prompt_a = builder.build_system_prompt("Seg A", defn_a, feature_stats, 100)
    prompt_b = builder.build_system_prompt("Seg B", defn_b, feature_stats, 200)
    assert "Sports" in prompt_a
    assert "Beauty" in prompt_b
    assert "Sports" not in prompt_b
