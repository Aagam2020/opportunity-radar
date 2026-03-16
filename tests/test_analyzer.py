"""Tests for analyzer helpers."""

from __future__ import annotations

import pytest

import analyzer
from analyzer import (
    _extract_json_with_required_fields,
    _normalize_result,
    _normalize_resume_tailoring,
    generate_resume_tailoring,
)


def test_extract_json_with_required_fields_accepts_valid_resume_tailoring_json() -> None:
    content = """
    {
      "resume_highlights": ["Own roadmap", "Ship AI features", "Partner cross-functionally"],
      "key_skills_to_surface": ["Roadmapping", "AI product strategy", "Stakeholder management"],
      "outreach_angle": "I would frame interest around product ownership and AI execution.",
      "why_you_match": "The role aligns with strong PM fundamentals and clear AI exposure."
    }
    """

    result = _extract_json_with_required_fields(
        content,
        [
            "resume_highlights",
            "key_skills_to_surface",
            "outreach_angle",
            "why_you_match",
        ],
    )

    assert result["resume_highlights"][0] == "Own roadmap"
    assert result["key_skills_to_surface"][1] == "AI product strategy"


def test_normalize_resume_tailoring_returns_clean_strings() -> None:
    data = {
        "resume_highlights": [
            " Lead product direction ",
            "Ship AI features",
            " Partner with engineering and design ",
        ],
        "key_skills_to_surface": [" Roadmapping ", "LLM products", "Stakeholder alignment"],
        "outreach_angle": " Highlight direct interest in the product area. ",
        "why_you_match": " Emphasize ownership, AI context, and cross-functional execution. ",
    }

    normalized = _normalize_resume_tailoring(data)

    assert normalized == {
        "resume_highlights": [
            "Lead product direction",
            "Ship AI features",
            "Partner with engineering and design",
        ],
        "key_skills_to_surface": [
            "Roadmapping",
            "LLM products",
            "Stakeholder alignment",
        ],
        "outreach_angle": "Highlight direct interest in the product area.",
        "why_you_match": "Emphasize ownership, AI context, and cross-functional execution.",
    }


def test_normalize_resume_tailoring_rejects_too_few_highlights() -> None:
    data = {
        "resume_highlights": ["One", "Two"],
        "key_skills_to_surface": ["Roadmapping"],
        "outreach_angle": "Short outreach angle.",
        "why_you_match": "Short fit summary.",
    }

    with pytest.raises(ValueError, match="resume_highlights must contain 3 to 5 bullets"):
        _normalize_resume_tailoring(data)


def test_normalize_result_appends_company_context_to_analysis() -> None:
    normalized = _normalize_result(
        {
            "company": "OpenAI",
            "title": "Product Manager",
            "cleaned_description": "Build AI tools.",
            "ownership_score": 9,
            "ai_score": 10,
            "learning_score": 8,
            "prestige_score": 9,
            "startup_score": 8,
            "comp_score": 7,
            "analysis": "Strong fit due to AI relevance and ownership.",
        },
        original_description="Build AI tools.",
    )

    assert "Company context:" in normalized["analysis"]
    assert "High AI relevance due to generative AI focus" in normalized["analysis"]


def test_generate_resume_tailoring_uses_profile_summary_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_prompt: dict[str, str] = {}

    class FakeResponse:
        output_text = """
        {
          "resume_highlights": ["Own roadmap execution", "Translate AI requirements", "Partner cross-functionally"],
          "key_skills_to_surface": ["Roadmapping", "AI product strategy", "Stakeholder management"],
          "outreach_angle": "Frame interest around AI product execution and user impact.",
          "why_you_match": "The role matches prior product execution and transferable AI-adjacent work."
        }
        """

    class FakeClient:
        class Responses:
            @staticmethod
            def create(*, model: str, input: str) -> FakeResponse:
                del model
                captured_prompt["value"] = input
                return FakeResponse()

        responses = Responses()

    monkeypatch.setattr(analyzer, "_build_client", lambda: FakeClient())
    monkeypatch.setattr(
        analyzer,
        "load_user_profile",
        lambda: {
            "name": "Taylor",
            "target_roles": ["AI Product Manager"],
            "target_industries": ["Artificial Intelligence"],
            "experience_summary": "PM with AI-adjacent product delivery experience.",
            "key_projects": ["Launched workflow automation features"],
            "skills": ["Roadmapping", "Experimentation"],
            "strengths": ["Cross-functional leadership"],
            "preferred_locations": ["Remote"],
        },
    )

    result = generate_resume_tailoring(
        {
            "company": "OpenAI",
            "title": "Product Manager",
            "description": "Build AI tools for developers.",
            "fit_score": 88,
            "analysis": "Strong fit due to AI relevance and ownership.",
        }
    )

    assert result["key_skills_to_surface"][0] == "Roadmapping"
    assert "Candidate profile:" in captured_prompt["value"]
    assert "Taylor" in captured_prompt["value"]
    assert "Saved analysis: Strong fit due to AI relevance and ownership." in captured_prompt["value"]


def test_generate_resume_tailoring_falls_back_to_generic_mode_without_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_prompt: dict[str, str] = {}

    class FakeResponse:
        output_text = """
        {
          "resume_highlights": ["Own roadmap execution", "Translate AI requirements", "Partner cross-functionally"],
          "key_skills_to_surface": ["Roadmapping", "AI product strategy", "Stakeholder management"],
          "outreach_angle": "Frame interest around AI product execution and user impact.",
          "why_you_match": "The role matches strong product fundamentals and relevant execution patterns."
        }
        """

    class FakeClient:
        class Responses:
            @staticmethod
            def create(*, model: str, input: str) -> FakeResponse:
                del model
                captured_prompt["value"] = input
                return FakeResponse()

        responses = Responses()

    monkeypatch.setattr(analyzer, "_build_client", lambda: FakeClient())
    monkeypatch.setattr(analyzer, "load_user_profile", lambda: None)

    generate_resume_tailoring(
        {
            "company": "OpenAI",
            "title": "Product Manager",
            "description": "Build AI tools for developers.",
            "fit_score": 88,
            "analysis": "Strong fit due to AI relevance and ownership.",
        }
    )

    assert "Candidate profile:\nNot provided." in captured_prompt["value"]
