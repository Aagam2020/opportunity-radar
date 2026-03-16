"""Prompt templates used by the OpenAI analyzer."""

from __future__ import annotations

from config import SCORE_WEIGHTS


def build_analysis_prompt(job_description: str) -> str:
    """Create the prompt sent to the model.

    The model is asked for strict JSON so the UI can parse and display the result.
    """
    return f"""
You are an expert career analyst focused on AI product management roles.

Evaluate the following job description and return a JSON object only.

Scoring dimensions and weights:
- Product Ownership Scope: {SCORE_WEIGHTS["ownership_score"]}
- AI Relevance: {SCORE_WEIGHTS["ai_score"]}
- Learning Opportunity: {SCORE_WEIGHTS["learning_score"]}
- Company Prestige: {SCORE_WEIGHTS["prestige_score"]}
- Startup Upside: {SCORE_WEIGHTS["startup_score"]}
- Compensation Potential: {SCORE_WEIGHTS["comp_score"]}

Instructions:
- Score each dimension from 0 to 10.
- Base your answer only on the job description and reasonable inference from the text itself.
- Keep the analysis concise but useful.
- Extract the company name if it appears anywhere in the job description. If it does not appear, return "Unknown".
- Extract the job title from the posting. If unclear, return the best likely title and mention uncertainty in the analysis.
- Produce a `cleaned_description` field that removes legal boilerplate, equal opportunity statements, immigration or accommodation notices, generic benefits disclaimers, and repetitive application instructions. Keep only the role, team, product, impact, responsibilities, qualifications, and business context.
- Preserve the meaning of the description when cleaning it; do not summarize beyond removing boilerplate.
- For `ai_score`, reward direct involvement with AI systems, machine learning products, LLMs, generative AI, model tooling, inference platforms, data labeling for models, AI safety, evaluation, prompt systems, or shipping ML-powered user experiences.
- Do not over-score jobs that only mention analytics, dashboards, automation, or data infrastructure unless the role clearly works on AI/ML systems.
- Give especially high `ai_score` values to roles that own ML models, LLM applications, retrieval systems, agentic workflows, model evaluation, training data, or AI platform capabilities.
- `analysis` should explain the title/company extraction if uncertain, note why the role is or is not AI-relevant, and briefly justify the highest-impact scores.

Return this exact JSON shape:
{{
  "company": "string",
  "title": "string",
  "cleaned_description": "string",
  "ownership_score": 0,
  "ai_score": 0,
  "learning_score": 0,
  "prestige_score": 0,
  "startup_score": 0,
  "comp_score": 0,
  "analysis": "short explanation"
}}

Job description:
\"\"\"
{job_description}
\"\"\"
""".strip()


def build_resume_tailoring_prompt(
    *,
    title: str,
    company: str,
    description: str,
    fit_score: float,
    analysis: str,
    user_profile_summary: str = "",
) -> str:
    """Create the prompt used for on-demand resume tailoring guidance."""
    personalization_block = ""
    if user_profile_summary.strip():
        personalization_block = f"""
Candidate profile:
{user_profile_summary}

Personalization instructions:
- Use the candidate profile to tailor the guidance to the candidate's background, target roles, strengths, and likely transferable experience.
- Ground recommendations in the profile details instead of defaulting to generic PM language.
- If the profile does not perfectly match the role, emphasize the most relevant overlap and transferable experience honestly.
""".strip()
    else:
        personalization_block = """
Candidate profile:
Not provided.

Personalization instructions:
- No saved candidate profile is available, so generate useful generic guidance grounded only in the role details.
""".strip()

    return f"""
You are an expert resume strategist for product management candidates targeting AI companies.

Generate structured resume-tailoring guidance for one specific role and return a JSON object only.

Instructions:
- Base the guidance on the provided role details, saved job analysis, and candidate profile when available.
- Keep each `resume_highlights` bullet specific and action-oriented.
- Return 3 to 5 items in `resume_highlights`.
- Return a short list for `key_skills_to_surface`.
- Keep `outreach_angle` to 1 to 2 sentences.
- Keep `why_you_match` to 2 to 3 sentences.
- Do not reproduce the full candidate profile verbatim.
- Do not mention missing candidate information. Focus on what to emphasize and how to frame fit.

Return this exact JSON shape:
{{
  "resume_highlights": ["bullet 1", "bullet 2", "bullet 3"],
  "key_skills_to_surface": ["skill 1", "skill 2", "skill 3"],
  "outreach_angle": "1 to 2 sentences",
  "why_you_match": "2 to 3 sentences"
}}

Role details:
- Company: {company}
- Title: {title}
- Fit score: {fit_score:.1f}/100
- Saved analysis: {analysis}

{personalization_block}

Job description:
\"\"\"
{description}
\"\"\"
""".strip()
