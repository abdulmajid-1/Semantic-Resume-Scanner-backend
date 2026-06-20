"""
Application configuration module.
Loads settings from environment variables / .env file using pydantic-settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/semantic_ats"

    # JWT Authentication
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # File Uploads
    UPLOAD_DIR: str = "./uploads"

    # AI Model
    MODEL_NAME: str = "all-MiniLM-L6-v2"

    # FAISS Index
    FAISS_INDEX_PATH: str = "./faiss_index"

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # Ranking Weights (configurable)
    SEMANTIC_WEIGHT: float = 0.60
    SKILL_WEIGHT: float = 0.20
    EXPERIENCE_WEIGHT: float = 0.20

    # SMTP Email Configuration (Gmail)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Semantic ATS Recruitment"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — created once, reused across the app."""
    return Settings()
