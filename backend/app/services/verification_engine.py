"""
Central Verification Engine for Part 5A
Coordinates adapter resolution, claim input validation, timeout protection,
response normalization, and error encapsulation across all verification types.
"""

import asyncio
import logging
from typing import Any, Optional

from app.core.verification_config import verification_settings
from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.registry import adapter_registry
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)

logger = logging.getLogger(__name__)


class VerificationEngine:
    """
    Core Verification Engine responsible for executing adapter calls,
    enforcing deterministic fallbacks, and standardizing verification outputs.
    """

    async def execute_verification(
        self,
        request: VerificationRequest,
    ) -> VerificationResult:
        """
        Executes a verification request against the registered adapter.
        Safely traps exceptions, enforces timeout limits, and normalizes output.
        """
        # 1. Missing Input Validation Check
        if not request.claimed_value or not str(request.claimed_value).strip():
            logger.warning(
                "Verification requested for type '%s' with empty/missing claimed value.",
                request.verification_type,
            )
            return VerificationResult(
                verification_type=request.verification_type,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name="Verification Engine",
                source_type=VerificationSourceType.INTERNAL,
                claimed_value="",
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={
                    "field": request.verification_type.lower(),
                    "reason": "MISSING_VERIFICATION_VALUE",
                    "matched": False,
                },
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="Verification claim value was empty or missing.",
            )

        # 2. Adapter Resolution from Registry
        adapter = adapter_registry.get_adapter(request.verification_type)
        if not adapter:
            logger.error("No verification adapter registered for type '%s'", request.verification_type)
            return VerificationResult(
                verification_type=request.verification_type,
                verification_status=VerificationStatus.FAILED,
                source_name="Verification Engine",
                source_type=VerificationSourceType.INTERNAL,
                claimed_value=str(request.claimed_value),
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"error": f"Adapter not registered for {request.verification_type}"},
                error_code=VerificationErrorCode.ADAPTER_NOT_FOUND,
                error_message=f"No verification adapter registered for verification type '{request.verification_type}'.",
            )

        # 3. Upstream Liveness / Availability Check
        if not adapter.is_available():
            logger.warning(
                "Adapter '%s' for type '%s' is reported unavailable.",
                adapter.source_name,
                request.verification_type,
            )
            return VerificationResult(
                verification_type=request.verification_type,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=adapter.source_name,
                source_type=adapter.source_type,
                claimed_value=str(request.claimed_value),
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"source": adapter.source_name, "available": False},
                error_code=VerificationErrorCode.SOURCE_UNAVAILABLE,
                error_message=f"Verification source '{adapter.source_name}' is currently unavailable.",
            )

        # 4. Dispatch to Adapter with Timeout Protection
        try:
            timeout_sec = verification_settings.VERIFICATION_TIMEOUT_SECONDS
            result = await asyncio.wait_for(
                adapter.verify(request),
                timeout=float(timeout_sec),
            )
            return result

        except asyncio.TimeoutError:
            logger.error(
                "Verification call timed out for type '%s' after %ss",
                request.verification_type,
                verification_settings.VERIFICATION_TIMEOUT_SECONDS,
            )
            return VerificationResult(
                verification_type=request.verification_type,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=adapter.source_name,
                source_type=adapter.source_type,
                claimed_value=str(request.claimed_value),
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"error": "SOURCE_TIMEOUT", "source": adapter.source_name},
                error_code=VerificationErrorCode.SOURCE_TIMEOUT,
                error_message=f"Verification source '{adapter.source_name}' did not respond within {timeout_sec} seconds.",
            )

        except Exception as exc:
            logger.exception(
                "Unexpected internal error executing adapter '%s': %s",
                adapter.source_name,
                exc,
            )
            return VerificationResult(
                verification_type=request.verification_type,
                verification_status=VerificationStatus.FAILED,
                source_name=adapter.source_name,
                source_type=adapter.source_type,
                claimed_value=str(request.claimed_value),
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"error": "INTERNAL_FAILURE"},
                error_code=VerificationErrorCode.VERIFICATION_FAILED,
                error_message="An internal technical failure occurred during claim verification.",
            )


verification_engine = VerificationEngine()
