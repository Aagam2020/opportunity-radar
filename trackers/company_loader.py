"""Load tracked companies from a small YAML config file."""

from __future__ import annotations

from pathlib import Path

import yaml

SUPPORTED_ATS_TYPES = {"greenhouse", "lever", "ashby"}


def load_companies(path: str = "data/companies.yaml") -> list[dict]:
    """Load tracked companies from YAML and validate the basic shape.

    The config is intentionally simple so beginners can edit it without learning
    a larger framework or schema system.
    """
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Could not find company config: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    companies = data.get("companies", [])
    if not isinstance(companies, list):
        raise ValueError("The companies config must contain a top-level 'companies' list.")

    validated_companies: list[dict] = []

    for entry in companies:
        if not isinstance(entry, dict):
            raise ValueError("Each company entry must be a dictionary.")

        name = str(entry.get("name", "")).strip()
        ats = str(entry.get("ats", "")).strip().lower()
        careers_url = str(entry.get("careers_url", "")).strip()

        if not name:
            raise ValueError("Each company entry must include a name.")
        if ats not in SUPPORTED_ATS_TYPES:
            raise ValueError(
                f"Unsupported ATS type '{ats}' for {name}. "
                f"Use one of: {', '.join(sorted(SUPPORTED_ATS_TYPES))}."
            )
        if not careers_url:
            raise ValueError(f"Company '{name}' is missing a careers_url.")

        validated_companies.append(
            {
                "name": name,
                "ats": ats,
                "careers_url": careers_url,
            }
        )

    return validated_companies
