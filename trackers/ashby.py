"""Fetch jobs from Ashby-hosted careers pages."""

from __future__ import annotations

import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from description_utils import html_to_text, is_weak_description, join_text_parts


def _fetch_json(url: str) -> dict:
    """Fetch JSON from a public ATS endpoint."""
    request = Request(url, headers={"User-Agent": "Opportunity-Radar/0.1"})

    with urlopen(request, timeout=30) as response:
        return json.load(response)


def _extract_job_board_name(careers_url: str) -> str:
    """Pull the Ashby job board name from the hosted jobs URL."""
    path_parts = [part for part in urlparse(careers_url).path.split("/") if part]
    if not path_parts:
        raise ValueError(f"Could not extract Ashby board name from {careers_url}")

    return path_parts[-1]


def _coerce_text(value: object) -> str:
    """Normalize either plain text or HTML fragments into plain text."""
    if isinstance(value, str):
        return html_to_text(value)
    return ""


def _build_section_text(section: object) -> list[str]:
    """Convert common Ashby description sections into readable text."""
    if isinstance(section, str):
        text = _coerce_text(section)
        return [text] if text else []

    if isinstance(section, list):
        parts: list[str] = []
        for item in section:
            parts.extend(_build_section_text(item))
        return parts

    if isinstance(section, dict):
        heading = str(
            section.get("heading")
            or section.get("title")
            or section.get("name")
            or section.get("label")
            or ""
        ).strip()
        parts = [
            _coerce_text(section.get("descriptionPlain")),
            _coerce_text(section.get("descriptionHtml")),
            _coerce_text(section.get("html")),
            _coerce_text(section.get("text")),
            _coerce_text(section.get("content")),
            _coerce_text(section.get("body")),
            _coerce_text(section.get("value")),
        ]
        body = join_text_parts(parts)
        section_text = join_text_parts([heading, body])

        nested_parts: list[str] = []
        for key in ("sections", "items", "content", "blocks"):
            nested = section.get(key)
            if nested and not isinstance(nested, str):
                nested_parts.extend(_build_section_text(nested))

        return [part for part in [section_text, *nested_parts] if part]

    return []


def _build_location(job: dict) -> str:
    """Include remote status when Ashby exposes it."""
    location = str(job.get("location", "")).strip()
    workplace_type = str(job.get("workplaceType", "")).strip()

    if workplace_type.lower() == "none":
        workplace_type = ""

    if location and workplace_type and workplace_type.lower() not in location.lower():
        return f"{location} ({workplace_type})"
    if location:
        return location
    if workplace_type:
        return workplace_type

    return "Unknown"


def _build_description(job: dict) -> str:
    """Prefer Ashby's structured description fields over public page HTML."""
    parts = [
        _coerce_text(job.get("descriptionPlain")),
        _coerce_text(job.get("descriptionHtml")),
        _coerce_text(job.get("jobDescriptionPlain")),
        _coerce_text(job.get("jobDescriptionHtml")),
        _coerce_text(job.get("responsibilitiesPlain")),
        _coerce_text(job.get("responsibilitiesHtml")),
        _coerce_text(job.get("requirementsPlain")),
        _coerce_text(job.get("requirementsHtml")),
        _coerce_text(job.get("qualificationsPlain")),
        _coerce_text(job.get("qualificationsHtml")),
    ]

    for key in ("sections", "jobSections", "descriptionSections", "content"):
        parts.extend(_build_section_text(job.get(key, [])))

    return join_text_parts(parts)


def _extract_job_identifier(job: dict) -> str:
    """Find the best Ashby job identifier from the payload or public URL."""
    for key in ("id", "jobId", "jobPostingId", "jobPostId", "externalJobPostingId"):
        value = str(job.get(key, "")).strip()
        if value:
            return value

    job_url = str(job.get("jobUrl", "")).strip()
    path_parts = [part for part in urlparse(job_url).path.split("/") if part]
    if path_parts:
        return path_parts[-1]

    return ""


def _fetch_job_detail(board_name: str, job: dict) -> dict:
    """Try a few likely Ashby job detail endpoints until one works."""
    job_id = _extract_job_identifier(job)
    if not job_id:
        raise ValueError("Missing Ashby job identifier.")

    candidate_urls = [
        f"https://api.ashbyhq.com/posting-api/job-board/{board_name}/job/{job_id}",
        f"https://api.ashbyhq.com/posting-api/job-board/{board_name}/jobs/{job_id}",
        f"https://api.ashbyhq.com/posting-api/job/{job_id}",
    ]

    last_error: Exception | None = None
    for candidate_url in candidate_urls:
        try:
            return _fetch_json(candidate_url)
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if last_error is not None:
        raise last_error

    raise ValueError("No Ashby job detail endpoints were attempted.")


def fetch_jobs(company: dict) -> list[dict]:
    """Fetch and normalize Ashby job postings.

    Ashby exposes public job board data at:
    https://api.ashbyhq.com/posting-api/job-board/{job_board_name}
    """
    board_name = _extract_job_board_name(company["careers_url"])
    api_url = f"https://api.ashbyhq.com/posting-api/job-board/{board_name}"
    payload = _fetch_json(api_url)

    normalized_jobs: list[dict] = []

    for job in payload.get("jobs", []):
        if job.get("isListed") is False:
            continue

        description = _build_description(job)
        title = str(job.get("title", "")).strip()

        if is_weak_description(description, title=title, company=company["name"]):
            try:
                detail_payload = _fetch_job_detail(board_name, job)
                detail_description = _build_description(detail_payload)
                if not is_weak_description(detail_description, title=title, company=company["name"]):
                    description = detail_description
                    print(f"Fetched full description successfully: {company['name']} | {title}")
            except Exception as exc:  # noqa: BLE001
                print(f"Could not fetch Ashby job detail for {company['name']} | {title}: {exc}")

        normalized_jobs.append(
            {
                "company": company["name"],
                "title": title,
                "location": _build_location(job),
                "url": str(job.get("jobUrl", "")).strip(),
                "description": description,
                "source": "ashby",
            }
        )

    return normalized_jobs
