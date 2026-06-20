"""
Ranking Service.
Computes final candidate rankings for jobs using a weighted formula.
Saves ranking records to PostgreSQL.
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import numpy as np
import logging

from app.models.job import Job
from app.models.resume import Resume
from app.models.application import Application, ApplicationStatus
from app.models.ranking import Ranking
from app.models.embedding import Embedding, EmbeddingSourceType
from app.ranking.matching_service import MatchingService
from app.ranking.explainer_service import ExplainerService
from app.embeddings.embedding_service import EmbeddingService
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RankingService:
    def __init__(self, db: Session):
        self.db = db
        self.matching_service = MatchingService()
        self.explainer_service = ExplainerService()
        self.embedding_service = EmbeddingService()

    def process_and_rank_candidates(
        self, 
        job_id: int, 
        semantic_w: float = None, 
        skill_w: float = None, 
        exp_w: float = None
    ) -> List[Ranking]:
        """
        Retrieves all applications for a specific job, calculates their scores,
        saves them to the ranking table, updates rank positions, and returns sorted rankings.
        """
        # 1. Resolve weights (fallback to defaults from settings)
        sem_w = semantic_w if semantic_w is not None else settings.SEMANTIC_WEIGHT
        skl_w = skill_w if skill_w is not None else settings.SKILL_WEIGHT
        exp_w = exp_w if exp_w is not None else settings.EXPERIENCE_WEIGHT
        
        # Ensure weights add up to 1.0 (normalize if not)
        total_w = sem_w + skl_w + exp_w
        if total_w != 1.0 and total_w > 0:
            sem_w /= total_w
            skl_w /= total_w
            exp_w /= total_w

        # 2. Get Job Details and Job Embedding
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError("Job not found.")

        job_emb_record = self.db.query(Embedding).filter(
            Embedding.source_type == EmbeddingSourceType.JOB,
            Embedding.job_id == job_id
        ).first()
        
        if not job_emb_record:
            # Generate job embedding if missing
            combined_text = f"{job.title}\n{job.description}"
            job_vector = self.embedding_service.get_or_create_job_embedding(self.db, job_id, combined_text)
        else:
            job_vector = np.frombuffer(job_emb_record.embedding_vector, dtype=np.float32)

        # 3. Get all applications for this job
        applications = self.db.query(Application).filter(Application.job_id == job_id).all()
        if not applications:
            return []

        computed_rankings = []

        # 4. Compute scores for each application
        for app in applications:
            resume = app.resume
            
            # Retrieve resume embedding
            res_emb_record = self.db.query(Embedding).filter(
                Embedding.source_type == EmbeddingSourceType.RESUME,
                Embedding.resume_id == resume.id
            ).first()
            
            if not res_emb_record:
                resume_vector = self.embedding_service.get_or_create_resume_embedding(self.db, resume.id, resume.raw_text)
            else:
                resume_vector = np.frombuffer(res_emb_record.embedding_vector, dtype=np.float32)

            # Compute semantic score
            semantic_score = self.matching_service.compute_semantic_similarity(resume_vector, job_vector) * 100

            # Compute skills score
            candidate_skill_names = [cs.skill.name for cs in resume.candidate_skills]
            skill_match_data = self.matching_service.compute_skill_match(
                candidate_skills=candidate_skill_names,
                required_skills=job.required_skills or []
            )
            skill_score = skill_match_data["match_score"] * 100

            # Compute experience score
            experience_score = self.matching_service.compute_experience_match(
                candidate_years=resume.years_of_experience or 0,
                required_years=job.experience_required or 0
            ) * 100

            # Weighted final score
            final_score = (
                (semantic_score * sem_w) + 
                (skill_score * skl_w) + 
                (experience_score * exp_w)
            )

            # Generate natural language AI explanation
            explanation = self.explainer_service.generate_explanation(
                candidate_name=resume.parsed_name,
                semantic_score=semantic_score,
                skill_score=skill_score,
                experience_score=experience_score,
                matched_skills=skill_match_data["matched_skills"],
                missing_skills=skill_match_data["missing_skills"],
                candidate_years=resume.years_of_experience or 0,
                required_years=job.experience_required or 0
            )

            # Check if ranking already exists for this application
            ranking_record = self.db.query(Ranking).filter(Ranking.application_id == app.id).first()
            if not ranking_record:
                ranking_record = Ranking(
                    application_id=app.id,
                    semantic_score=round(semantic_score, 2),
                    skill_score=round(skill_score, 2),
                    experience_score=round(experience_score, 2),
                    final_score=round(final_score, 2),
                    matched_skills=skill_match_data["matched_skills"],
                    missing_skills=skill_match_data["missing_skills"],
                    explanation=explanation
                )
                self.db.add(ranking_record)
            else:
                ranking_record.semantic_score = round(semantic_score, 2)
                ranking_record.skill_score = round(skill_score, 2)
                ranking_record.experience_score = round(experience_score, 2)
                ranking_record.final_score = round(final_score, 2)
                ranking_record.matched_skills = skill_match_data["matched_skills"]
                ranking_record.missing_skills = skill_match_data["missing_skills"]
                ranking_record.explanation = explanation

            computed_rankings.append(ranking_record)

        self.db.commit()

        # 5. Sort by final score descending and assign rank positions
        computed_rankings.sort(key=lambda r: r.final_score, reverse=True)
        for index, rank in enumerate(computed_rankings):
            rank.rank_position = index + 1
            
        self.db.commit()

        return computed_rankings
