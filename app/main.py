"""
FastAPI Application Entry Point.
Sets up CORS, mounts API routers, and configures startup/shutdown events.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from app.config import get_settings
from app.database.connection import engine
from app.database.base import Base
from app.api import auth, resume, jobs, matching, search, admin, dashboard, interview

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Semantic ATS: AI-Based Resume Intelligence & Candidate Ranking System",
    description="Backend API powering Semantic screening, parsing, matching, search, and analytics.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
# Allows requests from React Frontend (supports Vite auto-port-increment)
cors_origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://localhost:5174",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """
    Actions performed on application startup:
    1. Ensure database tables exist (if not using Alembic explicitly)
    2. Warm up / load the SentenceTransformer model (in background thread)
    3. Load FAISS index or build it if missing (in background thread)
    """
    logger.info("Application starting up...")
    
    # 1. Create tables if they don't exist
    logger.info("Verifying database schema...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema verification completed.")
    except Exception as e:
        logger.error(f"Failed to verify/create database tables: {e}")

    # 2 & 3. Load models and FAISS index in a background thread
    # This prevents blocking the port binding on Render's free tier
    import threading

    def _load_models():
        try:
            from app.embeddings.embedding_service import EmbeddingService
            EmbeddingService()
            logger.info("SentenceTransformer model ready.")
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")

        try:
            from app.database.connection import SessionLocal
            from app.faiss_search.faiss_service import FAISSSearchService
            db = SessionLocal()
            faiss_service = FAISSSearchService()
            if faiss_service.index.ntotal == 0:
                logger.info("FAISS index is empty. Performing initial build from database...")
                faiss_service.rebuild_index(db)
            db.close()
            logger.info("FAISS index ready.")
        except Exception as e:
            logger.error(f"Failed to initialize FAISS index search: {e}")

    thread = threading.Thread(target=_load_models, daemon=True)
    thread.start()
    logger.info("Background model loading started. Server is accepting requests.")



# Register routers under /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(resume.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(matching.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(interview.router, prefix="/api")


@app.get("/api/health", tags=["Health"])
def health_check():
    """
    Simple API health check endpoint.
    """
    return {"status": "healthy", "service": "semantic-ats-backend"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
