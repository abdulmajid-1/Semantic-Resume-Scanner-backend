"""
Explainer Service for generating human-readable explanation strings for why candidates were ranked/matched.
Part of the Explainable AI (XAI) module.
"""

from typing import List


class ExplainerService:
    @staticmethod
    def generate_explanation(
        candidate_name: str,
        semantic_score: float,
        skill_score: float,
        experience_score: float,
        matched_skills: List[str],
        missing_skills: List[str],
        candidate_years: int,
        required_years: int
    ) -> str:
        """
        Generates a natural-sounding paragraph summary explaining the ranking score.
        """
        name = candidate_name or "The candidate"
        
        # 1. Evaluate Semantic similarity
        if semantic_score >= 80:
            semantic_desc = "has a strong semantic alignment with the overall job description, suggesting their background is very relevant."
        elif semantic_score >= 60:
            semantic_desc = "shows moderate semantic alignment, indicating a reasonable fit with the job requirements."
        else:
            semantic_desc = "exhibits lower semantic alignment, meaning their general profile does not closely match this role's description."

        # 2. Evaluate Experience match
        if required_years <= 0:
            exp_desc = "This role does not require prior years of experience."
        elif candidate_years >= required_years:
            exp_desc = f"They meet the experience requirement, possessing {candidate_years} years (required: {required_years} years)."
        else:
            exp_desc = f"They fall short on experience, possessing {candidate_years} years relative to the required {required_years} years."

        # 3. Evaluate Technical Skills match
        if not matched_skills and not missing_skills:
            skills_desc = "No required skill keywords were specified for matching."
        elif len(missing_skills) == 0:
            skills_desc = "They possess all required tech skills for this job description."
        else:
            skills_count = len(matched_skills)
            total_skills = len(matched_skills) + len(missing_skills)
            skills_desc = f"They cover {skills_count} out of {total_skills} required skills ({skill_score:.0f}% matching)."

        # Compile detailed explanation
        parts = [
            f"{name} {semantic_desc}",
            exp_desc,
            skills_desc
        ]

        if matched_skills:
            parts.append(f"Matched skills include: {', '.join(matched_skills[:6])}.")
            
        if missing_skills:
            parts.append(f"Key missing skills to consider: {', '.join(missing_skills[:6])}.")

        return " ".join(parts)
