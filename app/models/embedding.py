"""
Embedding model — stores vector embeddings for resumes and job descriptions.
Embeddings are serialized numpy arrays stored as binary (LargeBinary).
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.database.base import Base


class EmbeddingSourceType(str, enum.Enum):
    """Type of content the embedding represents."""
    RESUME = "resume"
    JOB = "job"


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_type = Column(SQLEnum(EmbeddingSourceType), nullable=False)
    source_id = Column(Integer, nullable=False, index=True)  # ID of the resume or job
    embedding_vector = Column(LargeBinary, nullable=False)    # Serialized numpy array
    model_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships — polymorphic via source_type + source_id
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True)

    resume = relationship("Resume", back_populates="embedding", foreign_keys=[resume_id])
    job = relationship("Job", back_populates="embedding", foreign_keys=[job_id])

    def __repr__(self):
        return f"<Embedding(id={self.id}, source_type='{self.source_type}', source_id={self.source_id})>"
