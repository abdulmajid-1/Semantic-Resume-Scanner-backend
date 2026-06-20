"""
Password Reset model — stores temporary reset codes for forgot-password flow.
Codes expire after 15 minutes and are single-use.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime, timezone, timedelta

from app.database.base import Base


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def is_expired(self) -> bool:
        """Check if the reset code has expired."""
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    def __repr__(self):
        return f"<PasswordReset(id={self.id}, email='{self.email}', is_used={self.is_used})>"
