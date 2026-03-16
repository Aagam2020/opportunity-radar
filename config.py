"""Configuration helpers for Opportunity Radar."""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Load values from a local .env file if one exists.
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Central place for score weights so the app and analyzer stay aligned.
SCORE_WEIGHTS = {
    "ownership_score": 30,
    "ai_score": 25,
    "learning_score": 15,
    "prestige_score": 15,
    "startup_score": 10,
    "comp_score": 5,
}

# These are the fields the model must return.
REQUIRED_OUTPUT_FIELDS = [
    "company",
    "title",
    "ownership_score",
    "ai_score",
    "learning_score",
    "prestige_score",
    "startup_score",
    "comp_score",
    "analysis",
]
