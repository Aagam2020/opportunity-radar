"""Tests for company intelligence helpers."""

from __future__ import annotations

from company_intel import build_company_context_bullets, get_company_intel


def test_get_company_intel_returns_seeded_company_data() -> None:
    intel = get_company_intel("OpenAI")

    assert intel == {
        "category": "Frontier AI Lab",
        "prestige_score": 10,
        "ai_relevance": 10,
        "startup_upside": 9,
    }


def test_get_company_intel_returns_neutral_defaults_for_unknown_company() -> None:
    intel = get_company_intel("Example AI Co")

    assert intel == {
        "category": "General AI Company",
        "prestige_score": 5,
        "ai_relevance": 5,
        "startup_upside": 5,
    }


def test_build_company_context_bullets_returns_three_explanation_bullets() -> None:
    bullets = build_company_context_bullets("OpenAI")

    assert bullets == [
        "Frontier AI Lab with high research prestige",
        "High AI relevance due to generative AI focus",
        "Strong startup upside due to rapid industry growth",
    ]
