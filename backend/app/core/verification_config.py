"""
Verification Configuration for Part 5A
Provides centralized settings, operational modes (mock, sandbox, official),
and timeout foundations for verification adapters.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.config import ENV_FILE


class VerificationSettings(BaseSettings):
    # Verification Mode: "mock" | "sandbox" | "official"
    VERIFICATION_MODE: str = "mock"

    # Adapter Request Timeouts (in seconds)
    VERIFICATION_TIMEOUT_SECONDS: int = 15
    VERIFICATION_MAX_RETRIES: int = 3

    # Future Provider Endpoint URLs (Placeholders for official/sandbox APIs)
    GST_API_BASE_URL: Optional[str] = None
    PAN_API_BASE_URL: Optional[str] = None
    UDYAM_API_BASE_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=ENV_FILE if ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


verification_settings = VerificationSettings()
