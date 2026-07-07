"""
Groq AI Agent for resume analysis.
Uses Groq's high-speed models via OpenAI-compatible API to extract
structured skills, highlights, and ATS score from raw resume text.

Get your FREE API key at: https://console.groq.com/
"""

import json
import logging
import os
import re
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from models import (
    ATSScoreBreakdown,
    ATSSubscore,
    Highlight,
    ImprovementTip,
    ResumeAnalysisResponse,
    SkillsBreakdown,
)

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Grok client setup
# ---------------------------------------------------------------------------

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Return a cached Groq API client."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key or api_key.startswith("your_"):
            raise ValueError(
                "GROQ_API_KEY is not set. "
                "Get your key at https://console.groq.com/ and add it to the .env file."
            )
        _client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    return _client


# ---------------------------------------------------------------------------
# Prompt engineering
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an elite resume analysis AI and ATS (Applicant Tracking System) expert with 15+ years of experience in HR and talent acquisition.

Your task is to analyze the given resume text and return a **single JSON object** — no markdown, no code blocks, no extra text — strictly following the schema below.

JSON SCHEMA:
{
  "candidate_name": "string or null",
  "candidate_title": "string or null",
  "summary": "string (2-3 sentence professional summary)",
  "total_experience_years": number or null,
  "skills": {
    "technical": ["list of technical skills"],
    "tools": ["list of tools and software"],
    "soft_skills": ["list of soft skills"],
    "domain_expertise": ["list of domain/industry knowledge areas"]
  },
  "highlights": [
    {
      "category": "Work Experience | Education | Project | Certification | Achievement",
      "title": "string",
      "description": "string",
      "impact": "string or null (quantified impact if present)"
    }
  ],
  "ats_score": {
    "overall": integer (0-100),
    "grade": "A+ | A | B+ | B | C+ | C | D | F",
    "summary": "string (paragraph explaining the ATS compatibility)",
    "subscores": [
      {
        "label": "Keywords & Skills Match",
        "score": integer (0-30),
        "max_score": 30,
        "feedback": "string"
      },
      {
        "label": "Quantified Achievements",
        "score": integer (0-25),
        "max_score": 25,
        "feedback": "string"
      },
      {
        "label": "Format & Structure",
        "score": integer (0-20),
        "max_score": 20,
        "feedback": "string"
      },
      {
        "label": "Completeness of Sections",
        "score": integer (0-15),
        "max_score": 15,
        "feedback": "string"
      },
      {
        "label": "Readability & Action Verbs",
        "score": integer (0-10),
        "max_score": 10,
        "feedback": "string"
      }
    ]
  },
  "improvement_tips": [
    {
      "priority": "High | Medium | Low",
      "area": "string",
      "suggestion": "string (actionable, specific advice)"
    }
  ]
}

ATS SCORING RUBRIC:
- Keywords & Skills Match (0–30): Presence of relevant industry keywords, technical skills with appropriate context
- Quantified Achievements (0–25): Use of numbers, percentages, dollar amounts to demonstrate impact
- Format & Structure (0–20): Clear section headers, bullet points, no tables/columns that break ATS parsing
- Completeness of Sections (0–15): Has Contact Info, Summary, Experience, Education, Skills sections
- Readability & Action Verbs (0–10): Strong action verbs, concise bullets, no grammar errors

GRADE SCALE: 90-100=A+, 80-89=A, 70-79=B+, 60-69=B, 50-59=C+, 40-49=C, 30-39=D, 0-29=F

IMPORTANT:
- Return ONLY valid JSON. No markdown. No explanations outside the JSON.
- Be comprehensive — extract ALL skills mentioned anywhere in the resume.
- Extract at least 3-5 highlights covering different categories.
- Provide 3-5 improvement tips ordered by priority.
- The "overall" score must equal the sum of all subscore values.
"""

USER_PROMPT_TEMPLATE = """Analyze this resume and return the structured JSON:

--- RESUME START ---
{resume_text}
--- RESUME END ---"""


# ---------------------------------------------------------------------------
# Main agent function
# ---------------------------------------------------------------------------

def analyze_resume(resume_text: str) -> ResumeAnalysisResponse:
    """
    Send resume text to Grok and return a structured analysis.

    Args:
        resume_text: Plain text extracted from the resume file.

    Returns:
        ResumeAnalysisResponse with skills, highlights, and ATS score.

    Raises:
        ValueError: If the AI returns invalid JSON or the API call fails.
    """
    client = get_client()
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    max_tokens = int(os.getenv("MAX_TOKENS", "4096"))

    # Truncate very long resumes to avoid token limits (keep ~8000 chars)
    if len(resume_text) > 8000:
        logger.warning("Resume text truncated from %d to 8000 characters.", len(resume_text))
        resume_text = resume_text[:8000] + "\n\n[... resume truncated for processing ...]"

    logger.info("Sending resume to Groq model: %s", model)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(resume_text=resume_text)},
        ],
        max_tokens=max_tokens,
        temperature=0.2,  # Low temp for consistent, structured output
    )

    raw_content = response.choices[0].message.content.strip()
    logger.debug("Raw Grok response: %s", raw_content[:500])

    # Strip markdown code fences if model wraps response anyway
    raw_content = _strip_code_fences(raw_content)

    # Parse JSON
    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Grok JSON response: %s\nContent: %s", e, raw_content[:1000])
        raise ValueError(f"AI returned invalid JSON: {e}")

    return _build_response(data)


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) if present."""
    pattern = r"^```(?:json)?\s*(.*?)\s*```$"
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _build_response(data: dict) -> ResumeAnalysisResponse:
    """Map raw JSON dict to typed Pydantic models."""
    skills_data = data.get("skills", {})
    skills = SkillsBreakdown(
        technical=skills_data.get("technical", []),
        tools=skills_data.get("tools", []),
        soft_skills=skills_data.get("soft_skills", []),
        domain_expertise=skills_data.get("domain_expertise", []),
    )

    highlights = [
        Highlight(
            category=h.get("category", "General"),
            title=h.get("title", ""),
            description=h.get("description", ""),
            impact=h.get("impact"),
        )
        for h in data.get("highlights", [])
    ]

    ats_raw = data.get("ats_score", {})
    subscores = [
        ATSSubscore(
            label=s.get("label", ""),
            score=int(s.get("score", 0)),
            max_score=int(s.get("max_score", 100)),
            feedback=s.get("feedback", ""),
        )
        for s in ats_raw.get("subscores", [])
    ]

    overall = int(ats_raw.get("overall", sum(s.score for s in subscores)))
    grade = ats_raw.get("grade", _score_to_grade(overall))

    ats_score = ATSScoreBreakdown(
        overall=overall,
        grade=grade,
        subscores=subscores,
        summary=ats_raw.get("summary", ""),
    )

    tips = [
        ImprovementTip(
            priority=t.get("priority", "Medium"),
            area=t.get("area", ""),
            suggestion=t.get("suggestion", ""),
        )
        for t in data.get("improvement_tips", [])
    ]

    return ResumeAnalysisResponse(
        candidate_name=data.get("candidate_name"),
        candidate_title=data.get("candidate_title"),
        summary=data.get("summary", ""),
        skills=skills,
        highlights=highlights,
        ats_score=ats_score,
        improvement_tips=tips,
        total_experience_years=data.get("total_experience_years"),
    )


