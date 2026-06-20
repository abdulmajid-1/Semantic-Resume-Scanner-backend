"""
Pydantic schemas for Resumes.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ResumeUploadResponse(BaseModel):
    id: int
    user_id: int
    file_path: str
    file_type: str
    parsed_name: Optional[str] = None
    parsed_email: Optional[str] = None
    parsed_phone: Optional[str] = None
    years_of_experience: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class EducationEntry(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[str] = None


class ExperienceEntry(BaseModel):
    role: Optional[str] = None
    company: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None


class ProjectEntry(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ResumeDetailResponse(BaseModel):
    id: int
    user_id: int
    file_path: str
    file_type: str
    parsed_name: Optional[str] = None
    parsed_email: Optional[str] = None
    parsed_phone: Optional[str] = None
    education: Optional[List[Dict[str, Any]]] = None
    experience: Optional[List[Dict[str, Any]]] = None
    projects: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[str]] = None
    years_of_experience: int = 0
    skills: List[str] = []
    raw_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
