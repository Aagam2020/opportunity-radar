"""OpenAI-powered job description analyzer."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from company_intel import enrich_analysis_with_company_context
from config import OPENAI_API_KEY, OPENAI_MODEL
from prompts import build_analysis_prompt, build_resume_tailoring_prompt
from scoring import calculate_fit_score
from user_profile import get_profile_summary_text, load_user_profile

REQUIRED_ANALYSIS_FIELDS = [
    "company",
    "title",
    "cleaned_description",
    "ownership_score",
    "ai_score",
    "learning_score",
    "prestige_score",
    "startup_score",
    "comp_score",
    "analysis",
]

SCORE_FIELDS = [
    "ownership_score",
    "ai_score",
    "learning_score",
    "prestige_score",
    "startup_score",
    "comp_score",
]

REQUIRED_RESUME_TAILORING_FIELDS = [
    "resume_highlights",
    "key_skills_to_surface",
    "outreach_angle",
    "why_you_match",
]


def _clamp_score(value: Any) -> float:
    """Convert model score values into a safe 0-10 float."""
    return max(0.0, min(10.0, float(value)))


def _extract_json(content: str) -> dict:
    """Parse JSON from the model response.

    This keeps the function beginner-friendly while still handling the common
    case where a model wraps JSON in markdown code fences.
    """
    cleaned = content.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    return json.loads(cleaned)


def _extract_json_with_required_fields(content: str, required_fields: list[str]) -> dict:
    """Parse JSON and enforce a known response schema."""
    data = _extract_json(content)

    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    return data


def _normalize_result(data: dict, original_description: str) -> dict:
    """Normalize model output so downstream consumers get a stable schema."""
    cleaned_description = str(data.get("cleaned_description", "")).strip()
    if not cleaned_description:
        cleaned_description = original_description.strip()

    normalized = {
        "company": str(data.get("company", "")).strip() or "Unknown",
        "title": str(data.get("title", "")).strip() or "Unknown",
        "cleaned_description": cleaned_description,
        "analysis": "",
    }

    normalized["analysis"] = enrich_analysis_with_company_context(
        str(data.get("analysis", "")).strip(),
        normalized["company"],
    )

    for field in SCORE_FIELDS:
        normalized[field] = _clamp_score(data.get(field, 0))

    normalized["fit_score"] = calculate_fit_score(normalized)
    return normalized


def _normalize_string_list(value: Any) -> list[str]:
    """Coerce a model list field into a clean list of non-empty strings."""
    if not isinstance(value, list):
        raise ValueError("Expected a list of strings.")

    normalized_items = [str(item).strip() for item in value if str(item).strip()]
    if not normalized_items:
        raise ValueError("Expected at least one non-empty list item.")

    return normalized_items


def _normalize_resume_tailoring(data: dict) -> dict:
    """Normalize resume-tailoring output so the UI can render predictable fields."""
    resume_highlights = _normalize_string_list(data.get("resume_highlights", []))
    key_skills = _normalize_string_list(data.get("key_skills_to_surface", []))
    outreach_angle = str(data.get("outreach_angle", "")).strip()
    why_you_match = str(data.get("why_you_match", "")).strip()

    if len(resume_highlights) < 3 or len(resume_highlights) > 5:
        raise ValueError("resume_highlights must contain 3 to 5 bullets.")
    if not outreach_angle:
        raise ValueError("outreach_angle cannot be empty.")
    if not why_you_match:
        raise ValueError("why_you_match cannot be empty.")

    return {
        "resume_highlights": resume_highlights,
        "key_skills_to_surface": key_skills,
        "outreach_angle": outreach_angle,
        "why_you_match": why_you_match,
    }


def _build_client() -> OpenAI:
    """Create an OpenAI client after validating local configuration."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set. Add it to your environment or .env file.")

    return OpenAI(api_key=OPENAI_API_KEY)


def analyze_job_description(job_description: str) -> dict:
    """Send the job description to OpenAI and return a structured result."""
    if not job_description.strip():
        raise ValueError("Job description cannot be empty.")

    client = _build_client()
    prompt = build_analysis_prompt(job_description)

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt,
    )

    content = response.output_text
    result = _extract_json_with_required_fields(content, REQUIRED_ANALYSIS_FIELDS)
    return _normalize_result(result, job_description)


def analyze_job(job_description: str) -> dict:
    """Small wrapper used by the pipeline.

    The Streamlit app already imports ``analyze_job_description`` directly.
    This alias lets the backend pipeline call a shorter, clearer name without
    changing the app code.
    """
    return analyze_job_description(job_description)


def generate_resume_tailoring(job: dict) -> dict:
    """Generate on-demand resume-tailoring guidance for one tracked job."""
    title = str(job.get("title", "")).strip() or "Unknown"
    company = str(job.get("company", "")).strip() or "Unknown"
    description = str(job.get("description", "")).strip()
    fit_score = float(job.get("fit_score", 0))
    analysis = str(job.get("analysis", "")).strip()

    if not description:
        raise ValueError("Job description is required for resume tailoring.")

    # Personalization is optional. Missing profile data falls back to a
    # generic role-based prompt so the existing feature keeps working.
    user_profile = load_user_profile()
    user_profile_summary = get_profile_summary_text(user_profile)

    client = _build_client()
    prompt = build_resume_tailoring_prompt(
        title=title,
        company=company,
        description=description,
        fit_score=fit_score,
        analysis=analysis,
        user_profile_summary=user_profile_summary,
    )

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt,
    )

    content = response.output_text
    result = _extract_json_with_required_fields(content, REQUIRED_RESUME_TAILORING_FIELDS)
    return _normalize_resume_tailoring(result)
