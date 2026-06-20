"""
JWT token handler — creates and verifies JSON Web Tokens for authentication.
"""

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.config import get_settings

settings = get_settings()


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token with an expiration time.
    
    Args:
        data: Dictionary of claims to encode (must include 'sub' for user ID).
    
    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The JWT token string to verify.
    
    Returns:
        Decoded token payload.
    
    Raises:
        JWTError: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise JWTError("Invalid or expired token")
