# Repository Guidelines

## Project Structure & Module Organization
Opportunity Radar is a Python + Streamlit application for discovering and ranking product manager roles at AI companies. Keep app code in `src/opportunity_radar/`, with Streamlit entrypoints in `app/` such as `app/Home.py` or `app/pages/01_Jobs.py`. Put integration logic for job boards, company enrichment, and ranking models in `src/opportunity_radar/services/`. Store reusable prompts, fixtures, or seed data in `assets/`, and keep tests in `tests/` with matching module paths.

## Build, Test, and Development Commands
Use a local virtual environment before installing dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/Home.py
pytest
ruff check .
ruff format .
```

`streamlit run` starts the UI locally. `pytest` runs unit and integration tests. `ruff check` enforces lint rules; `ruff format` applies consistent formatting. If a `Makefile` or `pyproject.toml` is added later, keep these commands aliased there as the canonical entrypoints.

## Coding Style & Naming Conventions
Target Python 3.11+ and use 4-space indentation. Prefer type hints on public functions and dataclasses or Pydantic models for structured job, company, and scoring data. Use `snake_case` for modules, functions, and variables, `PascalCase` for classes, and short descriptive page names for Streamlit files. Keep side effects out of ranking logic so scoring code remains testable.

## Testing Guidelines
Write tests with `pytest`. Name files `test_<module>.py` and mirror the source layout, for example `tests/services/test_ranker.py`. Cover parsing, scoring, and filtering logic first; UI tests are secondary. Add fixtures for sample job posts and company metadata instead of relying on live APIs. New ranking or filtering behavior should ship with at least one deterministic test.

## Commit & Pull Request Guidelines
No local Git history is present in this workspace, so adopt concise imperative commits such as `feat: add greenhouse scraper` or `fix: handle duplicate job URLs`. Keep pull requests focused, describe user-facing impact, list validation steps, and attach screenshots for Streamlit UI changes. Link related issues or task IDs when available.

## Security & Configuration Tips
Keep API keys and model credentials in `.env` and never commit them. Document required environment variables in `README.md` and provide safe defaults for local development. Cache external requests where practical to avoid rate-limit issues during testing.
