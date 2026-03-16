"""Scoring utilities for Opportunity Radar."""

from __future__ import annotations

from config import SCORE_WEIGHTS


def _normalize_score(value: float) -> float:
    """Keep model scores inside the expected 0-10 range."""
    return max(0.0, min(10.0, float(value)))


def calculate_fit_score(result: dict) -> float:
    """Convert six 0-10 scores into one weighted 0-100 fit score."""
    total = 0.0

    for field_name, weight in SCORE_WEIGHTS.items():
        score = _normalize_score(result.get(field_name, 0))
        # Each dimension score is out of 10, so divide by 10 before applying weight.
        total += (score / 10) * weight

    return round(total, 1)
