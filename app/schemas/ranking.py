"""
Pydantic schemas for Ranking, Matching, and Suggestions.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class MatchRequest(BaseModel):
    job_id: int


class CandidateRank(BaseModel):
    application_id: int
    candidate_id: int
    candidate_name: str
    resume_id: int
    semantic_score: float
    skill_score: float
    experience_score: float
    final_score: float
    rank_position: Optional[int] = None
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    explanation: Optional[str] = None
    applied_at: datetime


class RankingResponse(BaseModel):
    job_id: int
    job_title: str
    rankings: List[CandidateRank]


class Recommendation(BaseModel):
    title: str
    description: str
    type: str  # "skill", "certification", "experience", "project", "general"
