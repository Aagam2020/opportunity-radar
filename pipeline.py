"""Backend pipeline for fetching, filtering, analyzing, and saving jobs.

This script intentionally stays simple:

1. Load tracked companies.
2. Fetch jobs from each company's public ATS.
3. Keep only product-related roles.
4. Download the full job description from the job URL.
5. Send that description to the OpenAI analyzer.
6. Save the structured result to ``data/analyzed_jobs.json``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from analyzer import analyze_job
from company_intel import enrich_analysis_with_company_context
from description_utils import html_to_text, is_weak_description
from trackers import ashby, greenhouse, lever
from trackers.company_loader import load_companies

PRODUCT_ROLE_EXCLUDE_TERMS = [
    "applied scientist",
    "distinguished engineer",
    "engineer",
    "engineering",
    "research",
    "scientist",
    "ml engineer",
    "software engineer",
    "staff engineer",
    "principal engineer",
]

# Keep pipeline output in one predictable place.
ANALYZED_JOBS_PATH = Path("data/analyzed_jobs.json")
RAW_JOBS_PATH = Path("data/raw_jobs.json")
ANALYSIS_SCORE_FIELDS = [
    "ownership_score",
    "ai_score",
    "learning_score",
    "prestige_score",
    "startup_score",
    "comp_score",
    "fit_score",
    "analysis",
]


def normalize_job_title(job: dict) -> str:
    """Return a lowercase job title for matching and logging."""
    return str(job.get("title", "")).strip().lower()


def classify_product_role(job: dict) -> tuple[bool, str]:
    """Return whether a job avoids clearly engineering or research titles."""
    title = normalize_job_title(job)
    if not title:
        return False, "missing title"

    has_excluded_term = any(term in title for term in PRODUCT_ROLE_EXCLUDE_TERMS)
    if has_excluded_term:
        return False, "engineering or research title"

    return True, "allowed title"


def is_product_role(job: dict) -> bool:
    """Return True when a title avoids clearly engineering or research roles."""
    is_allowed, _ = classify_product_role(job)
    return is_allowed


def split_product_jobs(jobs: list[dict]) -> tuple[list[dict], list[dict], dict[str, int]]:
    """Separate fetched jobs into kept product roles and excluded roles."""
    kept_jobs: list[dict] = []
    excluded_jobs: list[dict] = []
    exclusion_counts: dict[str, int] = {}

    for job in jobs:
        is_allowed, reason = classify_product_role(job)
        if is_allowed:
            kept_jobs.append(job)
        else:
            excluded_jobs.append(job)
            exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1

    return kept_jobs, excluded_jobs, exclusion_counts


def fetch_company_jobs(company: dict) -> list[dict]:
    """Route a company to the correct ATS tracker."""
    ats = company["ats"]

    if ats == "greenhouse":
        return greenhouse.fetch_jobs(company)
    if ats == "lever":
        return lever.fetch_jobs(company)
    if ats == "ashby":
        return ashby.fetch_jobs(company)

    raise ValueError(f"Unsupported ATS type: {ats}")


def fetch_job_description(job: dict) -> str:
    """Return the best available full description for a normalized job.

    The trackers already prefer ATS API data. This helper only fetches the
    public page when the existing description still looks weak.
    """
    url = str(job.get("url", "")).strip()
    fallback_description = str(job.get("description", "")).strip()
    title = str(job.get("title", "")).strip()
    company = str(job.get("company", "")).strip()

    if fallback_description and not is_weak_description(
        fallback_description,
        title=title,
        company=company,
    ):
        print(f"Fetched full description successfully: {company} | {title}")
        return fallback_description

    if not url:
        return fallback_description

    request = Request(url, headers={"User-Agent": "Opportunity-Radar/0.1"})

    try:
        with urlopen(request, timeout=30) as response:
            page_html = response.read().decode("utf-8", errors="ignore")
    except Exception as exc:  # noqa: BLE001
        print(f"Could not fetch full description for {job.get('title', 'Unknown Role')}: {exc}")
        return fallback_description

    page_text = html_to_text(page_html)
    if page_text and not is_weak_description(page_text, title=title, company=company):
        print(f"Fetched full description successfully: {company} | {title}")
        return page_text

    return fallback_description


def has_sufficient_description_quality(job: dict, description: str) -> bool:
    """Keep model analysis away from placeholder or title-only descriptions."""
    return not is_weak_description(
        description,
        title=str(job.get("title", "")).strip(),
        company=str(job.get("company", "")).strip(),
    )


def load_saved_jobs(output_path: Path = ANALYZED_JOBS_PATH) -> list[dict]:
    """Load existing analyzed jobs from disk.

    Returning an empty list keeps the first pipeline run simple.
    """
    if not output_path.exists():
        return []

    with output_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{output_path} must contain a JSON list.")

    return data


def _timestamp_now() -> str:
    """Return a simple UTC timestamp for job metadata."""
    return datetime.now(UTC).isoformat()


def build_job_key(job: dict) -> tuple[str, str, str]:
    """Build the duplicate key required by the pipeline.

    The requirement is company + title + url. Lowercasing makes duplicate
    detection slightly more forgiving across data sources.
    """
    return (
        str(job.get("company", "")).strip().lower(),
        str(job.get("title", "")).strip().lower(),
        str(job.get("url", "")).strip().lower(),
    )


def normalize_description_for_comparison(description: str) -> str:
    """Collapse trivial text differences before deciding to re-analyze.

    This keeps the change detection simple and JSON-based. We only ignore
    whitespace and casing changes, so genuinely edited descriptions still
    trigger a fresh analysis.
    """
    # Split/join collapses repeated whitespace and line-break noise into
    # single spaces, which is enough for a lightweight "meaningful change"
    # check without introducing extra storage or hashing.
    return " ".join(str(description).split()).strip().lower()


def save_jobs(jobs: list[dict], output_path: Path = ANALYZED_JOBS_PATH) -> None:
    """Write analyzed jobs to disk as pretty JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(jobs, file, indent=2, ensure_ascii=True)


