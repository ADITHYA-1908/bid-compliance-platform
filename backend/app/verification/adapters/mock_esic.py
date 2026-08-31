"""
Mock ESIC Verification Adapter for Part 5C
Provides deterministic Employees' State Insurance Corporation employer verification against synthetic fixtures.
Validates employer identity and preserves registration status (ACTIVE, INACTIVE) and regional office state.
Does NOT invoke external ESIC portal APIs.
"""

import re
from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_ESIC_REGISTRY
from app.verification.normalizers import (
    compare_names,
    compare_strings,
    normalize_esic_code,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)

# Standard ESIC 17-digit numeric employer code
ESIC_PATTERN = re.compile(r'^[0-9]{17}$')


class MockESICVerificationAdapter(VerificationAdapter):
    """
    Deterministic Mock ESIC Employer Verification Adapter.
    """

    @property
    def source_name(self) -> str:
        return "Mock ESIC Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.ESIC

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if not claimed_value or not isinstance(claimed_value, str):
            return False, "ESIC employer registration number must be a non-empty string."

        cleaned = normalize_esic_code(claimed_value)
        if not ESIC_PATTERN.match(cleaned):
            return False, f"Invalid ESIC employer code '{cleaned}'. Must be exactly 17 digits."

        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        if not request.claimed_value:
            return VerificationResult(
                verification_type=VerificationType.ESIC,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "MISSING_VERIFICATION_VALUE"},
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="No ESIC employer code was provided for verification.",
            )

        is_valid, validation_err = self.validate_input(request.claimed_value)
        if not is_valid:
            return VerificationResult(
                verification_type=VerificationType.ESIC,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                evidence={
                    "field": "esic_registration_number",
                    "claimed_value": request.claimed_value,
                    "validation_error": validation_err,
                    "matched": False,
                },
                error_code=VerificationErrorCode.VERIFICATION_INPUT_INVALID,
                error_message=validation_err,
            )

        code = normalize_esic_code(request.claimed_value)
        record = MOCK_ESIC_REGISTRY.get(code)

        # 1. Simulated Source Outage
        if record and record.get("status") == "UNAVAILABLE":
            return VerificationResult(
                verification_type=VerificationType.ESIC,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=code,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={
                    "field": "esic_registration_number",
                    "claimed_value": code,
                    "source": self.source_name,
                    "simulated_outage": True,
                },
                raw_response=record,
                error_code=record.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=record.get("error_message", "Mock ESIC Registry is currently unavailable."),
            )

        # 2. Not Found in Mock Registry
        if not record:
            return VerificationResult(
                verification_type=VerificationType.ESIC,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=code,
                verified_value=None,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                match_summary={"identifier": VerificationMatchStatus.MISMATCH},
                evidence={
                    "field": "esic_registration_number",
                    "claimed_value": code,
                    "source": self.source_name,
                    "matched": False,
                    "details": "ESIC employer code not found in Mock ESIC Registry records.",
                },
                raw_response={"found": False, "employer_code": code},
                error_code=None,
                error_message="ESIC employer code was not found in Mock ESIC Registry records.",
            )

        # 3. Found in Registry: Compare Primary and Supporting Claims
        claimed_name = (
            request.supporting_claims.get("employer_name")
            or request.supporting_claims.get("company_name")
            or request.supporting_claims.get("legal_name")
            or request.extra_context.get("employer_name")
        )

        registry_code = record.get("employer_code") or record.get("registration_number", code)
        registry_name = record.get("employer_name", "")
        registry_status = record.get("registration_status", "ACTIVE")
        regional_office = record.get("regional_office", "")
        state = record.get("state", "")

        # Compare fields
        id_match = VerificationMatchStatus.MATCH
        name_match, name_confidence = compare_names(claimed_name, registry_name)

        match_summary: Dict[str, str] = {
            "identifier": id_match,
            "employer_name": name_match,
            "registration_status": registry_status,
        }

        normalized_claim_payload: Dict[str, Any] = {
            "esic_registration_number": code,
            "employer_name": claimed_name,
        }

        normalized_verified_payload: Dict[str, Any] = {
            "esic_registration_number": registry_code,
            "employer_code": registry_code,
            "employer_name": registry_name,
            "registration_status": registry_status,
            "regional_office": regional_office,
            "state": state,
            "registration_date": record.get("registration_date"),
        }

        # Determine Verification Status and Confidence
        if claimed_name and name_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.60
            reason_msg = f"ESIC employer '{code}' found, but claimed name '{claimed_name}' differs from registry name '{registry_name}'."
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else VerificationMatchStatus.PARTIAL_MATCH
            confidence = 1.0 if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else 0.95
            reason_msg = f"ESIC employer '{code}' authenticated against Mock ESIC Registry (Status: {registry_status}, RO: {regional_office})."

        evidence_payload: Dict[str, Any] = {
            "field": "esic_registration_number",
            "claimed_value": code,
            "verified_value": registry_code,
            "source": self.source_name,
            "matched": v_status == VerificationStatus.VERIFIED,
            "name_match": name_match,
            "claimed_employer_name": claimed_name,
            "employer_name": registry_name,
            "registry_employer_name": registry_name,
            "registration_status": registry_status,
            "regional_office": regional_office,
            "state": state,
            "reason": reason_msg,
        }

        return VerificationResult(
            verification_type=VerificationType.ESIC,
            verification_status=v_status,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=code,
            verified_value=registry_code,
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
