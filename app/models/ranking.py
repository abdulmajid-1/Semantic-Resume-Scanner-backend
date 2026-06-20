"""
Ranking model — stores the computed ranking scores for each application.
Includes individual score components, matched/missing skills, and AI explanations.
"""

from sqlalchemy import Column, Integer, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database.base import Base


class Ranking(Base):
    __tablename__ = "rankings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"),
                            nullable=False, unique=True, index=True)

    # Individual score components (0-100 scale)
    semantic_score = Column(Float, nullable=False, default=0.0)
    skill_score = Column(Float, nullable=False, default=0.0)
    experience_score = Column(Float, nullable=False, default=0.0)

    # Weighted final score (0-100 scale)
    final_score = Column(Float, nullable=False, default=0.0)

    # Rank position among all candidates for this job
    rank_position = Column(Integer, nullable=True)

    # Skill gap analysis
    matched_skills = Column(JSON, nullable=True)   # List of matched skill names
    missing_skills = Column(JSON, nullable=True)   # List of missing skill names

    # Explainable AI output
    explanation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    application = relationship("Application", back_populates="ranking")

    def __repr__(self):
        return f"<Ranking(id={self.id}, application_id={self.application_id}, final_score={self.final_score})>"
