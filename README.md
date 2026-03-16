# Opportunity Radar

Opportunity Radar is a small Streamlit app that analyzes product manager job descriptions with the OpenAI API and returns a structured score.

The project also includes a first-pass company tracker that fetches product-related jobs from a small list of AI companies using public ATS endpoints.

## Features

- Paste a job description into the UI
- Analyze the role with OpenAI
- Score the role across six dimensions
- Calculate a weighted overall fit score
- Track product jobs from Greenhouse, Lever, and Ashby career pages

## Project Files

- `app.py`: Streamlit user interface
- `analyzer.py`: Calls OpenAI and parses the JSON response
- `scoring.py`: Calculates the weighted fit score
- `prompts.py`: Stores the analysis prompt template
- `config.py`: Loads environment variables and shared constants
- `pipeline.py`: Loads tracked companies and prints matching product jobs
- `trackers/`: ATS-specific company trackers
- `data/companies.yaml`: Example tracked AI companies

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

## Run the App

```bash
streamlit run app.py
```

## Run the Company Tracker

The tracker loads companies from `data/companies.yaml`, fetches public job postings, and prints product-related matches.

```bash
python3 pipeline.py
```

You can edit `data/companies.yaml` to add or remove tracked companies. Each entry should include:

- `name`
- `ats`
- `careers_url`

## Output Fields

The app returns:

- `company`
- `title`
- `cleaned_description`
- `ownership_score`
- `ai_score`
- `learning_score`
- `prestige_score`
- `startup_score`
- `comp_score`
- `fit_score`
- `analysis`
