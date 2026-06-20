"""
Matching Service.
Computes similarity scores for Semantic alignment (Cosine), Technical Skills matching,
and Years of Experience matching.
"""

import numpy as np
from typing import List, Set, Dict, Any


class MatchingService:
    @staticmethod
    def scale_similarity(sim: float) -> float:
        """
        Scales raw cosine similarity from SentenceTransformer (concentrated in [0.15, 0.60])
        to a more human-expected range [0.0, 1.0].
        """
        if sim <= 0.15:
            return 0.0
        elif sim <= 0.35:
            # Map [0.15, 0.35] -> [0.0, 0.60]
            return (sim - 0.15) / (0.35 - 0.15) * 0.60
        elif sim <= 0.55:
            # Map [0.35, 0.55] -> [0.60, 0.95]
            return 0.60 + (sim - 0.35) / (0.55 - 0.35) * (0.95 - 0.60)
        else:
            # Map [0.55, 1.0] -> [0.95, 1.0]
            return 0.95 + (sim - 0.55) / (1.0 - 0.55) * 0.05

    @classmethod
    def compute_semantic_similarity(cls, resume_vector: np.ndarray, job_vector: np.ndarray) -> float:
        """
        Computes cosine similarity between candidate resume embedding and job description embedding,
        and scales it to a human-expected range [0.0, 1.0].
        """
        if resume_vector is None or job_vector is None:
            return 0.0
            
        dot_product = np.dot(resume_vector, job_vector)
        norm_resume = np.linalg.norm(resume_vector)
        norm_job = np.linalg.norm(job_vector)
        
        if norm_resume == 0 or norm_job == 0:
            return 0.0
            
        similarity = float(dot_product / (norm_resume * norm_job))
        # Clip to [0, 1] range to avoid floating point anomalies outside range
        similarity = max(0.0, min(1.0, similarity))
        
        # Scale to human-friendly percentage
        return cls.scale_similarity(similarity)

    @staticmethod
    def compute_skill_match(candidate_skills: List[str], required_skills: List[str]) -> Dict[str, Any]:
        """
        Computes the skill match ratio.
        Compares candidate extracted skills against job required skills (case-insensitive).
        Returns a dictionary with:
        - match_score: float (0.0 to 1.0)
        - matched_skills: List[str]
        - missing_skills: List[str]
        """
        if not required_skills:
            # If no skills are required, candidate automatically gets 100% skill match
            return {
                "match_score": 1.0,
                "matched_skills": [],
                "missing_skills": []
            }

        candidate_set = {s.lower() for s in candidate_skills}
        required_set = {s.lower() for s in required_skills}
        
        matched_set = candidate_set.intersection(required_set)
        missing_set = required_set.difference(candidate_set)

        # Retrieve original casing for display
        matched_display = []
        for req in required_skills:
            if req.lower() in matched_set:
                matched_display.append(req)
                
        missing_display = []
        for req in required_skills:
            if req.lower() in missing_set:
                missing_display.append(req)

        match_score = len(matched_set) / len(required_set)

        return {
            "match_score": match_score,
            "matched_skills": matched_display,
            "missing_skills": missing_display
        }

    @staticmethod
    def compute_experience_match(candidate_years: int, required_years: int) -> float:
        """
        Computes experience match score.
        If candidate experience is equal to or greater than required, returns 1.0.
        Otherwise, returns candidate_years / required_years.
        """
        if required_years <= 0:
            # If no experience is required, candidate gets full experience match
            return 1.0
            
        ratio = candidate_years / required_years
        return max(0.0, min(1.0, ratio))
