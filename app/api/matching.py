"""
Matching and Rankings API Router.
Handles job application submissions, rank calculation triggers, and retrieval of rankings/recommendations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.job import Job
from app.models.resume import Resume
from app.models.application import Application, ApplicationStatus
from app.models.ranking import Ranking
from app.auth.dependencies import get_current_user, require_role
from app.ranking.ranking_service import RankingService
from app.recommendations.suggestion_service import SuggestionService
from app.schemas.ranking import MatchRequest, RankingResponse, CandidateRank, Recommendation

router = APIRouter(tags=["Matching & Ranking"])


@router.post("/jobs/{job_id}/apply", status_code=status.HTTP_201_CREATED)
def apply_to_job(
    job_id: int,
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
    db: Session = Depends(get_db)
):
    """
    Apply to a job. The candidate must have uploaded a resume first.
    """
    # 1. Fetch job
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    # 2. Get candidate's latest resume
    resume = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must upload a resume before applying to jobs."
        )

    # 3. Check for existing application
    existing = db.query(Application).filter(
        Application.job_id == job_id,
        Application.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied to this job."
        )

    # 4. Create application
    app = Application(
        user_id=current_user.id,
        job_id=job_id,
        resume_id=resume.id,
        status=ApplicationStatus.PENDING
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    # 5. Automatically trigger ranking generation/refresh for this job
    # This keeps rankings in sync
    try:
        rank_service = RankingService(db)
        rank_service.process_and_rank_candidates(job_id)
    except Exception as e:
        # Don't fail the application if ranking generation has a background issue
        import logging
        logging.getLogger(__name__).error(f"Failed to auto-generate rankings: {e}")

    return {"message": "Application submitted successfully.", "application_id": app.id}


@router.post("/match", response_model=Dict[str, Any])
def trigger_match(
    request: MatchRequest,
    current_user: User = Depends(require_role(UserRole.RECRUITER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Manually triggers calculations and refreshes candidate rankings for a specific job.
    """
    rank_service = RankingService(db)
    try:
        rankings = rank_service.process_and_rank_candidates(request.job_id)
        return {
            "message": f"Successfully calculated/refreshed rankings for {len(rankings)} candidates.",
            "candidates_ranked": len(rankings)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/rankings/{job_id}", response_model=RankingResponse)
def get_rankings(
    job_id: int,
    current_user: User = Depends(require_role(UserRole.RECRUITER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Retrieve rankings for all candidates who applied to a specific job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    # Refresh rankings to ensure they are up to date
    rank_service = RankingService(db)
    db_rankings = rank_service.process_and_rank_candidates(job_id)

    rank_list = []
    for rank in db_rankings:
        app = rank.application
        rank_list.append(CandidateRank(
            application_id=app.id,
            candidate_id=app.user_id,
            candidate_name=app.resume.parsed_name or app.user.name,
            resume_id=app.resume_id,
            semantic_score=rank.semantic_score,
            skill_score=rank.skill_score,
            experience_score=rank.experience_score,
            final_score=rank.final_score,
            rank_position=rank.rank_position,
            matched_skills=rank.matched_skills or [],
            missing_skills=rank.missing_skills or [],
            explanation=rank.explanation,
            applied_at=app.applied_at
        ))

    return RankingResponse(
        job_id=job.id,
        job_title=job.title,
        rankings=rank_list
    )


@router.get("/recommendations/{candidate_id}", response_model=List[Recommendation])
def get_recommendations(
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve resume suggestions for a specific candidate.
    Candidates can only view their own; recruiters/admins can view any.
    """
    if current_user.role == UserRole.CANDIDATE and current_user.id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view suggestions for other candidates."
        )

    suggestions = SuggestionService.get_resume_suggestions(db, candidate_id)
    return [Recommendation(**s) for s in suggestions]
