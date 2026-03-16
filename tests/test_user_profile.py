"""Tests for user profile helpers."""

from __future__ import annotations

import json
from pathlib import Path

from user_profile import get_profile_summary_text, load_user_profile


def test_load_user_profile_returns_none_when_file_is_missing(tmp_path: Path) -> None:
    assert load_user_profile(tmp_path / "missing.json") is None


def test_load_user_profile_normalizes_supported_fields(tmp_path: Path) -> None:
    profile_path = tmp_path / "user_profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "name": " Taylor ",
                "target_roles": [" AI Product Manager ", "", "Senior Product Manager"],
                "target_industries": ["Artificial Intelligence"],
                "experience_summary": " Built AI-adjacent products. ",
                "key_projects": [" Launched copilots "],
                "skills": [" Roadmapping ", "Stakeholder management"],
                "strengths": [" Structured thinking "],
                "preferred_locations": [" Remote "],
                "ignored_field": "should not be kept",
            }
        ),
        encoding="utf-8",
    )

    profile = load_user_profile(profile_path)

    assert profile == {
        "name": "Taylor",
        "target_roles": ["AI Product Manager", "Senior Product Manager"],
        "target_industries": ["Artificial Intelligence"],
        "experience_summary": "Built AI-adjacent products.",
        "key_projects": ["Launched copilots"],
        "skills": ["Roadmapping", "Stakeholder management"],
        "strengths": ["Structured thinking"],
        "preferred_locations": ["Remote"],
    }


def test_get_profile_summary_text_returns_compact_multiline_summary() -> None:
    summary = get_profile_summary_text(
        {
            "name": "Taylor",
            "target_roles": ["AI Product Manager"],
            "target_industries": ["Artificial Intelligence"],
            "experience_summary": "Built AI-adjacent products.",
            "key_projects": ["Launched copilots"],
            "skills": ["Roadmapping"],
            "strengths": ["Structured thinking"],
            "preferred_locations": ["Remote"],
        }
    )

    assert "Candidate name: Taylor" in summary
    assert "Experience summary: Built AI-adjacent products." in summary
    assert "Target roles: AI Product Manager" in summary
    assert "Preferred locations: Remote" in summary
