from typing import Generator
from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

_engine = None
_SessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        db_uri = settings.sqlalchemy_database_uri
        _engine = create_engine(
            db_uri,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            connect_args={"prepare_threshold": None},
        )
    return _engine


def get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionFactory


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy database session.
    Ensures the session is cleanly closed after each request.
    Handles unconfigured/failing database connections gracefully without leaking secrets.
    """
    try:
        session_factory = get_session_factory()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable or not configured.",
        )

    db = session_factory()
    try:
        yield db
    finally:
        db.close()
