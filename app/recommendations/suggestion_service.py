"""
Recommendation / Suggestion Service.
Generates resume improvement suggestions for candidates based on missing skills,
experience gap, and project relevancy.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.resume import Resume
from app.models.job import Job
from app.models.application import Application
from app.models.ranking import Ranking


class SuggestionService:
    @staticmethod
    def get_resume_suggestions(db: Session, candidate_id: int) -> List[Dict[str, Any]]:
        """
        Generates improvement recommendations for a candidate based on all jobs they have applied to.
        Checks for gaps in skills and experience and provides specific action items.
        """
        # Get candidate's latest resume
        resume = db.query(Resume).filter(Resume.user_id == candidate_id).order_by(Resume.created_at.desc()).first()
        if not resume:
            return [{
                "title": "Upload your resume",
                "description": "Please upload a resume (PDF or DOCX) to get started with AI resume feedback.",
                "type": "general"
            }]

        suggestions = []
        candidate_skills = {cs.skill.name.lower() for cs in resume.candidate_skills}

        # 1. Fetch applications
        applications = db.query(Application).filter(Application.user_id == candidate_id).all()
        
        missing_skills_across_jobs = set()
        experience_shortfalls = []

        for app in applications:
            job = app.job
            ranking = app.ranking
            
            # Check experience gap
            if job.experience_required and (resume.years_of_experience or 0) < job.experience_required:
                experience_shortfalls.append(job)

            # Check missing skills from rankings or calculate manually
            if ranking and ranking.missing_skills:
                for skill in ranking.missing_skills:
                    missing_skills_across_jobs.add(skill)
            elif job.required_skills:
                for skill in job.required_skills:
                    if skill.lower() not in candidate_skills:
                        missing_skills_across_jobs.add(skill)

        # 2. Skill Improvement suggestions
        if missing_skills_across_jobs:
            skills_list = list(missing_skills_across_jobs)[:5]
            suggestions.append({
                "title": "Acquire In-Demand Technical Skills",
                "description": f"Based on your target jobs, consider learning: {', '.join(skills_list)}. Adding these to your profile will boost your semantic matches.",
                "type": "skill"
            })
            
            # Add certifications suggestions
            suggestions.append({
                "title": "Add Relevant Certifications",
                "description": f"Look into professional certifications related to: {', '.join(skills_list[:3])}. Certifications validate your expertise for recruiters.",
                "type": "certification"
            })

        # 3. Experience level suggestions
        if experience_shortfalls:
            target_roles = ", ".join({job.title for job in experience_shortfalls[:2]})
            suggestions.append({
                "title": "Highlight Relevant Achievements",
                "description": f"Since your experience is slightly below the target for roles like '{target_roles}', emphasize projects, volunteer work, or freelance experience to demonstrate comparable depth.",
                "type": "experience"
            })

        # 4. Project improvement suggestions
        if not resume.projects:
            suggestions.append({
                "title": "Add Projects Section",
                "description": "Your resume currently does not highlight specific projects. Adding a 'Projects' section showing how you applied tools like Python, React, etc., will greatly enhance your credibility.",
                "type": "project"
            })
        else:
            suggestions.append({
                "title": "Structure Projects with STAR Method",
                "description": "Ensure your project descriptions follow the STAR method (Situation, Task, Action, Result). Quantify your results where possible (e.g., 'improved performance by 20%').",
                "type": "project"
            })

        # 5. Fallback general suggestion
        if not suggestions:
            suggestions.append({
                "title": "Profile looking strong!",
                "description": "Your current resume matches all requirements for your applied roles. To stand out further, consider adding specific numbers and metrics of your achievements.",
                "type": "general"
            })

        return suggestions
