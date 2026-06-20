"""
Pydantic schemas for FAISS Semantic Search.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=2, max_length=200)
    top_k: int = Field(default=5, ge=1, le=50)


class SearchResult(BaseModel):
    resume_id: int
    candidate_id: int
    candidate_name: str
    file_type: str
    skills: List[str]
    years_of_experience: int
    similarity_score: float
