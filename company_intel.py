"""Company intelligence helpers for backend job analysis."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

COMPANY_INTEL_PATH = Path("data/company_intel.json")
NEUTRAL_COMPANY_INTEL = {
    "category": "General AI Company",
    "prestige_score": 5,
    "ai_relevance": 5,
    "startup_upside": 5,
}

CATEGORY_FOCUS_PHRASES = {
    "Frontier AI Lab": "generative AI focus",
    "Data Labeling Platform": "AI data and model operations focus",
    "AI Search": "AI-native search focus",
    "Enterprise AI Platform": "enterprise AI product focus",
    "AI Agents": "autonomous agent focus",
    "Open-Weight Frontier AI Lab": "open-weight model focus",
    "Open Model Platform": "open-source AI platform focus",
}


def _normalize_company_name(company_name: str) -> str:
    """Collapse casing and repeated whitespace for stable company lookup."""
    return " ".join(str(company_name).split()).strip().casefold()


@lru_cache(maxsize=1)
def load_company_intel() -> dict[str, dict[str, int | str]]:
    """Load company intelligence data once per process."""
    with COMPANY_INTEL_PATH.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    if not isinstance(raw_data, dict):
        raise ValueError(f"{COMPANY_INTEL_PATH} must contain a JSON object.")

    normalized_data: dict[str, dict[str, int | str]] = {}
    for company_name, intel in raw_data.items():
        if not isinstance(intel, dict):
            raise ValueError(f"Company intel for {company_name} must be a JSON object.")
        normalized_data[_normalize_company_name(company_name)] = intel

    return normalized_data


def get_company_intel(company_name: str) -> dict[str, int | str]:
    """Return company intelligence data or neutral defaults."""
    normalized_name = _normalize_company_name(company_name)
    intel = load_company_intel().get(normalized_name, NEUTRAL_COMPANY_INTEL)
    return {
        "category": str(intel.get("category", NEUTRAL_COMPANY_INTEL["category"])).strip()
        or NEUTRAL_COMPANY_INTEL["category"],
        "prestige_score": int(intel.get("prestige_score", NEUTRAL_COMPANY_INTEL["prestige_score"])),
        "ai_relevance": int(intel.get("ai_relevance", NEUTRAL_COMPANY_INTEL["ai_relevance"])),
        "startup_upside": int(intel.get("startup_upside", NEUTRAL_COMPANY_INTEL["startup_upside"])),
    }


def build_company_context_bullets(company_name: str) -> list[str]:
    """Convert company-level signals into concise explanation bullets."""
    intel = get_company_intel(company_name)
    category = str(intel["category"])
    prestige_score = int(intel["prestige_score"])
    ai_relevance = int(intel["ai_relevance"])
    startup_upside = int(intel["startup_upside"])
    focus_phrase = CATEGORY_FOCUS_PHRASES.get(category, "AI product focus")

    if prestige_score >= 8:
        prestige_bullet = f"{category} with high research prestige"
    elif prestige_score >= 6:
        prestige_bullet = f"{category} with solid market credibility"
    else:
        prestige_bullet = f"{category} with moderate external prestige"

    if ai_relevance >= 8:
        ai_bullet = f"High AI relevance due to {focus_phrase}"
    elif ai_relevance >= 6:
        ai_bullet = f"Meaningful AI relevance due to {focus_phrase}"
    else:
        ai_bullet = f"Moderate AI relevance with some exposure to {focus_phrase}"

    if startup_upside >= 8:
        startup_bullet = "Strong startup upside due to rapid industry growth"
    elif startup_upside >= 6:
        startup_bullet = "Solid startup upside with room for category expansion"
    else:
        startup_bullet = "Moderate startup upside relative to the broader AI market"

    return [prestige_bullet, ai_bullet, startup_bullet]


def enrich_analysis_with_company_context(analysis: str, company_name: str) -> str:
    """Append deterministic company context bullets to a freeform analysis string."""
    cleaned_analysis = str(analysis).strip()
    if "Company context:" in cleaned_analysis:
        return cleaned_analysis

    company_context = "\n".join(
        f"- {bullet}" for bullet in build_company_context_bullets(company_name)
    )

    if cleaned_analysis:
        return f"{cleaned_analysis}\n\nCompany context:\n{company_context}"

    return f"Company context:\n{company_context}"
