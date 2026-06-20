"""
Authentication API endpoints.
Provides user registration, login, and password reset capability.
"""

import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.password_reset import PasswordReset
from app.auth.password import hash_password, verify_password
from app.auth.jwt_handler import create_access_token
from app.schemas.auth import (
    UserRegister, 
    UserResponse, 
    TokenResponse, 
    UserLogin,
    ForgotPasswordRequest,
    VerifyResetCodeRequest,
    ResetPasswordRequest
)

router = APIRouter(tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user (candidate or recruiter).
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password to receive a JWT access token.
    """
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Generate token
    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Generate a 6-digit verification code, save it to the database, and log it.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email address not found",
        )

    # Invalidate any existing unused reset codes for this email
    db.query(PasswordReset).filter(
        PasswordReset.email == request.email,
        PasswordReset.is_used == False
    ).update({PasswordReset.is_used: True}, synchronize_session=False)

    # Generate a 6-digit random verification code
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    # Create new reset entry
    reset_record = PasswordReset(
        email=request.email,
        code=code,
        expires_at=expires_at,
        is_used=False
    )
    db.add(reset_record)
    db.commit()

    # Log/Print code to terminal for debugging and test visibility
    print(f"\n==================================================")
    print(f" PASSWORD RESET CODE FOR {request.email}: {code} ")
    print(f"==================================================\n")

    # Send code to candidate's email using the SMTP service
    try:
        from app.services.email_service import InterviewEmailService
        
        subject = "Reset Your Password - Semantic ATS"
        body = (
            f"Hello {user.name},\n\n"
            f"We received a request to reset your password on Semantic ATS.\n\n"
            f"Your 6-digit verification code is:\n"
            f"👉 {code}\n\n"
            f"This code is valid for 15 minutes. If you did not request this, please ignore this email.\n\n"
            f"Best regards,\n"
            f"Semantic ATS Team"
        )
        InterviewEmailService.send_email_smtp(
            to_email=request.email,
            subject=subject,
            body=body
        )
    except Exception as e:
        print(f"Error sending forgot password email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send reset code email: {str(e)}"
        )

    return {
        "message": "Reset code sent to email"
    }


@router.post("/verify-reset-code", status_code=status.HTTP_200_OK)
def verify_reset_code(request: VerifyResetCodeRequest, db: Session = Depends(get_db)):
    """
    Verify the 6-digit reset code matches and hasn't expired.
    """
    reset_record = db.query(PasswordReset).filter(
        PasswordReset.email == request.email,
        PasswordReset.code == request.code,
        PasswordReset.is_used == False
    ).order_by(PasswordReset.created_at.desc()).first()

    if not reset_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset code or email address",
        )

    if reset_record.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset code has expired",
        )

    return {"message": "Code verified successfully"}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Verify the reset code and update user's password.
    """
    reset_record = db.query(PasswordReset).filter(
        PasswordReset.email == request.email,
        PasswordReset.code == request.code,
        PasswordReset.is_used == False
    ).order_by(PasswordReset.created_at.desc()).first()

    if not reset_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset code or email address",
        )

    if reset_record.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset code has expired",
        )

    # Update password
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.password_hash = hash_password(request.new_password)
    reset_record.is_used = True
    db.commit()

    return {"message": "Password reset successfully"}

