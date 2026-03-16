"""Tests for UI helper functions."""

from __future__ import annotations

from ui_helpers import (
    DESCRIPTION_PREVIEW_FALLBACK,
    DEFAULT_SORT_OPTION,
    build_description_preview,
    build_interpretation,
    build_interpretation_bullets,
    build_interpretation_heading,
    build_weighted_score_rows,
    compute_apply_priority,
    hide_low_priority_opportunities,
    sort_opportunities,
)


def test_build_weighted_score_rows_uses_expected_weights() -> None:
    job = {
        "ownership_score": 8.0,
        "ai_score": 10.0,
        "learning_score": 7.0,
        "prestige_score": 9.0,
        "startup_score": 6.0,
        "comp_score": 4.0,
    }

    rows = build_weighted_score_rows(job)

    assert rows == [
        {
            "Factor": "Ownership",
            "Raw score out of 10": 8.0,
            "Weight %": 30,
            "Weighted contribution": 24.0,
        },
        {
            "Factor": "AI Relevance",
            "Raw score out of 10": 10.0,
            "Weight %": 25,
            "Weighted contribution": 25.0,
        },
        {
            "Factor": "Learning",
            "Raw score out of 10": 7.0,
            "Weight %": 15,
            "Weighted contribution": 10.5,
        },
        {
            "Factor": "Prestige",
            "Raw score out of 10": 9.0,
            "Weight %": 15,
            "Weighted contribution": 13.5,
        },
        {
            "Factor": "Startup Upside",
            "Raw score out of 10": 6.0,
            "Weight %": 10,
            "Weighted contribution": 6.0,
        },
        {
            "Factor": "Comp Potential",
            "Raw score out of 10": 4.0,
            "Weight %": 5,
            "Weighted contribution": 2.0,
        },
    ]


def test_compute_apply_priority_uses_expected_thresholds() -> None:
    assert compute_apply_priority(90) == "Apply now"
    assert compute_apply_priority(89.9) == "Apply this week"
    assert compute_apply_priority(80) == "Apply this week"
    assert compute_apply_priority(79.9) == "Worth considering"
    assert compute_apply_priority(65) == "Worth considering"
    assert compute_apply_priority(64.9) == "Low priority"


def test_build_interpretation_heading_switches_for_lower_scores() -> None:
    assert build_interpretation_heading({"fit_score": 82}) == "Why this role stands out"
    assert build_interpretation_heading({"fit_score": 60}) == "Why this ranks lower"


def test_build_interpretation_bullets_highlight_top_strengths_and_tradeoff() -> None:
    job = {
        "fit_score": 88,
        "ownership_score": 9,
        "ai_score": 10,
        "learning_score": 8,
        "prestige_score": 8,
        "startup_score": 4,
        "comp_score": 6,
        "analysis": (
            "This role scores well on ownership because it owns roadmap decisions. "
            "It also benefits from strong AI relevance and a credible learning environment. "
            "Compensation detail is limited."
        )
    }

    interpretation = build_interpretation_bullets(job)

    assert interpretation == [
        "strong product ownership",
        "high AI relevance",
        "strong learning opportunity",
        "lower startup upside",
    ]


def test_build_interpretation_bullets_focus_on_lower_signals_for_weaker_roles() -> None:
    job = {
        "fit_score": 58,
        "ownership_score": 4,
        "ai_score": 5,
        "learning_score": 6,
        "prestige_score": 8,
        "startup_score": 3,
        "comp_score": 4,
        "analysis": "The posting has limited detail and unclear ownership scope.",
    }

    interpretation = build_interpretation(job)

    assert interpretation == [
        "lower startup upside",
        "lower product ownership",
        "lower compensation potential",
        "strong prestige",
    ]


def test_hide_low_priority_opportunities_filters_below_threshold() -> None:
    jobs = [
        {"company": "Alpha", "fit_score": 82},
        {"company": "Beta", "fit_score": 69.9},
        {"company": "Gamma", "fit_score": 70},
    ]

    assert hide_low_priority_opportunities(jobs, enabled=True) == [
        {"company": "Alpha", "fit_score": 82},
        {"company": "Gamma", "fit_score": 70},
    ]


def test_sort_opportunities_uses_expected_sort_orders() -> None:
    jobs = [
        {"company": "Beta", "fit_score": 76, "ai_score": 8, "startup_score": 5},
        {"company": "Alpha", "fit_score": 88, "ai_score": 7, "startup_score": 6},
        {"company": "Gamma", "fit_score": 82, "ai_score": 10, "startup_score": 9},
    ]

    assert [job["company"] for job in sort_opportunities(jobs, DEFAULT_SORT_OPTION)] == [
        "Alpha",
        "Gamma",
        "Beta",
    ]
    assert [job["company"] for job in sort_opportunities(jobs, "Score (Low → High)")] == [
        "Beta",
        "Gamma",
        "Alpha",
    ]
    assert [job["company"] for job in sort_opportunities(jobs, "AI Relevance")] == [
        "Gamma",
        "Beta",
        "Alpha",
    ]


def test_build_description_preview_truncates_cleanly() -> None:
    job = {
        "company": "OpenAI",
        "title": "Product Manager",
        "description": (
            "Own the roadmap for customer-facing AI tools and translate user needs into clear "
            "product requirements across multiple product surfaces and lifecycle stages."
        ),
    }

    preview = build_description_preview(job, max_characters=80)

    assert preview == (
        "Own the roadmap for customer-facing AI tools and translate user needs into..."
    )


def test_build_description_preview_hides_placeholder_copy() -> None:
    job = {
        "company": "OpenAI",
        "title": "Product Manager",
        "description": "Product Manager @ OpenAI\nYou need to enable JavaScript to run this app.",
    }

    assert build_description_preview(job) == DESCRIPTION_PREVIEW_FALLBACK
