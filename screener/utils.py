"""
Gemini API integration for resume analysis.

Sends the job description and resume text to Google's Gemini 2.5 Flash model
and returns a structured JSON analysis.
"""

import json
import logging
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Expected keys in Gemini response ─────────────────────────
REQUIRED_KEYS = {
    "match_score",
    "matched_skills",
    "missing_skills",
    "summary",
    "improvements",
    "rewritten_bullets",
    "ats_keywords",
}

PROMPT_TEMPLATE = """You are an expert career coach and ATS (Applicant Tracking System) specialist.

Analyze the following resume against the provided job description and return a JSON object with EXACTLY these keys:

1. "match_score": integer 0–100 representing overall match percentage.
2. "matched_skills": list of strings — skills/technologies present in BOTH the resume and job description.
3. "missing_skills": list of strings — skills/technologies required by the JD but MISSING from the resume.
4. "summary": a 2–3 sentence professional summary tailored to this specific job.
5. "improvements": list of 3–5 actionable suggestions to improve the resume for this role.
6. "rewritten_bullets": list of 2–3 objects, each with "before" (an existing bullet from the resume) and "after" (an improved, quantified version targeting this JD).
7. "ats_keywords": list of 5–10 important keywords/phrases from the JD that should appear in the resume for ATS compatibility.

===== JOB DESCRIPTION =====
{job_description}

===== RESUME =====
{resume_text}

Return ONLY valid JSON. No markdown, no explanation, no code fences."""


def analyze_resume(job_description: str, resume_text: str) -> dict:
    """
    Call Gemini 2.5 Flash and return the parsed analysis dict.

    Raises ValueError on configuration or parsing errors.
    Raises RuntimeError on API communication failures.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    prompt = PROMPT_TEMPLATE.format(
        job_description=job_description,
        resume_text=resume_text,
    )

    # Try up to 2 times
    last_error = None
    for attempt in range(2):
        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()
            # Remove possible markdown fences
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                raw = raw.rsplit("```", 1)[0]
            data = json.loads(raw)
            break
        except json.JSONDecodeError as exc:
            last_error = exc
            logger.warning("Attempt %d: Invalid JSON from Gemini: %s", attempt + 1, exc)
        except Exception as exc:
            last_error = exc
            logger.warning("Attempt %d: Gemini API error: %s", attempt + 1, exc)
    else:
        raise RuntimeError(
            f"Gemini API failed after 2 attempts: {last_error}"
        )

    # Validate keys
    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        logger.warning("Gemini response missing keys: %s — filling defaults", missing)
        defaults = {
            "match_score": 0,
            "matched_skills": [],
            "missing_skills": [],
            "summary": "",
            "improvements": [],
            "rewritten_bullets": [],
            "ats_keywords": [],
        }
        for key in missing:
            data[key] = defaults[key]

    # Clamp score
    data["match_score"] = max(0, min(100, int(data["match_score"])))

    return data