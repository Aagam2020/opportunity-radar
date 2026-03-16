"""Helpers for loading and summarizing a saved candidate profile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Keep the profile path in one place so the analyzer can reuse it easily.
USER_PROFILE_PATH = Path("data/user_profile.json")

SUPPORTED_PROFILE_FIELDS = [
    "name",
    "target_roles",
    "target_industries",
    "experience_summary",
    "key_projects",
    "skills",
    "strengths",
    "preferred_locations",
]


def _normalize_string_list(value: Any) -> list[str]:
    """Return a clean list of non-empty strings for profile list fields."""
    if not isinstance(value, list):
        return []

    return [str(item).strip() for item in value if str(item).strip()]


def load_user_profile(profile_path: Path = USER_PROFILE_PATH) -> dict[str, Any] | None:
    """Load the saved user profile if it exists.

    Returning ``None`` keeps downstream personalization optional, so resume
    tailoring can fall back to a generic mode when the profile file is absent.
    """
    if not profile_path.exists():
        return None

    with profile_path.open("r", encoding="utf-8") as file:
        raw_profile = json.load(file)

    if not isinstance(raw_profile, dict):
        return None

    normalized_profile: dict[str, Any] = {}
    for field in SUPPORTED_PROFILE_FIELDS:
        value = raw_profile.get(field)
        if field == "experience_summary":
            normalized_profile[field] = str(value or "").strip()
        elif field == "name":
            normalized_profile[field] = str(value or "").strip()
        else:
            normalized_profile[field] = _normalize_string_list(value)

    return normalized_profile


def get_profile_summary_text(profile: dict[str, Any] | None) -> str:
    """Convert a loaded profile into compact prompt-friendly text."""
    if not profile:
        return ""

    summary_lines: list[str] = []

    name = str(profile.get("name", "")).strip()
    if name:
        summary_lines.append(f"Candidate name: {name}")

    experience_summary = str(profile.get("experience_summary", "")).strip()
    if experience_summary:
        summary_lines.append(f"Experience summary: {experience_summary}")

    for field in [
        "target_roles",
        "target_industries",
        "key_projects",
        "skills",
        "strengths",
        "preferred_locations",
    ]:
        values = _normalize_string_list(profile.get(field))
        if not values:
            continue

        label = field.replace("_", " ").capitalize()
        summary_lines.append(f"{label}: {', '.join(values)}")

    return "\n".join(summary_lines)
