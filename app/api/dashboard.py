"""
Dashboard API Router.
Exposes statistics and aggregation endpoints for recruiters and candidates.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.auth.dependencies import get_current_user, require_role
from app.services.stats_service import StatsService

router = APIRouter(tags=["Dashboards"])


@router.get("/dashboard/recruiter")
def get_recruiter_dashboard(
    current_user: User = Depends(require_role(UserRole.RECRUITER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Get Recruiter analytics: jobs posted, total candidates, top candidate, and score distributions.
    """
    return StatsService.get_recruiter_stats(db, recruiter_id=current_user.id)


@router.get("/dashboard/candidate")
def get_candidate_dashboard(
    current_user: User = Depends(require_role(UserRole.CANDIDATE, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Get Candidate dashboard info: parsed resume, applied jobs details, and match scores.
    """
    return StatsService.get_candidate_stats(db, candidate_id=current_user.id)
