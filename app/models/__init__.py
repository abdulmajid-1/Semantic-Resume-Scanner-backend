"""
Models package — imports all ORM models so Alembic and SQLAlchemy
can discover them automatically.
"""

from app.models.user import User, UserRole
from app.models.resume import Resume
from app.models.job import Job
from app.models.skill import Skill, CandidateSkill, JobSkill, SkillCategory
from app.models.application import Application, ApplicationStatus
from app.models.embedding import Embedding, EmbeddingSourceType
from app.models.ranking import Ranking
from app.models.password_reset import PasswordReset

__all__ = [
    "User", "UserRole",
    "Resume",
    "Job",
    "Skill", "CandidateSkill", "JobSkill", "SkillCategory",
    "Application", "ApplicationStatus",
    "Embedding", "EmbeddingSourceType",
    "Ranking",
    "PasswordReset",
]

