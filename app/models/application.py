"""
Application model — tracks candidate applications to jobs.
Links a user + resume to a specific job posting.
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.database.base import Base


class ApplicationStatus(str, enum.Enum):
    """Status of a candidate's application."""
    PENDING = "pending"
    REVIEWED = "reviewed"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.PENDING, nullable=False)
    applied_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")
    ranking = relationship("Ranking", back_populates="application", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Application(id={self.id}, user_id={self.user_id}, job_id={self.job_id}, status='{self.status}')>"
