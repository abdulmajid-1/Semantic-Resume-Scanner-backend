"""
FAISS Search Service.
Builds and maintains an in-memory & on-disk FAISS index of all candidate resume embeddings.
Allows recruiters to run natural language semantic queries to find matching candidates.
"""

import faiss
import numpy as np
import os
import pickle
from typing import List, Dict, Tuple, Any
from sqlalchemy.orm import Session
import logging

from app.models.resume import Resume
from app.models.embedding import Embedding, EmbeddingSourceType
from app.embeddings.embedding_service import EmbeddingService
from app.ranking.matching_service import MatchingService
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FAISSSearchService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern for FAISS Index management."""
        if not cls._instance:
            cls._instance = super(FAISSSearchService, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.index_dir = settings.FAISS_INDEX_PATH
        self.index_file = os.path.join(self.index_dir, "candidates.index")
        self.mapping_file = os.path.join(self.index_dir, "mapping.pkl")
        self.dimension = 384  # Dimension of all-MiniLM-L6-v2 embeddings
        
        # Initialize index & ID mapping
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner Product (Cosine similarity if normalized)
        self.index_to_resume_id: List[int] = []

        os.makedirs(self.index_dir, exist_ok=True)
        self.load_index_from_disk()
        
        self.embedding_service = EmbeddingService()
        self._initialized = True

    def load_index_from_disk(self):
        """Loads FAISS index and ID mapping from disk if they exist."""
        if os.path.exists(self.index_file) and os.path.exists(self.mapping_file):
            try:
                self.index = faiss.read_index(self.index_file)
                with open(self.mapping_file, "rb") as f:
                    self.index_to_resume_id = pickle.load(f)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} candidate records from disk.")
            except Exception as e:
                logger.error(f"Failed to load FAISS index from disk: {e}. Reinitializing empty index.")
                self.index = faiss.IndexFlatIP(self.dimension)
                self.index_to_resume_id = []

    def save_index_to_disk(self):
        """Saves the current FAISS index and mapping to disk."""
        try:
            faiss.write_index(self.index, self.index_file)
            with open(self.mapping_file, "wb") as f:
                pickle.dump(self.index_to_resume_id, f)
            logger.info("Saved FAISS index and mappings to disk.")
        except Exception as e:
            logger.error(f"Failed to save FAISS index to disk: {e}")

    def rebuild_index(self, db: Session):
        """
        Queries all resume embeddings from database, normalizes them, and rebuilds the FAISS index.
        """
        logger.info("Rebuilding FAISS index from database embeddings...")
        
        # Fetch all resume embeddings
        records = db.query(Embedding).filter(Embedding.source_type == EmbeddingSourceType.RESUME).all()
        
        if not records:
            # Reinitialize empty
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index_to_resume_id = []
            self.save_index_to_disk()
            return

        vectors = []
        mapping = []

        for rec in records:
            vector = np.frombuffer(rec.embedding_vector, dtype=np.float32)
            if vector.shape[0] == self.dimension:
                # Normalize vector to unit length (so inner product search performs Cosine similarity)
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = vector / norm
                vectors.append(vector)
                mapping.append(rec.source_id) # source_id is resume_id

        if vectors:
            vectors_np = np.vstack(vectors).astype(np.float32)
            # Create a new index
            new_index = faiss.IndexFlatIP(self.dimension)
            new_index.add(vectors_np)
            
            self.index = new_index
            self.index_to_resume_id = mapping
            self.save_index_to_disk()
            logger.info(f"FAISS index successfully rebuilt with {new_index.ntotal} records.")

    def add_resume_to_index(self, resume_id: int, raw_text: str):
        """
        Dynamically appends a new resume embedding to the FAISS index.
        """
        try:
            # Generate new embedding
            vector = self.embedding_service.generate_embedding(raw_text)
            
            # Normalize for cosine similarity
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
                
            vector_np = np.array([vector]).astype(np.float32)
            
            # Add to FAISS index
            self.index.add(vector_np)
            self.index_to_resume_id.append(resume_id)
            
            self.save_index_to_disk()
            logger.info(f"Dynamically added Resume ID: {resume_id} to FAISS index.")
        except Exception as e:
            logger.error(f"Failed to add resume {resume_id} to FAISS index: {e}")

    def search_candidates(self, db: Session, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Computes query embedding, searches FAISS index, and returns matching candidates.
        """
        if self.index.ntotal == 0:
            # If index is empty, try to rebuild it
            self.rebuild_index(db)
            if self.index.ntotal == 0:
                return []

        # 1. Embed and normalize search query
        query_vector = self.embedding_service.generate_embedding(query)
        q_norm = np.linalg.norm(query_vector)
        if q_norm > 0:
            query_vector = query_vector / q_norm
            
        query_vector_np = np.array([query_vector]).astype(np.float32)

        # 2. Search index
        # D: Distances (Inner products), I: Indices of matches
        top_k = min(top_k, self.index.ntotal)
        D, I = self.index.search(query_vector_np, top_k)

        results = []
        
        for score, idx in zip(D[0], I[0]):
            if idx == -1:
                continue
                
            resume_id = self.index_to_resume_id[idx]
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if resume:
                results.append({
                    "resume_id": resume.id,
                    "candidate_id": resume.user_id,
                    "candidate_name": resume.parsed_name or resume.user.name,
                    "file_type": resume.file_type,
                    "skills": [cs.skill.name for cs in resume.candidate_skills][:10],
                    "years_of_experience": resume.years_of_experience or 0,
                    "similarity_score": round(MatchingService.scale_similarity(float(score)) * 100, 2)
                })

        # Sort results by similarity score descending
        results.sort(key=lambda r: r["similarity_score"], reverse=True)
        return results
