import os
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure backend root is always resolved
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "BidVerify AI API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Database Configuration
    DATABASE_URL: Optional[str] = None

    # Storage Configuration (Supabase Storage / Local Fallback)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "bid-documents"
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB per file limit
    LOCAL_STORAGE_DIR: str = str(BACKEND_DIR / "storage" / "bid_documents")

    # JWT Authentication Configuration
    JWT_SECRET_KEY: str = "bidverify-dev-secret-key-replace-in-production-f3a7c89b2d"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS Settings
    FRONTEND_URL: Optional[str] = None
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # AI & RAG Configuration (Part 7E)
    EMBEDDING_PROVIDER: str = "local_fallback"  # 'openai', 'gemini', 'local_fallback'
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    LLM_PROVIDER: str = "local_fallback"  # 'openai', 'gemini', 'local_fallback'
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_OUTPUT_TOKENS: int = 1500
    RAG_TOP_K: int = 10
    RAG_SIMILARITY_THRESHOLD: float = 0.5
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None


    @property
    def cors_origins_list(self) -> List[str]:
        origins = list(self.CORS_ORIGINS)
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return origins

    @property
    def sqlalchemy_database_uri(self) -> str:
        """
        Returns SQLAlchemy-compatible database URI.
        Normalizes 'postgresql://' or 'postgres://' to 'postgresql+psycopg://'
        for psycopg3 driver compatibility.
        """
        if not self.DATABASE_URL:
            raise ValueError(
                f"DATABASE_URL is not set. Please configure DATABASE_URL in {ENV_FILE}"
            )
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def database_host(self) -> str:
        """
        Safely extracts and returns only the database hostname for debugging,
        never exposing password or sensitive query parameters.
        """
        if not self.DATABASE_URL:
            return "<DATABASE_URL NOT SET>"
        try:
            url = self.DATABASE_URL
            if "://" in url:
                parsed = urlparse(url)
                return parsed.hostname or "<unknown>"
            return "<invalid format>"
        except Exception:
            return "<error parsing host>"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE if ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