def _score_to_grade(score: int) -> str:
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B+"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C+"
    elif score >= 40:
        return "C"
    elif score >= 30:
        return "D"
    return "F"


# ---------------------------------------------------------------------------
# Resume Converter — prompts + agent function
# ---------------------------------------------------------------------------

CONVERT_SYSTEM_PROMPT = """You are an expert resume formatter. Your task is to extract ALL information from the given resume and restructure it into a specific professional template format.

You must return a SINGLE valid JSON object — no markdown, no code fences, no extra text.

TARGET TEMPLATE FORMAT (match this structure exactly):
The template follows this layout:
1. name: Candidate's full name
2. phone: Phone number (or null)
3. email: Email address (or null)
4. linkedin: LinkedIn URL (or null)
5. specialization: Pipe-separated expertise titles, e.g. "Salesforce ADM | Sales Cloud | Service Cloud"
6. professional_summary: 5-8 concise bullet points highlighting key experience and expertise
7. technical_skills: Bullet points grouped by category, e.g. "CRM – Salesforce, Veeva, Conga"
8. professional_experience: Each job listed with role, client/company, date range, and 4-8 responsibility bullets
9. other_experience: Older or less-detailed roles listed briefly (role, company, date range only)
10. education: Degree lines, e.g. "Master of Computer Applications - University of the Punjab (2007)"
11. certifications: Certification names as bullet points

RULES:
- Extract ALL work experience from the resume without omitting any
- Detailed recent roles go in professional_experience; brief older roles go in other_experience
- Generate a professional_summary if the resume does not have one, based on the experience
- Organize technical skills into logical categories (CRM, Programming Languages, Cloud Platforms, Tools, etc.)
- Keep bullet points concise and action-oriented
- If information is missing (e.g. no LinkedIn), set that field to null
- Return ONLY valid JSON with this exact schema:

{
  "name": "string",
  "phone": "string or null",
  "email": "string or null",
  "linkedin": "string or null",
  "specialization": "string or null",
  "professional_summary": ["bullet 1", "bullet 2", ...],
  "technical_skills": ["Category – tool1, tool2", ...],
  "professional_experience": [
    {
      "role": "string",
      "client": "string",
      "date_range": "string",
      "responsibilities": ["bullet 1", "bullet 2", ...]
    }
  ],
  "other_experience": [
    {
      "role": "string",
      "company": "string",
      "date_range": "string"
    }
  ],
  "education": ["string"],
  "certifications": ["string"]
}"""

CONVERT_USER_PROMPT = """Restructure this resume into the template format and return JSON:

--- RESUME START ---
{resume_text}
--- RESUME END ---"""


def convert_resume(resume_text: str) -> dict:
    """
    Send resume text to Groq and return a structured dict matching
    the ConvertedResumeData schema (template format).

    Args:
        resume_text: Plain text extracted from the uploaded resume.

    Returns:
        Dict matching ConvertedResumeData structure.

    Raises:
        ValueError: If AI returns invalid JSON or API call fails.
    """
    client = get_client()
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    max_tokens = int(os.getenv("MAX_TOKENS", "4096"))

    if len(resume_text) > 8000:
        logger.warning("Resume text truncated from %d to 8000 chars for conversion.", len(resume_text))
        resume_text = resume_text[:8000] + "\n\n[... resume truncated ...]"

    logger.info("Converting resume with Groq model: %s", model)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": CONVERT_SYSTEM_PROMPT},
            {"role": "user",   "content": CONVERT_USER_PROMPT.format(resume_text=resume_text)},
        ],
        max_tokens=max_tokens,
        temperature=0.1,  # Very low — we want deterministic structured output
    )

    raw = response.choices[0].message.content.strip()
    raw = _strip_code_fences(raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Conversion JSON parse error: %s\nContent: %s", e, raw[:500])
        raise ValueError(f"AI returned invalid JSON during conversion: {e}")

    logger.info("Conversion complete — %d experience entries, %d skills",
                len(data.get("professional_experience", [])),
                len(data.get("technical_skills", [])))
    return data

