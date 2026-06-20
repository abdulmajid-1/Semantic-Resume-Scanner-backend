"""
Jobs API Router.
Handles CRUD operations for Job Descriptions.
Restricts modifications to Recruiters and Admins.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.job import Job
from app.models.skill import Skill, JobSkill, SkillCategory
from app.auth.dependencies import get_current_user, require_role
from app.schemas.job import JobCreate, JobUpdate, JobResponse
from app.embeddings.embedding_service import EmbeddingService

router = APIRouter(tags=["Jobs"])


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_data: JobCreate,
    current_user: User = Depends(require_role(UserRole.RECRUITER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Create a new job posting. Generates embedding and saves required/preferred skills.
    Only accessible by Recruiters and Admins.
    """
    # 1. Create Job object
    db_job = Job(
        recruiter_id=current_user.id,
        title=job_data.title,
        description=job_data.description,
        required_skills=job_data.required_skills,
        preferred_skills=job_data.preferred_skills,
        experience_required=job_data.experience_required,
        location=job_data.location,
        is_active=True
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    # 2. Add Job Skills relations
    # Combine required and preferred skills to map them in junction table
    all_skills = [(s, True) for s in job_data.required_skills] + [(s, False) for s in job_data.preferred_skills]
    
    for skill_name, is_req in all_skills:
        # Check master skill table
        master_skill = db.query(Skill).filter(Skill.name.ilike(skill_name)).first()
        if not master_skill:
            # Create a master skill record (default to other category)
            master_skill = Skill(name=skill_name, category=SkillCategory.OTHER)
            db.add(master_skill)
            db.commit()
            db.refresh(master_skill)
            
        # Add JobSkill junction entry
        job_skill_entry = JobSkill(
            job_id=db_job.id,
            skill_id=master_skill.id,
            is_required=is_req
        )
        db.add(job_skill_entry)

    db.commit()

    # 3. Generate and cache Job description embedding
    # We combine title + description for richer semantic context
    combined_text = f"{db_job.title}\n{db_job.description}"
    embedding_service = EmbeddingService()
    embedding_service.get_or_create_job_embedding(db, db_job.id, combined_text)

    return db_job


@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    """
    List all active jobs. Available to all roles.
    """
    return db.query(Job).filter(Job.is_active == True).all()


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """
    Get job details by ID.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found."
        )
    return job


@router.put("/jobs/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    job_data: JobUpdate,
    current_user: User = Depends(require_role(UserRole.RECRUITER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Update a job description.
    Only allows owner recruiter or admins to update.
    """
    db_job = db.query(Job).filter(Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found.")

    # Authorization Check
    if current_user.role == UserRole.RECRUITER and db_job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this job."
        )

    # Update simple fields
    update_dict = job_data.model_dump(exclude_unset=True)
    
    # Check if we need to regenerate embedding
    text_changed = False
    if "title" in update_dict or "description" in update_dict:
        text_changed = True

    for key, value in update_dict.items():
        if key not in ["required_skills", "preferred_skills"]:
            setattr(db_job, key, value)

    # Handle skill list updates if provided
    if job_data.required_skills is not None or job_data.preferred_skills is not None:
        # Clear existing job skills
        db.query(JobSkill).filter(JobSkill.job_id == job_id).delete()
        
        req = job_data.required_skills if job_data.required_skills is not None else db_job.required_skills
        pref = job_data.preferred_skills if job_data.preferred_skills is not None else db_job.preferred_skills
        
        db_job.required_skills = req
        db_job.preferred_skills = pref

        # Repopulate
        all_skills = [(s, True) for s in req] + [(s, False) for s in pref]
        for skill_name, is_req in all_skills:
            master_skill = db.query(Skill).filter(Skill.name.ilike(skill_name)).first()
            if not master_skill:
                master_skill = Skill(name=skill_name, category=SkillCategory.OTHER)
                db.add(master_skill)
                db.commit()
                db.refresh(master_skill)
            
            job_skill_entry = JobSkill(job_id=job_id, skill_id=master_skill.id, is_required=is_req)
            db.add(job_skill_entry)

    db.commit()
    db.refresh(db_job)

    # Regenerate embedding if title/description changed
    if text_changed:
        combined_text = f"{db_job.title}\n{db_job.description}"
        # Delete old embedding record to force regeneration
        from app.models.embedding import Embedding, EmbeddingSourceType
        db.query(Embedding).filter(
            Embedding.source_type == EmbeddingSourceType.JOB,
            Embedding.job_id == job_id
        ).delete()
        db.commit()

        embedding_service = EmbeddingService()
        embedding_service.get_or_create_job_embedding(db, db_job.id, combined_text)

    return db_job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    current_user: User = Depends(require_role(UserRole.RECRUITER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Delete a job posting.
    Only allows owner recruiter or admins to delete.
    """
    db_job = db.query(Job).filter(Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found.")

    # Authorization Check
    if current_user.role == UserRole.RECRUITER and db_job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this job."
        )

    db.delete(db_job)
    db.commit()
    return None
