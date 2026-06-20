"""
Pydantic schemas for Job Descriptions.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class JobCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=10)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    experience_required: int = Field(default=0, ge=0)
    location: Optional[str] = Field(None, max_length=100)


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, min_length=10)
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    experience_required: Optional[int] = Field(None, ge=0)
    location: Optional[str] = None
    is_active: Optional[bool] = None


class JobResponse(BaseModel):
    id: int
    recruiter_id: int
    title: str
    description: str
    required_skills: Optional[List[str]] = []
    preferred_skills: Optional[List[str]] = []
    experience_required: int
    location: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
