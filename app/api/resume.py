"""
Resume upload and details API endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
import os
import uuid
import logging

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.resume import Resume
from app.auth.dependencies import get_current_user
from app.resume_parser.pdf_parser import extract_text_from_pdf
from app.resume_parser.docx_parser import extract_text_from_docx
from app.resume_parser.parser_service import ResumeParserService
from app.skill_extractor.extractor_service import SkillExtractorService
from app.embeddings.embedding_service import EmbeddingService
from app.schemas.resume import ResumeUploadResponse, ResumeDetailResponse
from app.config import get_settings

router = APIRouter(tags=["Resumes"])
logger = logging.getLogger(__name__)
settings = get_settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


@router.post("/resume/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and parse a candidate's resume (PDF or DOCX).
    Extracts structure, extracts skills, and generates embeddings.
    """
    # 1. Validate file extension
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are allowed."
        )

    # 2. Save file to disk securely
    file_id = str(uuid.uuid4())
    save_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")
    try:
        with open(save_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file on server."
        )

    # 3. Extract text depending on type
    try:
        raw_text = ""
        if ext == ".pdf":
            raw_text = extract_text_from_pdf(save_path)
        elif ext == ".docx":
            raw_text = extract_text_from_docx(save_path)
    except Exception as e:
        logger.error(f"Text extraction failed: {e}", exc_info=True)
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text from the document: {str(e)}"
        )

    if not raw_text.strip():
        # Clean up file on failure
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract any text from the document. Please check the file formatting."
        )

    try:
        # 4. Parse fields using Parser Service
        parser_service = ResumeParserService()
        parsed_data = parser_service.parse_resume(raw_text)

        # 5. Create Resume in DB
        db_resume = Resume(
            user_id=current_user.id,
            file_path=save_path,
            file_type=ext.lstrip('.'),
            raw_text=raw_text,
            parsed_name=parsed_data.name or current_user.name,
            parsed_email=parsed_data.email or current_user.email,
            parsed_phone=parsed_data.phone,
            education=parsed_data.education,
            experience=parsed_data.experience,
            projects=parsed_data.projects,
            certifications=parsed_data.certifications,
            years_of_experience=parsed_data.years_of_experience
        )
        db.add(db_resume)
        db.commit()
        db.refresh(db_resume)

        # 6. Extract and Save Skills
        try:
            extractor_service = SkillExtractorService()
            extracted_skills = extractor_service.extract_skills_from_text(raw_text)
            extractor_service.save_candidate_skills(db, db_resume.id, extracted_skills)
        except Exception as e:
            logger.warning(f"Skill extraction failed (non-fatal): {e}", exc_info=True)

        # 7. Generate and Cache Embedding
        try:
            embedding_service = EmbeddingService()
            embedding_service.get_or_create_resume_embedding(db, db_resume.id, raw_text)
        except Exception as e:
            logger.warning(f"Embedding generation failed (non-fatal): {e}", exc_info=True)

        # 8. Rebuild FAISS search index
        try:
            from app.faiss_search.faiss_service import FAISSSearchService
            faiss_service = FAISSSearchService()
            faiss_service.add_resume_to_index(db_resume.id, raw_text)
        except Exception as e:
            logger.warning(f"FAISS index update skipped or failed: {e}")

        return db_resume

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume upload pipeline failed: {e}", exc_info=True)
        # Clean up the saved file on failure
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume processing failed: {str(e)}"
        )


@router.get("/resume/{resume_id}", response_model=ResumeDetailResponse)
def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed parsed resume information by resume ID.
    Only allows Candidates to view their own resume, and Recruiters/Admins to view any.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found."
        )

    # Authorization Check
    if current_user.role == UserRole.CANDIDATE and resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this resume."
        )

    # Compile skill list for output
    skill_names = [cs.skill.name for cs in resume.candidate_skills]

    # Map to schema output
    return ResumeDetailResponse(
        id=resume.id,
        user_id=resume.user_id,
        file_path=resume.file_path,
        file_type=resume.file_type,
        parsed_name=resume.parsed_name,
        parsed_email=resume.parsed_email,
        parsed_phone=resume.parsed_phone,
        education=resume.education,
        experience=resume.experience,
        projects=resume.projects,
        certifications=resume.certifications,
        years_of_experience=resume.years_of_experience,
        skills=skill_names,
        raw_text=resume.raw_text,
        created_at=resume.created_at
    )


@router.get("/resume/{resume_id}/download")
def download_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download/stream candidate's raw resume file (PDF/DOCX).
    Allows candidate to download their own, and recruiter/admin to download any.
    If the physical file doesn't exist on disk (e.g. seeded database), return raw text representation.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found."
        )

    # Authorization Check
    if current_user.role == UserRole.CANDIDATE and resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to download this resume."
        )

    # Check if file exists, if not, fallback to plain text representation from database
    if not resume.file_path or not os.path.exists(resume.file_path):
        from fastapi.responses import Response
        name_slug = "".join(c for c in (resume.parsed_name or "Resume") if c.isalnum() or c in (" ", "-", "_")).strip()
        name_slug = name_slug.replace(" ", "_")
        
        headers = {
            'Content-Disposition': f'attachment; filename="{name_slug}_Resume.txt"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        return Response(content=resume.raw_text or "No text content available.", media_type="text/plain", headers=headers)

    # Serve the original file
    from fastapi.responses import FileResponse
    name_slug = "".join(c for c in (resume.parsed_name or "Resume") if c.isalnum() or c in (" ", "-", "_")).strip()
    name_slug = name_slug.replace(" ", "_")
    filename = f"{name_slug}_Resume.{resume.file_type}"
    
    media_type = "application/pdf" if resume.file_type == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Access-Control-Expose-Headers': 'Content-Disposition'
    }
    
    return FileResponse(
        path=resume.file_path,
        filename=filename,
        media_type=media_type,
        headers=headers
    )
