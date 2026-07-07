"""
Pydantic models for the Resume Parser AI Agent.
Defines all request/response data structures used across the app.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class SkillsBreakdown(BaseModel):
    """Categorized skills extracted from the resume."""
    technical: List[str] = Field(default_factory=list, description="Programming languages, frameworks, databases, cloud platforms, etc.")
    tools: List[str] = Field(default_factory=list, description="Software tools, IDEs, version control, CI/CD tools, etc.")
    soft_skills: List[str] = Field(default_factory=list, description="Communication, leadership, problem-solving, etc.")
    domain_expertise: List[str] = Field(default_factory=list, description="Industry/domain-specific knowledge areas.")


class ATSSubscore(BaseModel):
    """A single ATS scoring dimension."""
    label: str
    score: int = Field(ge=0, le=100)
    max_score: int
    feedback: str


class ATSScoreBreakdown(BaseModel):
    """Full ATS score with dimension-level breakdown."""
    overall: int = Field(ge=0, le=100, description="Overall ATS score out of 100.")
    grade: str = Field(description="Letter grade: A+, A, B+, B, C+, C, D, F")
    subscores: List[ATSSubscore]
    summary: str = Field(description="One-paragraph summary of ATS compatibility.")


class Highlight(BaseModel):
    """A single key highlight or achievement from the resume."""
    category: str = Field(description="e.g. Work Experience, Education, Project, Certification, Achievement")
    title: str
    description: str
    impact: Optional[str] = Field(None, description="Quantified impact, if any (e.g., '↑ 40% performance')")


class ImprovementTip(BaseModel):
    """An actionable improvement suggestion."""
    priority: str = Field(description="High / Medium / Low")
    area: str = Field(description="e.g. Keywords, Formatting, Quantification")
    suggestion: str


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------

class ResumeAnalysisResponse(BaseModel):
    """Complete analysis result returned by the AI agent."""
    candidate_name: Optional[str] = Field(None, description="Extracted candidate name, if found.")
    candidate_title: Optional[str] = Field(None, description="Current or target job title.")
    summary: str = Field(description="2–3 sentence professional summary of the candidate.")
    skills: SkillsBreakdown
    highlights: List[Highlight]
    ats_score: ATSScoreBreakdown
    improvement_tips: List[ImprovementTip]
    total_experience_years: Optional[float] = Field(None, description="Estimated years of experience.")


# ---------------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None


# ---------------------------------------------------------------------------
# Resume Conversion models
# ---------------------------------------------------------------------------

class ExperienceEntry(BaseModel):
    """One professional experience role in the converted resume."""
    role: str = Field(description="Job title, e.g. 'Salesforce Marketing Consultant'")
    client: str = Field(description="Company / client name")
    date_range: str = Field(description="e.g. 'Jan 2020 – Dec 2022'")
    responsibilities: List[str] = Field(default_factory=list, description="Bullet-point responsibilities")


class OtherExperience(BaseModel):
    """Brief entry for older / less-detailed experience."""
    role: str
    company: str
    date_range: str


class ConvertedResumeData(BaseModel):
    """Structured resume content formatted to match the HAIRAT template."""
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    linkedin: Optional[str] = None
    specialization: Optional[str] = Field(
        None,
        description="Pipe-separated title line, e.g. 'Salesforce ADM | Sales Cloud | Service Cloud'"
    )
    professional_summary: List[str] = Field(default_factory=list)
    technical_skills: List[str] = Field(
        default_factory=list,
        description="Each item is 'Category – tool1, tool2' format"
    )
    professional_experience: List[ExperienceEntry] = Field(default_factory=list)
    other_experience: List[OtherExperience] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list, description="e.g. 'Master of CS - MIT (2015)'")
    certifications: List[str] = Field(default_factory=list)

