"""
Admin API Router.
Provides administrative endpoints for user management and global analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.auth.dependencies import require_role
from app.services.stats_service import StatsService
from app.schemas.auth import UserResponse

router = APIRouter(tags=["Admin Operations"])


class RoleUpdateRequest(BaseModel):
    role: UserRole


@router.get("/admin/users", response_model=List[UserResponse])
def get_all_users(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    List all users in the system. Admin-only.
    """
    return db.query(User).order_by(User.id.asc()).all()


@router.put("/admin/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    request: RoleUpdateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Change a user's role (e.g. elevate a Candidate to Recruiter). Admin-only.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own admin role."
        )

    user.role = request.role
    db.commit()
    db.refresh(user)
    return user


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Force-delete a user profile and all associated data. Admin-only.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own admin account."
        )

    db.delete(user)
    db.commit()
    return None


@router.get("/admin/stats")
def get_system_statistics(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Get system-wide analytics for the Admin Dashboard.
    """
    return StatsService.get_admin_stats(db)
