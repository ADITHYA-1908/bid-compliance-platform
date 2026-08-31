"""
Mock Startup India Verification Adapter for Part 5C
Provides deterministic DPIIT / Startup India recognition verification against synthetic fixtures.
Validates startup entity identity and preserves recognition status (RECOGNIZED, EXPIRED, etc.) and sector.
Does NOT invoke external Startup India portal APIs.
"""

import re
from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_STARTUP_INDIA_REGISTRY
from app.verification.normalizers import (
    compare_names,
    compare_strings,
    normalize_startup_number,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)

# Standard DPIIT recognition pattern: DIPP followed by numbers, or STARTUP-XX...
STARTUP_PATTERN = re.compile(r'^(DIPP|DPIIT|STARTUP)[\-_0-9A-Z]+$', re.IGNORECASE)


class MockStartupIndiaVerificationAdapter(VerificationAdapter):
    """
    Deterministic Mock Startup India DPIIT Verification Adapter.
    """

    @property
    def source_name(self) -> str:
        return "Mock Startup India Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.STARTUP_INDIA

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if not claimed_value or not isinstance(claimed_value, str):
            return False, "Startup India recognition number must be a non-empty string."

        cleaned = normalize_startup_number(claimed_value)
        if not STARTUP_PATTERN.match(cleaned) and len(cleaned) < 4:
            return False, f"Invalid Startup India recognition format '{cleaned}'. Must start with DIPP/DPIIT/STARTUP or be a valid identifier."

        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        if not request.claimed_value:
            return VerificationResult(
                verification_type=VerificationType.STARTUP_INDIA,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "MISSING_VERIFICATION_VALUE"},
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="No Startup India recognition number was provided for verification.",
            )

        is_valid, validation_err = self.validate_input(request.claimed_value)
        if not is_valid:
            return VerificationResult(
                verification_type=VerificationType.STARTUP_INDIA,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                evidence={
                    "field": "recognition_number",
                    "claimed_value": request.claimed_value,
                    "validation_error": validation_err,
                    "matched": False,
                },
                error_code=VerificationErrorCode.VERIFICATION_INPUT_INVALID,
                error_message=validation_err,
            )

        rec_number = normalize_startup_number(request.claimed_value)
        record = MOCK_STARTUP_INDIA_REGISTRY.get(rec_number)

        # 1. Simulated Source Outage
        if record and record.get("status") == "UNAVAILABLE":
            return VerificationResult(
                verification_type=VerificationType.STARTUP_INDIA,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=rec_number,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={
                    "field": "recognition_number",
                    "claimed_value": rec_number,
                    "source": self.source_name,
                    "simulated_outage": True,
                },
                raw_response=record,
                error_code=record.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=record.get("error_message", "Mock Startup India Registry is currently unavailable."),
            )

        # 2. Not Found in Mock Registry
        if not record:
            return VerificationResult(
                verification_type=VerificationType.STARTUP_INDIA,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=rec_number,
                verified_value=None,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                match_summary={"identifier": VerificationMatchStatus.MISMATCH},
                evidence={
                    "field": "recognition_number",
                    "claimed_value": rec_number,
                    "source": self.source_name,
                    "matched": False,
                    "details": "Recognition number not found in Mock Startup India Registry records.",
                },
                raw_response={"found": False, "recognition_number": rec_number},
                error_code=None,
                error_message="Startup India recognition number was not found in Mock Registry records.",
            )

        # 3. Found in Registry: Compare Primary and Supporting Claims
        claimed_name = (
            request.supporting_claims.get("entity_name")
            or request.supporting_claims.get("company_name")
            or request.supporting_claims.get("legal_name")
            or request.extra_context.get("entity_name")
        )

        registry_rec = record.get("recognition_number") or record.get("startup_india_number", rec_number)
        registry_name = record.get("entity_name", "")
        registry_status = record.get("startup_status", "RECOGNIZED")
        registry_date = record.get("recognition_date")
        registry_valid_until = record.get("valid_until")
        registry_sector = record.get("sector")

        # Compare fields
        id_match = VerificationMatchStatus.MATCH
        name_match, name_confidence = compare_names(claimed_name, registry_name)

        match_summary: Dict[str, str] = {
            "identifier": id_match,
            "entity_name": name_match,
            "startup_status": registry_status,
        }

        normalized_claim_payload: Dict[str, Any] = {
            "recognition_number": rec_number,
            "entity_name": claimed_name,
        }

        normalized_verified_payload: Dict[str, Any] = {
            "recognition_number": registry_rec,
            "entity_name": registry_name,
            "startup_status": registry_status,
            "recognition_date": registry_date,
            "valid_until": registry_valid_until,
            "sector": registry_sector,
            "state": record.get("state"),
        }

        # Determine Verification Status and Confidence
        if claimed_name and name_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.60
            reason_msg = f"Startup India recognition '{rec_number}' found, but claimed entity name '{claimed_name}' differs from registry name '{registry_name}'."
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else VerificationMatchStatus.PARTIAL_MATCH
            confidence = 1.0 if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else 0.95
            reason_msg = f"Startup India recognition '{rec_number}' authenticated against Mock DPIIT Registry (Status: {registry_status})."

        evidence_payload: Dict[str, Any] = {
            "field": "recognition_number",
            "claimed_value": rec_number,
            "verified_value": registry_rec,
            "source": self.source_name,
            "matched": v_status == VerificationStatus.VERIFIED,
            "name_match": name_match,
            "claimed_entity_name": claimed_name,
            "entity_name": registry_name,
            "registry_entity_name": registry_name,
            "startup_status": registry_status,
            "registration_status": registry_status,
            "recognition_date": registry_date,
            "valid_until": registry_valid_until,
            "sector": registry_sector,
            "reason": reason_msg,
        }

        return VerificationResult(
            verification_type=VerificationType.STARTUP_INDIA,
            verification_status=v_status,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=rec_number,
            verified_value=registry_rec,
            match_status=overall_match,
            confidence=confidence,
            match_summary=match_summary,
            evidence=evidence_payload,
            normalized_claim_payload=normalized_claim_payload,
            normalized_verified_payload=normalized_verified_payload,
            raw_response=record,
            error_code=None,
            error_message=reason_msg if v_status == VerificationStatus.NEEDS_REVIEW else None,
        )