def prepare_raw_job(job: dict, fetched_at: str) -> dict:
    """Normalize a fetched job and attach basic fetch metadata."""
    return {
        "company": str(job.get("company", "")).strip(),
        "title": str(job.get("title", "")).strip(),
        "location": str(job.get("location", "Unknown")).strip() or "Unknown",
        "url": str(job.get("url", "")).strip(),
        "description": str(job.get("description", "")).strip(),
        "source": str(job.get("source", "unknown")).strip() or "unknown",
        "fetched_at": str(job.get("fetched_at", "")).strip() or fetched_at,
    }


def prepare_analyzed_job(
    raw_job: dict,
    description: str,
    analysis_result: dict,
    analyzed_at: str,
    existing_job: dict | None = None,
) -> dict:
    """Build the persisted analyzed job payload."""
    existing_job = existing_job or {}
    company_name = str(raw_job.get("company", "")).strip() or str(existing_job.get("company", "")).strip()
    return {
        "company": company_name,
        "title": str(raw_job.get("title", "")).strip(),
        "location": str(raw_job.get("location", "Unknown")).strip() or "Unknown",
        "url": str(raw_job.get("url", "")).strip(),
        "description": description,
        "source": str(raw_job.get("source", "unknown")).strip() or "unknown",
        "fetched_at": str(raw_job.get("fetched_at", "")).strip(),
        "analyzed_at": analyzed_at,
        "ownership_score": analysis_result["ownership_score"],
        "ai_score": analysis_result["ai_score"],
        "learning_score": analysis_result["learning_score"],
        "prestige_score": analysis_result["prestige_score"],
        "startup_score": analysis_result["startup_score"],
        "comp_score": analysis_result["comp_score"],
        "fit_score": analysis_result["fit_score"],
        "analysis": enrich_analysis_with_company_context(
            analysis_result["analysis"],
            company_name,
        ),
    }


def should_update_existing_job(existing_job: dict, raw_job: dict, description: str) -> bool:
    """Return True when an existing analyzed job should be re-analyzed."""
    del raw_job
    existing_description = normalize_description_for_comparison(
        str(existing_job.get("description", ""))
    )
    current_description = normalize_description_for_comparison(description)
    return existing_description != current_description


def should_backfill_existing_job_metadata(existing_job: dict, raw_job: dict) -> bool:
    """Return True when an existing job is unchanged but missing required metadata."""
    expected_source = str(raw_job.get("source", "unknown")).strip() or "unknown"

    if str(existing_job.get("source", "")).strip() != expected_source:
        return True
    if not str(existing_job.get("fetched_at", "")).strip():
        return True
    if not str(existing_job.get("analyzed_at", "")).strip():
        return True

    return False


def backfill_existing_job_metadata(existing_job: dict, raw_job: dict) -> dict:
    """Fill required metadata fields without changing the analysis payload."""
    updated_job = dict(existing_job)
    fallback_timestamp = str(raw_job.get("fetched_at", "")).strip()
    updated_job["source"] = str(raw_job.get("source", "unknown")).strip() or "unknown"
    updated_job["fetched_at"] = str(existing_job.get("fetched_at", "")).strip() or fallback_timestamp
    updated_job["analyzed_at"] = str(existing_job.get("analyzed_at", "")).strip() or fallback_timestamp
    return updated_job


