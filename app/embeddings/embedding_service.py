"""
Embedding Service.
Loads the SentenceTransformer model and computes vector embeddings for resumes and job descriptions.
Stores and retrieves embeddings in PostgreSQL to avoid unnecessary regeneration.
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from sqlalchemy.orm import Session
import logging

from app.models.embedding import Embedding, EmbeddingSourceType
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Implement Singleton pattern so the model is only loaded once."""
        if not cls._instance:
            cls._instance = super(EmbeddingService, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.model_name = settings.MODEL_NAME
        logger.info(f"Loading SentenceTransformer model: {self.model_name}...")
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info("SentenceTransformer model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model {self.model_name}: {e}")
            raise e
        self._initialized = True

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generates a 384-dimensional vector embedding for the given text.
        """
        if not text:
            # Return a zero vector if text is empty
            return np.zeros(384, dtype=np.float32)
        
        # SentenceTransformer outputs a numpy array
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)

    def get_or_create_resume_embedding(self, db: Session, resume_id: int, text: str) -> np.ndarray:
        """
        Retrieves cached resume embedding or creates and caches a new one.
        """
        # Check database first
        db_emb = db.query(Embedding).filter(
            Embedding.source_type == EmbeddingSourceType.RESUME,
            Embedding.resume_id == resume_id
        ).first()

        if db_emb:
            # Deserialize binary back to numpy array
            return np.frombuffer(db_emb.embedding_vector, dtype=np.float32)

        # Generate new embedding
        logger.info(f"Generating new embedding for Resume ID: {resume_id}")
        vector = self.generate_embedding(text)
        
        # Save to database
        db_emb = Embedding(
            source_type=EmbeddingSourceType.RESUME,
            source_id=resume_id,
            resume_id=resume_id,
            embedding_vector=vector.tobytes(),
            model_name=self.model_name
        )
        db.add(db_emb)
        db.commit()
        
        return vector

    def get_or_create_job_embedding(self, db: Session, job_id: int, text: str) -> np.ndarray:
        """
        Retrieves cached job description embedding or creates and caches a new one.
        """
        # Check database first
        db_emb = db.query(Embedding).filter(
            Embedding.source_type == EmbeddingSourceType.JOB,
            Embedding.job_id == job_id
        ).first()

        if db_emb:
            # Deserialize binary back to numpy array
            return np.frombuffer(db_emb.embedding_vector, dtype=np.float32)

        # Generate new embedding
        logger.info(f"Generating new embedding for Job ID: {job_id}")
        vector = self.generate_embedding(text)
        
        # Save to database
        db_emb = Embedding(
            source_type=EmbeddingSourceType.JOB,
            source_id=job_id,
            job_id=job_id,
            embedding_vector=vector.tobytes(),
            model_name=self.model_name
        )
        db.add(db_emb)
        db.commit()
        
        return vector
