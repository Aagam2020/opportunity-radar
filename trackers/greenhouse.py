"""Fetch jobs from Greenhouse-hosted careers pages."""

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


def _extract_board_token(careers_url: str) -> str:
    """Pull the Greenhouse board token from the careers page URL."""
    path_parts = [part for part in urlparse(careers_url).path.split("/") if part]
    if not path_parts:
        raise ValueError(f"Could not extract Greenhouse board token from {careers_url}")

    return path_parts[-1]


def _collect_metadata_text(value: object) -> list[str]:
    """Pull readable text out of optional Greenhouse metadata blocks."""
    if isinstance(value, str):
        text = html_to_text(value)
        return [text] if text else []

    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            parts.extend(_collect_metadata_text(item))
        return parts

    if isinstance(value, dict):
        parts: list[str] = []
        title = str(value.get("name") or value.get("label") or value.get("title") or "").strip()
        raw_content = value.get("value") or value.get("content") or value.get("text")
        content_parts = _collect_metadata_text(raw_content)

        if title and content_parts:
            parts.append(join_text_parts([title, *content_parts]))
        else:
            if title:
                parts.append(title)
            parts.extend(content_parts)

        for key in ("metadata", "sections"):
            nested = value.get(key)
            if nested:
                parts.extend(_collect_metadata_text(nested))

        return parts

    return []


def _build_description(job: dict) -> str:
    """Use Greenhouse job content plus optional metadata sections."""
    parts = [html_to_text(str(job.get("content", "")))]
    parts.extend(_collect_metadata_text(job.get("metadata", [])))
    parts.extend(_collect_metadata_text(job.get("sections", [])))
    return join_text_parts(parts)


def _fetch_job_detail(board_token: str, job_id: object) -> dict:
    """Fetch the per-job detail payload when the listing data is incomplete."""
    detail_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"
    return _fetch_json(detail_url)


def fetch_jobs(company: dict) -> list[dict]:
    """Fetch and normalize Greenhouse job postings.

    Greenhouse exposes a public job board API:
    https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
    """
    board_token = _extract_board_token(company["careers_url"])
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    payload = _fetch_json(api_url)

    normalized_jobs: list[dict] = []

    for job in payload.get("jobs", []):
        description = _build_description(job)

        if is_weak_description(description, title=job.get("title", ""), company=company["name"]):
            job_id = job.get("id")
            if job_id:
                try:
                    detail_payload = _fetch_job_detail(board_token, job_id)
                    detail_description = _build_description(detail_payload)
                    if not is_weak_description(
                        detail_description,
                        title=job.get("title", ""),
                        company=company["name"],
                    ):
                        description = detail_description
                        print(
                            f"Fetched full description successfully: {company['name']} | {job.get('title', '').strip()}"
                        )
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"Could not fetch Greenhouse job detail for {company['name']} | {job.get('title', '').strip()}: {exc}"
                    )

        normalized_jobs.append(
            {
                "company": company["name"],
                "title": job.get("title", "").strip(),
                "location": job.get("location", {}).get("name", "Unknown"),
                "url": job.get("absolute_url", "").strip(),
                "description": description,
                "source": "greenhouse",
            }
        )

    return normalized_jobs
