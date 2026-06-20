"""
Skill models — stores the master skill list and junction tables linking
skills to candidates (resumes) and jobs.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.database.base import Base


class SkillCategory(str, enum.Enum):
    """Categories for classifying extracted skills."""
    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    CLOUD = "cloud"
    LIBRARY = "library"
    TOOL = "tool"
    SOFT_SKILL = "soft_skill"
    OTHER = "other"


class Skill(Base):
    """Master skill table — each unique skill appears once."""
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    category = Column(SQLEnum(SkillCategory), nullable=True, default=SkillCategory.OTHER)

    # Relationships
    candidate_skills = relationship("CandidateSkill", back_populates="skill", cascade="all, delete-orphan")
    job_skills = relationship("JobSkill", back_populates="skill", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Skill(id={self.id}, name='{self.name}', category='{self.category}')>"


class CandidateSkill(Base):
    """Junction table linking a resume (candidate) to their extracted skills."""
    __tablename__ = "candidate_skills"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    proficiency_level = Column(String(50), nullable=True)  # e.g., "beginner", "intermediate", "expert"

    # Relationships
    resume = relationship("Resume", back_populates="candidate_skills")
    skill = relationship("Skill", back_populates="candidate_skills")

    def __repr__(self):
        return f"<CandidateSkill(resume_id={self.resume_id}, skill_id={self.skill_id})>"


class JobSkill(Base):
    """Junction table linking a job to its required/preferred skills."""
    __tablename__ = "job_skills"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    is_required = Column(Boolean, default=True)

    # Relationships
    job = relationship("Job", back_populates="job_skills")
    skill = relationship("Skill", back_populates="job_skills")

    def __repr__(self):
        return f"<JobSkill(job_id={self.job_id}, skill_id={self.skill_id}, required={self.is_required})>"
