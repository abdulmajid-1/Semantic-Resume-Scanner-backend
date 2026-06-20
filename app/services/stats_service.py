"""
Stats Service.
Provides analytical aggregations for Candidate, Recruiter, and Admin dashboards.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List

from app.models.user import User, UserRole
from app.models.job import Job
from app.models.resume import Resume
from app.models.application import Application
from app.models.ranking import Ranking


class StatsService:
    @staticmethod
    def get_recruiter_stats(db: Session, recruiter_id: int) -> Dict[str, Any]:
        """
        Gathers analytical statistics for the recruiter dashboard.
        """
        # 1. Total jobs posted by this recruiter
        total_jobs = db.query(Job).filter(Job.recruiter_id == recruiter_id).count()

        # Get all jobs posted by this recruiter
        recruiter_job_ids = [j.id for j in db.query(Job.id).filter(Job.recruiter_id == recruiter_id).all()]

        if not recruiter_job_ids:
            return {
                "total_jobs": 0,
                "total_candidates": 0,
                "average_score": 0.0,
                "top_candidate": None,
                "score_distribution": []
            }

        # 2. Total candidate applications to those jobs
        total_candidates = db.query(Application).filter(Application.job_id.in_(recruiter_job_ids)).count()

        # 3. Average Match Score
        avg_score = db.query(func.avg(Ranking.final_score)).join(Application).filter(
            Application.job_id.in_(recruiter_job_ids)
        ).scalar()
        avg_score = round(float(avg_score), 2) if avg_score else 0.0

        # 4. Top Candidate (Highest ranking score application)
        top_ranking = db.query(Ranking).join(Application).filter(
            Application.job_id.in_(recruiter_job_ids)
        ).order_by(Ranking.final_score.desc()).first()

        top_candidate_info = None
        if top_ranking:
            app = top_ranking.application
            top_candidate_info = {
                "name": app.resume.parsed_name or app.user.name,
                "job_title": app.job.title,
                "score": top_ranking.final_score,
                "email": app.resume.parsed_email or app.user.email
            }

        # 5. Score Distribution (Recharts compatible)
        score_ranges = {
            "0-50%": 0,
            "50-70%": 0,
            "70-85%": 0,
            "85-100%": 0
        }
        
        all_scores = db.query(Ranking.final_score).join(Application).filter(
            Application.job_id.in_(recruiter_job_ids)
        ).all()

        for score_tuple in all_scores:
            score = score_tuple[0]
            if score < 50:
                score_ranges["0-50%"] += 1
            elif score < 70:
                score_ranges["50-70%"] += 1
            elif score < 85:
                score_ranges["70-85%"] += 1
            else:
                score_ranges["85-100%"] += 1

        chart_data = [{"range": k, "count": v} for k, v in score_ranges.items()]

        return {
            "total_jobs": total_jobs,
            "total_candidates": total_candidates,
            "average_score": avg_score,
            "top_candidate": top_candidate_info,
            "score_distribution": chart_data
        }

    @staticmethod
    def get_candidate_stats(db: Session, candidate_id: int) -> Dict[str, Any]:
        """
        Gathers analytical statistics for a candidate's dashboard.
        """
        # Fetch candidate's latest resume
        resume = db.query(Resume).filter(Resume.user_id == candidate_id).order_by(Resume.created_at.desc()).first()

        resume_details = None
        if resume:
            resume_details = {
                "id": resume.id,
                "name": resume.parsed_name,
                "email": resume.parsed_email,
                "phone": resume.parsed_phone,
                "experience_years": resume.years_of_experience,
                "skills": [cs.skill.name for cs in resume.candidate_skills],
                "education": resume.education or [],
                "experience": resume.experience or [],
                "projects": resume.projects or [],
                "certifications": resume.certifications or []
            }

        # Get list of applied jobs
        applications = db.query(Application).filter(Application.user_id == candidate_id).all()
        applied_jobs = []

        for app in applications:
            ranking = app.ranking
            applied_jobs.append({
                "job_id": app.job_id,
                "job_title": app.job.title,
                "company": "Company",  # Placeholder or default
                "status": app.status.value,
                "applied_at": app.applied_at,
                "match_score": ranking.final_score if ranking else None,
                "rank": ranking.rank_position if ranking else None,
                "explanation": ranking.explanation if ranking else None
            })

        return {
            "resume": resume_details,
            "applied_jobs": applied_jobs,
            "total_applications": len(applied_jobs)
        }

    @staticmethod
    def get_admin_stats(db: Session) -> Dict[str, Any]:
        """
        Gathers statistics for the system administrator.
        """
        total_users = db.query(User).count()
        total_jobs = db.query(Job).count()
        total_resumes = db.query(Resume).count()
        total_applications = db.query(Application).count()

        role_breakdown = {
            "candidates": db.query(User).filter(User.role == UserRole.CANDIDATE).count(),
            "recruiters": db.query(User).filter(User.role == UserRole.RECRUITER).count(),
            "admins": db.query(User).filter(User.role == UserRole.ADMIN).count()
        }

        # Get average matching scores across the entire system
        avg_score = db.query(func.avg(Ranking.final_score)).scalar()
        avg_score = round(float(avg_score), 2) if avg_score else 0.0

        return {
            "total_users": total_users,
            "total_jobs": total_jobs,
            "total_resumes": total_resumes,
            "total_applications": total_applications,
            "role_breakdown": role_breakdown,
            "system_average_score": avg_score
        }
