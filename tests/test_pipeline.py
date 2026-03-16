"""Tests for backend pipeline helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pipeline
from pipeline import (
    backfill_existing_job_metadata,
    build_job_key,
    fetch_job_description,
    has_sufficient_description_quality,
    is_product_role,
    load_saved_jobs,
    normalize_description_for_comparison,
    prepare_raw_job,
    save_jobs,
    should_backfill_existing_job_metadata,
    should_update_existing_job,
    split_product_jobs,
)


def test_build_job_key_normalizes_case_and_whitespace() -> None:
    job = {
        "company": " OpenAI ",
        "title": " Product Manager ",
        "url": " HTTPS://EXAMPLE.COM/JOB ",
    }

    assert build_job_key(job) == ("openai", "product manager", "https://example.com/job")


def test_load_saved_jobs_returns_empty_list_when_file_is_missing(tmp_path: Path) -> None:
    output_path = tmp_path / "missing.json"

    assert load_saved_jobs(output_path) == []


def test_save_jobs_writes_json_list(tmp_path: Path) -> None:
    output_path = tmp_path / "analyzed_jobs.json"
    jobs = [
        {
            "company": "OpenAI",
            "title": "Product Manager",
            "location": "San Francisco, CA",
            "url": "https://example.com/job",
            "description": "Full description",
            "ownership_score": 9.0,
            "ai_score": 10.0,
            "learning_score": 8.0,
            "prestige_score": 9.0,
            "startup_score": 7.0,
            "comp_score": 9.0,
            "fit_score": 88.5,
            "analysis": "Strong AI product role.",
        }
    ]

    save_jobs(jobs, output_path)

    assert json.loads(output_path.read_text(encoding="utf-8")) == jobs


def test_prepare_raw_job_adds_required_metadata() -> None:
    raw_job = prepare_raw_job(
        {
            "company": "OpenAI",
            "title": "Product Manager",
            "location": "San Francisco",
            "url": "https://example.com/job",
            "description": "Full description",
        },
        fetched_at="2026-03-16T10:00:00+00:00",
    )

    assert raw_job["source"] == "unknown"
    assert raw_job["fetched_at"] == "2026-03-16T10:00:00+00:00"


def test_prepare_analyzed_job_appends_company_context_to_analysis() -> None:
    saved_job = pipeline.prepare_analyzed_job(
        raw_job={
            "company": "OpenAI",
            "title": "Product Manager",
            "location": "San Francisco",
            "url": "https://example.com/job",
            "source": "ashby",
            "fetched_at": "2026-03-16T10:00:00+00:00",
        },
        description="Build AI products.",
        analysis_result={
            "ownership_score": 9.0,
            "ai_score": 9.0,
            "learning_score": 8.0,
            "prestige_score": 8.0,
            "startup_score": 7.0,
            "comp_score": 8.0,
            "fit_score": 84.0,
            "analysis": "Strong fit.",
        },
        analyzed_at="2026-03-16T10:05:00+00:00",
    )

    assert "Strong fit." in saved_job["analysis"]
    assert "Company context:" in saved_job["analysis"]
    assert "- Frontier AI Lab with high research prestige" in saved_job["analysis"]


def test_should_update_existing_job_only_when_description_changed() -> None:
    raw_job = {
        "company": "OpenAI",
        "title": "Product Manager",
        "url": "https://example.com/job",
        "source": "ashby",
        "fetched_at": "2026-03-16T10:00:00+00:00",
    }
    existing_job = {
        "company": "OpenAI",
        "title": "Product Manager",
        "url": "https://example.com/job",
        "description": "Same description",
        "source": "ashby",
        "fetched_at": "2026-03-16T10:00:00+00:00",
        "analyzed_at": "2026-03-16T10:05:00+00:00",
        "ownership_score": 9.0,
        "ai_score": 8.0,
        "learning_score": 7.0,
        "prestige_score": 6.0,
        "startup_score": 5.0,
        "comp_score": 4.0,
        "fit_score": 75.0,
        "analysis": "Stable role.",
    }

    assert should_update_existing_job(existing_job, raw_job, "Same description") is False
    assert should_update_existing_job(existing_job, raw_job, "  same   description\n") is False
    assert should_update_existing_job(existing_job, raw_job, "Updated description") is True


def test_normalize_description_for_comparison_ignores_case_and_whitespace() -> None:
    description = "  Build AI products\nwith customers.  "

    assert normalize_description_for_comparison(description) == "build ai products with customers."


def test_backfill_existing_job_metadata_fills_missing_fields() -> None:
    raw_job = {
        "company": "OpenAI",
        "title": "Product Manager",
        "url": "https://example.com/job",
        "source": "ashby",
        "fetched_at": "2026-03-16T10:00:00+00:00",
    }
    existing_job = {
        "company": "OpenAI",
        "title": "Product Manager",
        "url": "https://example.com/job",
        "description": "Same description",
    }

    assert should_backfill_existing_job_metadata(existing_job, raw_job) is True

    updated_job = backfill_existing_job_metadata(existing_job, raw_job)

    assert updated_job["source"] == "ashby"
    assert updated_job["fetched_at"] == "2026-03-16T10:00:00+00:00"
    assert updated_job["analyzed_at"] == "2026-03-16T10:00:00+00:00"


def test_has_sufficient_description_quality_rejects_javascript_placeholder() -> None:
    job = {
        "company": "OpenAI",
        "title": "Product Manager, Codex",
    }
    description = "Product Manager, Codex @ OpenAI\nYou need to enable JavaScript to run this app."

    assert has_sufficient_description_quality(job, description) is False


def test_has_sufficient_description_quality_rejects_short_descriptions() -> None:
    job = {
        "company": "OpenAI",
        "title": "Product Manager, Codex",
    }
    description = "Own product roadmap for AI tools." * 8

    assert len(description) < 300
    assert has_sufficient_description_quality(job, description) is False


def test_has_sufficient_description_quality_rejects_common_placeholder_markers() -> None:
    job = {
        "company": "OpenAI",
        "title": "Product Manager, Codex",
    }
    description = (
        "Product Manager, Codex @ OpenAI\n"
        "Loading job post now. Click here to continue and apply on company website."
        " This role would otherwise look detailed, but the placeholder markers should still fail."
        " Additional filler text keeps the string long enough to isolate marker-based filtering."
        " More filler text keeps the string above the minimum character threshold for validation."
    )

    assert len(description) >= 300
    assert has_sufficient_description_quality(job, description) is False


def test_fetch_job_description_prefers_existing_strong_description() -> None:
    job = {
        "company": "OpenAI",
        "title": "Product Manager, Codex",
        "url": "https://example.com/job",
        "description": (
            "About the role\n"
            "You will define product strategy, partner with engineering, own roadmap decisions, "
            "and translate user research into product requirements for AI-powered developer tools."
        ),
    }

    assert fetch_job_description(job) == job["description"]


def test_is_product_role_keeps_titles_without_engineering_or_research_terms() -> None:
    assert is_product_role({"title": "Staff Product Manager"}) is True
    assert is_product_role({"title": "AI Product Manager"}) is True
    assert is_product_role({"title": "Product Director, Platform"}) is True
    assert is_product_role({"title": "Senior Product Manager"}) is True
    assert is_product_role({"title": "Growth Lead"}) is True
    assert is_product_role({"title": "Platform Lead"}) is True
    assert is_product_role({"title": "Head of Product"}) is True
    assert is_product_role({"title": "Founding PM"}) is True
    assert is_product_role({"title": "AI Platform Lead"}) is True


def test_is_product_role_excludes_titles_with_engineering_or_research_terms() -> None:
    blocked_titles = [
        "Engineering Program Manager",
        "Product Engineer",
        "Applied Scientist, Product",
        "Distinguished Engineer",
        "ML Engineer",
        "Research Scientist",
        "UX Researcher",
        "Software Engineer",
        "Staff Engineer",
        "Principal Engineer",
    ]

    for title in blocked_titles:
        assert is_product_role({"title": title}) is False


def test_split_product_jobs_separates_kept_and_excluded_roles() -> None:
    jobs = [
        {"title": "Senior Product Manager"},
        {"title": "Software Engineer"},
        {"title": "Growth Lead"},
        {"title": "UX Researcher"},
    ]

    kept_jobs, excluded_jobs, exclusion_counts = split_product_jobs(jobs)

    assert [job["title"] for job in kept_jobs] == [
        "Senior Product Manager",
        "Growth Lead",
    ]
    assert [job["title"] for job in excluded_jobs] == [
        "Software Engineer",
        "UX Researcher",
    ]
    assert exclusion_counts == {
        "engineering or research title": 2,
    }


def test_analyze_and_save_jobs_skips_weak_descriptions(
    monkeypatch: object,
    tmp_path: Path,
    capsys: object,
) -> None:
    weak_job = {
        "company": "OpenAI",
        "title": "Product Manager, Codex",
        "location": "San Francisco",
        "url": "https://jobs.ashbyhq.com/OpenAI/example",
        "description": "Product Manager, Codex @ OpenAI\nYou need to enable JavaScript to run this app.",
        "source": "ashby",
    }

    def fake_collect_product_jobs(companies_path: str = "data/companies.yaml") -> list[dict]:
        return [weak_job]

    def fail_analyze_job(job_description: str) -> dict:
        raise AssertionError("analyze_job should not run for weak descriptions")

    monkeypatch.setattr(pipeline, "collect_product_jobs", fake_collect_product_jobs)
    monkeypatch.setattr(pipeline, "analyze_job", fail_analyze_job)

    saved_jobs = pipeline.analyze_and_save_jobs(output_path=tmp_path / "analyzed_jobs.json")

    assert saved_jobs == []
    captured = capsys.readouterr().out
    assert "Pipeline summary: filtered due to description quality=1" in captured


def test_analyze_and_save_jobs_saves_raw_and_adds_new_analyzed_job(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    job = {
        "company": "OpenAI",
        "title": "Product Manager, Codex",
        "location": "San Francisco",
        "url": "https://jobs.example.com/openai/codex-pm",
        "description": "Initial description",
        "source": "ashby",
    }
    analysis_result = {
        "ownership_score": 9.0,
        "ai_score": 9.0,
        "learning_score": 8.0,
        "prestige_score": 8.0,
        "startup_score": 7.0,
        "comp_score": 8.0,
        "fit_score": 84.0,
        "analysis": "Strong fit.",
    }

    def fake_collect_product_jobs(companies_path: str = "data/companies.yaml") -> list[dict]:
        return [job]

    monkeypatch.setattr(pipeline, "collect_product_jobs", fake_collect_product_jobs)
    monkeypatch.setattr(pipeline, "fetch_job_description", lambda current_job: current_job["description"])
    monkeypatch.setattr(pipeline, "analyze_job", lambda job_description: analysis_result)

    analyzed_path = tmp_path / "analyzed_jobs.json"
    raw_path = tmp_path / "raw_jobs.json"
    saved_jobs = pipeline.analyze_and_save_jobs(
        output_path=analyzed_path,
        raw_output_path=raw_path,
    )

    raw_jobs = json.loads(raw_path.read_text(encoding="utf-8"))
    assert len(raw_jobs) == 1
    assert raw_jobs[0]["source"] == "ashby"
    assert "fetched_at" in raw_jobs[0]

    assert len(saved_jobs) == 1
    assert saved_jobs[0]["description"] == "Initial description"
    assert saved_jobs[0]["source"] == "ashby"
    assert "fetched_at" in saved_jobs[0]
    assert "analyzed_at" in saved_jobs[0]
    assert "Company context:" in saved_jobs[0]["analysis"]


def test_analyze_and_save_jobs_skips_existing_unchanged_job(
    monkeypatch: object,
    tmp_path: Path,
    capsys: object,
) -> None:
    existing_job = {
        "company": "OpenAI",
        "title": "Product Manager, Codex",
        "location": "San Francisco",
        "url": "https://jobs.example.com/openai/codex-pm",
        "description": "Stable description",
        "source": "ashby",
        "fetched_at": "2026-03-16T10:00:00+00:00",
        "analyzed_at": "2026-03-16T10:05:00+00:00",
        "ownership_score": 9.0,
        "ai_score": 9.0,
        "learning_score": 8.0,
        "prestige_score": 8.0,
        "startup_score": 7.0,
        "comp_score": 8.0,
        "fit_score": 84.0,
        "analysis": "Strong fit.",
    }
    current_job = {
        "company": "OpenAI",
        "title": "Product Manager, Codex",
        "location": "San Francisco",
        "url": "https://jobs.example.com/openai/codex-pm",
        "description": "Stable description",
        "source": "ashby",
    }

    save_jobs([existing_job], tmp_path / "analyzed_jobs.json")

    def fake_collect_product_jobs(companies_path: str = "data/companies.yaml") -> list[dict]:
        return [current_job]

    def fail_analyze_job(job_description: str) -> dict:
        raise AssertionError("analyze_job should not run for unchanged jobs")

    monkeypatch.setattr(pipeline, "collect_product_jobs", fake_collect_product_jobs)
    monkeypatch.setattr(pipeline, "fetch_job_description", lambda job: job["description"])
    monkeypatch.setattr(pipeline, "analyze_job", fail_analyze_job)

    saved_jobs = pipeline.analyze_and_save_jobs(
        output_path=tmp_path / "analyzed_jobs.json",
        raw_output_path=tmp_path / "raw_jobs.json",
    )

    assert len(saved_jobs) == 1
    assert saved_jobs[0]["analyzed_at"] == "2026-03-16T10:05:00+00:00"
    assert "Skipping unchanged analyzed job" in capsys.readouterr().out


def test_analyze_and_save_jobs_updates_existing_job_when_description_changes(
    monkeypatch: object,
    tmp_path: Path,
    capsys: object,
) -> None:
    existing_job = {
        "company": "OpenAI",
        "title": "Product Manager, Codex",
        "location": "San Francisco",
        "url": "https://jobs.example.com/openai/codex-pm",
        "description": "Old description",
        "source": "ashby",
        "fetched_at": "2026-03-16T10:00:00+00:00",
        "analyzed_at": "2026-03-16T10:05:00+00:00",
        "ownership_score": 9.0,
        "ai_score": 9.0,
        "learning_score": 8.0,
        "prestige_score": 8.0,
        "startup_score": 7.0,
        "comp_score": 8.0,
        "fit_score": 84.0,
        "analysis": "Strong fit.",
    }
    current_job = {
        "company": "OpenAI",
        "title": "Product Manager, Codex",
        "location": "San Francisco",
        "url": "https://jobs.example.com/openai/codex-pm",
        "description": "New description",
        "source": "ashby",
    }
    updated_analysis = {
        "ownership_score": 10.0,
        "ai_score": 9.0,
        "learning_score": 9.0,
        "prestige_score": 8.0,
        "startup_score": 7.0,
        "comp_score": 8.0,
        "fit_score": 90.0,
        "analysis": "Improved fit.",
    }

    save_jobs([existing_job], tmp_path / "analyzed_jobs.json")

    def fake_collect_product_jobs(companies_path: str = "data/companies.yaml") -> list[dict]:
        return [current_job]

    monkeypatch.setattr(pipeline, "collect_product_jobs", fake_collect_product_jobs)
    monkeypatch.setattr(pipeline, "fetch_job_description", lambda job: job["description"])
    monkeypatch.setattr(pipeline, "analyze_job", lambda job_description: updated_analysis)

    saved_jobs = pipeline.analyze_and_save_jobs(
        output_path=tmp_path / "analyzed_jobs.json",
        raw_output_path=tmp_path / "raw_jobs.json",
    )

    assert len(saved_jobs) == 1
    assert saved_jobs[0]["description"] == "New description"
    assert saved_jobs[0]["fit_score"] == 90.0
    assert "fetched_at" in saved_jobs[0]
    assert "Company context:" in saved_jobs[0]["analysis"]
    captured = capsys.readouterr().out
    assert "Pipeline summary: analyzed or updated jobs=1" in captured
