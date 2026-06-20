"""
Semantic Search API Router.
Exposes FAISS search query endpoint to recruiters.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.auth.dependencies import require_role
from app.faiss_search.faiss_service import FAISSSearchService
from app.schemas.search import SearchQuery, SearchResult

router = APIRouter(tags=["Semantic Candidate Search"])


@router.post("/search", response_model=List[SearchResult])
def semantic_search(
    search_data: SearchQuery,
    current_user: User = Depends(require_role(UserRole.RECRUITER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Search candidates semantically based on a natural language query.
    Example query: "React and Node.js Developer with 3+ years experience"
    Only accessible by Recruiters and Admins.
    """
    faiss_service = FAISSSearchService()
    try:
        results = faiss_service.search_candidates(
            db=db,
            query=search_data.query,
            top_k=search_data.top_k
        )
        return [SearchResult(**r) for r in results]
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Semantic search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while executing the search."
        )


@router.post("/search/rebuild", status_code=status.HTTP_200_OK)
def rebuild_search_index(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Admin-only utility to force-rebuild the FAISS index from scratch.
    """
    faiss_service = FAISSSearchService()
    faiss_service.rebuild_index(db)
    return {"message": "FAISS index rebuilt successfully."}