def collect_product_jobs(companies_path: str = "data/companies.yaml") -> list[dict]:
    """Load tracked companies, fetch jobs, and keep product-related roles.

    Logging is kept close to the work so the terminal output reads like a simple
    progress report when the script runs.
    """
    tracked_companies = load_companies(companies_path)
    matching_jobs: list[dict] = []

    for company in tracked_companies:
        print(f"Fetching {company['name']} jobs...")

        try:
            jobs = fetch_company_jobs(company)
        except Exception as exc:  # noqa: BLE001
            # Keep going so one broken company board does not stop the pipeline.
            print(f"Skipping {company['name']} due to fetch error: {exc}")
            print()
            continue

        kept_jobs, excluded_jobs, exclusion_counts = split_product_jobs(jobs)
        sample_excluded_titles = [
            str(job.get("title", "")).strip() or "Unknown Role" for job in excluded_jobs[:5]
        ]

        print(f"Fetched jobs: {len(jobs)}")
        print(f"Filtered out by title: {len(excluded_jobs)}")
        print(f"Kept jobs: {len(kept_jobs)}")
        if exclusion_counts:
            print(f"Title filter breakdown: {exclusion_counts}")
        if sample_excluded_titles:
            print(f"Sample excluded titles: {sample_excluded_titles}")
        print()

        matching_jobs.extend(kept_jobs)

    return matching_jobs


def analyze_and_save_jobs(
    companies_path: str = "data/companies.yaml",
    output_path: Path = ANALYZED_JOBS_PATH,
    raw_output_path: Path = RAW_JOBS_PATH,
) -> list[dict]:
    """Run the full backend pipeline and save all analyzed jobs locally."""
    product_jobs = collect_product_jobs(companies_path)
    fetched_at = _timestamp_now()
    raw_jobs = [prepare_raw_job(job, fetched_at) for job in product_jobs]
    save_jobs(raw_jobs, raw_output_path)
    print(f"Saved raw jobs: {len(raw_jobs)} -> {raw_output_path}")
    print()

    saved_jobs = load_saved_jobs(output_path)
    saved_jobs_by_key = {build_job_key(job): index for index, job in enumerate(saved_jobs)}
    filtered_due_to_description = 0
    newly_analyzed_jobs = 0

    for job in raw_jobs:
        job_key = build_job_key(job)
        existing_index = saved_jobs_by_key.get(job_key)
        existing_job = saved_jobs[existing_index] if existing_index is not None else None

        # Log each candidate before deciding whether to skip or re-analyze it.
        print(f"Analyzing: {job['title']}")

        full_description = fetch_job_description(job)
        if not has_sufficient_description_quality(job, full_description):
            filtered_due_to_description += 1
            print(f"Skipping analysis due to weak description: {job['company']} | {job['title']}")
            if existing_job is not None:
                print(f"Existing job skipped: {job['company']} | {job['title']}")
            print()
            continue

        if existing_job is not None and not should_update_existing_job(
            existing_job,
            job,
            full_description,
        ):
            if should_backfill_existing_job_metadata(existing_job, job):
                # Keep the existing analysis result, but patch in missing
                # metadata fields so old JSON records stay consistent.
                saved_jobs[existing_index] = backfill_existing_job_metadata(existing_job, job)
                print(f"Existing job updated: {job['company']} | {job['title']}")
                print()
                continue

            # This is the main optimization: avoid spending time and tokens on
            # jobs we have already analyzed when the description is unchanged.
            print("Skipping unchanged analyzed job")
            print()
            continue

        # New jobs, or existing jobs with a meaningfully changed description,
        # still go through the full analyzer and overwrite the saved JSON row.
        analysis_result = analyze_job(full_description)
        analyzed_at = _timestamp_now()
        saved_job = prepare_analyzed_job(
            job,
            full_description,
            analysis_result,
            analyzed_at=analyzed_at,
            existing_job=existing_job,
        )

        print(f"Fit Score: {saved_job['fit_score']}")
        newly_analyzed_jobs += 1

        if existing_index is None:
            saved_jobs.append(saved_job)
            saved_jobs_by_key[job_key] = len(saved_jobs) - 1
            print(f"New job added: {job['company']} | {job['title']}")
        else:
            saved_jobs[existing_index] = saved_job
            print(f"Existing job updated: {job['company']} | {job['title']}")
        print()

    save_jobs(saved_jobs, output_path)
    print(f"Pipeline summary: title-qualified jobs={len(raw_jobs)}")
    print(f"Pipeline summary: filtered due to description quality={filtered_due_to_description}")
    print(f"Pipeline summary: analyzed or updated jobs={newly_analyzed_jobs}")
    print(f"Pipeline summary: saved analyzed jobs={len(saved_jobs)}")
    return saved_jobs


if __name__ == "__main__":
    analyze_and_save_jobs()
