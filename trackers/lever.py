"""Fetch jobs from Lever-hosted careers pages."""

from __future__ import annotations

import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def _fetch_json(url: str) -> list[dict]:
    """Fetch JSON from a public ATS endpoint."""
    request = Request(url, headers={"User-Agent": "Opportunity-Radar/0.1"})

    with urlopen(request, timeout=30) as response:
        return json.load(response)


def _extract_site_name(careers_url: str) -> str:
    """Pull the Lever site name from the hosted jobs URL."""
    path_parts = [part for part in urlparse(careers_url).path.split("/") if part]
    if not path_parts:
        raise ValueError(f"Could not extract Lever site name from {careers_url}")

    return path_parts[-1]


def _build_description(job: dict) -> str:
    """Use Lever's plain-text fields when available."""
    parts = [
        str(job.get("descriptionPlain", "")).strip(),
        str(job.get("additionalPlain", "")).strip(),
    ]
    return "\n\n".join(part for part in parts if part)


def _build_location(job: dict) -> str:
    """Combine the common Lever location fields into one readable value."""
    categories = job.get("categories", {})
    location = str(categories.get("location", "")).strip()
    workplace_type = str(job.get("workplaceType", "")).strip()

    if location and workplace_type:
        return f"{location} ({workplace_type})"
    if location:
        return location
    if workplace_type:
        return workplace_type

    return "Unknown"


def fetch_jobs(company: dict) -> list[dict]:
    """Fetch and normalize Lever job postings.

    Lever exposes public postings at:
    https://api.lever.co/v0/postings/{site}?mode=json
    """
    site_name = _extract_site_name(company["careers_url"])
    api_url = f"https://api.lever.co/v0/postings/{site_name}?mode=json"
    payload = _fetch_json(api_url)

    normalized_jobs: list[dict] = []

    for job in payload:
        normalized_jobs.append(
            {
                "company": company["name"],
                "title": str(job.get("text", "")).strip(),
                "location": _build_location(job),
                "url": str(job.get("hostedUrl", "")).strip(),
                "description": _build_description(job),
                "source": "lever",
            }
        )

    return normalized_jobs
