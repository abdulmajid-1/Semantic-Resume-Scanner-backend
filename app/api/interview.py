"""
Interview Operations API Router.
Handles generating AI interview invitation emails and dispatching them via SMTP.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.resume import Resume
from app.models.application import Application, ApplicationStatus
from app.auth.dependencies import require_role
from app.schemas.interview import GenerateEmailRequest, GenerateEmailResponse, SendEmailRequest
from app.services.email_service import InterviewEmailService

router = APIRouter(tags=["Interview Operations"])
logger = logging.getLogger(__name__)


@router.post("/interview/generate-email", response_model=GenerateEmailResponse)
def generate_email(
    request: GenerateEmailRequest,
    current_user: User = Depends(require_role(UserRole.RECRUITER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Generate an AI templated interview email invitation for a candidate.
    """
    try:
        email_data = InterviewEmailService.generate_interview_email(
            db=db,
            resume_id=request.resume_id,
            recruiter_user=current_user,
            date_time=request.date_time,
            job_id=request.job_id,
            job_title=request.job_title
        )
        return GenerateEmailResponse(**email_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate email: {str(e)}")


@router.post("/interview/send-email")
def send_email(
    request: SendEmailRequest,
    current_user: User = Depends(require_role(UserRole.RECRUITER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Send the interview email to the candidate via Gmail SMTP,
    and transition candidate application to SHORTLISTED status if applicable.
    """
    # 1. Actually send the email via SMTP
    try:
        InterviewEmailService.send_email_smtp(
            to_email=request.candidate_email,
            subject=request.subject,
            body=request.body
        )
    except ValueError as e:
        # Config or auth error — return a clear message
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Email dispatch failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )

    # 2. If the candidate has an application for this job, update its status to SHORTLISTED
    if request.job_id:
        application = db.query(Application).filter(
            Application.resume_id == request.resume_id,
            Application.job_id == request.job_id
        ).first()
        if application:
            application.status = ApplicationStatus.SHORTLISTED
            db.commit()
            db.refresh(application)
            logger.info(f"Updated application ID {application.id} status to SHORTLISTED")

    return {"message": f"Interview invitation email sent successfully to {request.candidate_email}."}
