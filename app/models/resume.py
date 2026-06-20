"""
Resume model — stores uploaded resume files and parsed content.
Linked to a user (candidate) via foreign key.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database.base import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False)  # "pdf" or "docx"
    raw_text = Column(Text, nullable=True)

    # Parsed fields
    parsed_name = Column(String(255), nullable=True)
    parsed_email = Column(String(255), nullable=True)
    parsed_phone = Column(String(50), nullable=True)
    education = Column(JSON, nullable=True)       # List of education entries
    experience = Column(JSON, nullable=True)      # List of experience entries
    projects = Column(JSON, nullable=True)        # List of projects
    certifications = Column(JSON, nullable=True)  # List of certifications
    years_of_experience = Column(Integer, nullable=True, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="resumes")
    candidate_skills = relationship("CandidateSkill", back_populates="resume", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="resume", cascade="all, delete-orphan")
    embedding = relationship("Embedding", back_populates="resume", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Resume(id={self.id}, user_id={self.user_id}, file_type='{self.file_type}')>"
