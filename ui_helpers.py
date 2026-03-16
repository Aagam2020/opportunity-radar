"""UI-oriented helpers for presenting scores and analysis text."""

from __future__ import annotations

import re

from config import SCORE_WEIGHTS
from description_utils import WEAK_DESCRIPTION_MARKERS, join_text_parts

SCORE_FIELD_LABELS = {
    "ownership_score": "Ownership",
    "ai_score": "AI Relevance",
    "learning_score": "Learning",
    "prestige_score": "Prestige",
    "startup_score": "Startup Upside",
    "comp_score": "Comp Potential",
}

INTERPRETATION_LABELS = {
    "ownership_score": ("strong product ownership", "lower product ownership"),
    "ai_score": ("high AI relevance", "lower AI relevance"),
    "learning_score": ("strong learning opportunity", "lower learning opportunity"),
    "prestige_score": ("strong prestige", "lower prestige"),
    "startup_score": ("strong startup upside", "lower startup upside"),
    "comp_score": ("strong compensation potential", "lower compensation potential"),
}

LOW_PRIORITY_SCORE_THRESHOLD = 70.0
DEFAULT_SORT_OPTION = "Score (High → Low)"
SORT_OPTIONS = [
    DEFAULT_SORT_OPTION,
    "Score (Low → High)",
    "AI Relevance",
]
DESCRIPTION_PREVIEW_FALLBACK = "Description preview unavailable."


def build_weighted_score_rows(job: dict) -> list[dict[str, str | float]]:
    """Return beginner-friendly score rows for a weighted breakdown table."""
    rows: list[dict[str, str | float]] = []

    for field_name, weight in SCORE_WEIGHTS.items():
        raw_score = float(job.get(field_name, 0))
        weighted_contribution = round((raw_score / 10) * weight, 1)
        rows.append(
            {
                "Factor": SCORE_FIELD_LABELS[field_name],
                "Raw score out of 10": raw_score,
                "Weight %": weight,
                "Weighted contribution": weighted_contribution,
            }
        )

    return rows


def compute_apply_priority(fit_score: float) -> str:
    """Map a fit score to a beginner-friendly application priority."""
    if fit_score >= 90:
        return "Apply now"
    if fit_score >= 80:
        return "Apply this week"
    if fit_score >= 65:
        return "Worth considering"
    return "Low priority"


def hide_low_priority_opportunities(jobs: list[dict], enabled: bool) -> list[dict]:
    """Optionally remove roles that fall below the low-priority threshold."""
    if not enabled:
        return list(jobs)

    return [
        job for job in jobs if float(job.get("fit_score", 0)) >= LOW_PRIORITY_SCORE_THRESHOLD
    ]


def sort_opportunities(jobs: list[dict], sort_option: str) -> list[dict]:
    """Sort jobs for display without changing the underlying scoring."""
    if sort_option == "Score (Low → High)":
        return sorted(
            jobs,
            key=lambda job: (
                float(job.get("fit_score", 0)),
                str(job.get("company", "Unknown")).strip().lower(),
            ),
        )

    if sort_option == "AI Relevance":
        return sorted(
            jobs,
            key=lambda job: (
                float(job.get("ai_score", 0)),
                float(job.get("fit_score", 0)),
            ),
            reverse=True,
        )

    return sorted(
        jobs,
        key=lambda job: (
            float(job.get("fit_score", 0)),
            float(job.get("ai_score", 0)),
        ),
        reverse=True,
    )


def build_interpretation_heading(job: dict) -> str:
    """Return the short heading shown above interpretation bullets."""
    fit_score = float(job.get("fit_score", 0))
    if fit_score >= 65:
        return "Why this role stands out"
    return "Why this ranks lower"


def _normalize_analysis(job: dict) -> str:
    """Return compact analysis text for keyword checks."""
    return " ".join(str(job.get("analysis", "")).split()).strip().lower()


def _score_value(job: dict, field_name: str) -> float:
    """Read a score field as a float with a safe default."""
    return float(job.get(field_name, 0))


def build_interpretation_bullets(job: dict) -> list[str]:
    """Turn score data into 3-4 concise bullets for the UI."""
    analysis = _normalize_analysis(job)
    weighted_fields = sorted(
        SCORE_WEIGHTS,
        key=lambda field_name: (_score_value(job, field_name) / 10) * SCORE_WEIGHTS[field_name],
        reverse=True,
    )
    weakest_fields = sorted(
        SCORE_WEIGHTS,
        key=lambda field_name: (_score_value(job, field_name), -SCORE_WEIGHTS[field_name]),
    )

    high_bullets = [
        INTERPRETATION_LABELS[field_name][0]
        for field_name in weighted_fields
        if _score_value(job, field_name) >= 8
    ]
    low_bullets = [
        INTERPRETATION_LABELS[field_name][1]
        for field_name in weakest_fields
        if _score_value(job, field_name) <= 5
    ]

    bullets: list[str] = []
    fit_score = float(job.get("fit_score", 0))

    if fit_score >= 65:
        bullets.extend(high_bullets[:3])
        if low_bullets:
            bullets.append(low_bullets[0])
    else:
        bullets.extend(low_bullets[:3])
        if high_bullets:
            bullets.append(high_bullets[0])

    if not bullets:
        if fit_score >= 65:
            bullets = [
                "balanced product ownership",
                "solid AI relevance",
                "steady learning opportunity",
            ]
        else:
            bullets = [
                "limited evidence of product ownership",
                "unclear AI relevance",
                "modest upside based on available details",
            ]

    if "unclear" in analysis or "lack" in analysis or "limited" in analysis:
        fallback_bullet = "limited detail in the posting"
        if fallback_bullet not in bullets:
            bullets.append(fallback_bullet)

    unique_bullets: list[str] = []
    for bullet in bullets:
        if bullet not in unique_bullets:
            unique_bullets.append(bullet)

    return unique_bullets[:4]


def build_interpretation(job: dict) -> list[str]:
    """Backward-compatible wrapper for concise interpretation bullets."""
    return build_interpretation_bullets(job)


def build_description_preview(job: dict, max_characters: int = 420) -> str:
    """Return a clean, readable description preview for the UI."""
    description = " ".join(str(job.get("description", "")).split()).strip()
    title = str(job.get("title", "")).strip()
    company = str(job.get("company", "")).strip()

    if not description:
        return DESCRIPTION_PREVIEW_FALLBACK

    lowered = description.lower()
    if any(marker in lowered for marker in WEAK_DESCRIPTION_MARKERS):
        return DESCRIPTION_PREVIEW_FALLBACK

    title_company_only = join_text_parts(
        [
            title,
            f"{title} @ {company}" if title and company else "",
            company,
        ]
    ).lower()
    if title_company_only and lowered == title_company_only:
        return DESCRIPTION_PREVIEW_FALLBACK

    if len(description) < 80:
        return DESCRIPTION_PREVIEW_FALLBACK

    cleaned_description = re.sub(r"[ \t]*[|•]+[ \t]*", " ", description)
    cleaned_description = re.sub(r"\s+", " ", cleaned_description).strip()

    if len(cleaned_description) <= max_characters:
        return cleaned_description

    truncated = cleaned_description[: max_characters + 1].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return f"{truncated}..."
