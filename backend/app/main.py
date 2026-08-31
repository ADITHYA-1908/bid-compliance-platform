import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.api.v1.router import api_v1_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for the AI-Powered Bid Compliance Verification Platform for GeM Procurement",
    version=settings.VERSION,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/", summary="Root endpoint")
def root():
    return {"message": "BidVerify AI Backend is running"}


@app.get("/health", summary="Basic service health check")
def health_check():
    return {"status": "healthy"}


@app.get("/health/database", summary="Database connectivity health check")
def health_database_check(db: Session = Depends(get_db)):
    """
    Checks connection to PostgreSQL database.
    Does not leak connection strings or credentials on failure.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        )
