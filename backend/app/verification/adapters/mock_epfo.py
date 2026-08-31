"""
Mock EPFO Verification Adapter for Part 5C
Provides deterministic Employees' Provident Fund Organisation establishment verification against synthetic fixtures.
Validates establishment identity and preserves coverage status (ACTIVE, INACTIVE) and office state.
Does NOT invoke external EPFO portal APIs.
"""

import re
from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_EPFO_REGISTRY
from app.verification.normalizers import (
    compare_names,
    compare_strings,
    normalize_epfo_code,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)

# Standard EPFO establishment code regex: 15 alphanumeric characters
EPFO_PATTERN = re.compile(r'^[A-Z0-9]{15}$')


class MockEPFOVerificationAdapter(VerificationAdapter):
    """
    Deterministic Mock EPFO Establishment Verification Adapter.
    """

    @property
    def source_name(self) -> str:
        return "Mock EPFO Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.EPFO

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if not claimed_value or not isinstance(claimed_value, str):
            return False, "EPFO establishment code must be a non-empty string."

        cleaned = normalize_epfo_code(claimed_value)
        if not EPFO_PATTERN.match(cleaned):
            return False, f"Invalid EPFO establishment code '{cleaned}'. Must be 15 alphanumeric characters."

        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        if not request.claimed_value:
            return VerificationResult(
                verification_type=VerificationType.EPFO,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "MISSING_VERIFICATION_VALUE"},
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="No EPFO establishment code was provided for verification.",
            )

        is_valid, validation_err = self.validate_input(request.claimed_value)
        if not is_valid:
            return VerificationResult(
                verification_type=VerificationType.EPFO,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                evidence={
                    "field": "epfo_registration_number",
                    "claimed_value": request.claimed_value,
                    "validation_error": validation_err,
                    "matched": False,
                },
                error_code=VerificationErrorCode.VERIFICATION_INPUT_INVALID,
                error_message=validation_err,
            )

        code = normalize_epfo_code(request.claimed_value)
        record = MOCK_EPFO_REGISTRY.get(code)

        # 1. Simulated Source Outage
        if record and record.get("status") == "UNAVAILABLE":
            return VerificationResult(
                verification_type=VerificationType.EPFO,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=code,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={
                    "field": "epfo_registration_number",
                    "claimed_value": code,
                    "source": self.source_name,
                    "simulated_outage": True,
                },
                raw_response=record,
                error_code=record.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=record.get("error_message", "Mock EPFO Registry is currently unavailable."),
            )

        # 2. Not Found in Mock Registry
        if not record:
            return VerificationResult(
                verification_type=VerificationType.EPFO,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=code,
                verified_value=None,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                match_summary={"identifier": VerificationMatchStatus.MISMATCH},
                evidence={
                    "field": "epfo_registration_number",
                    "claimed_value": code,
                    "source": self.source_name,
                    "matched": False,
                    "details": "EPFO establishment code not found in Mock EPFO Registry records.",
                },
                raw_response={"found": False, "establishment_code": code},
                error_code=None,
                error_message="EPFO establishment code was not found in Mock EPFO Registry records.",
            )

        # 3. Found in Registry: Compare Primary and Supporting Claims
        claimed_name = (
            request.supporting_claims.get("establishment_name")
            or request.supporting_claims.get("company_name")
            or request.supporting_claims.get("legal_name")
            or request.extra_context.get("establishment_name")
        )

        registry_code = record.get("establishment_code") or record.get("registration_number", code)
        registry_name = record.get("establishment_name", "")
        registry_status = record.get("registration_status") or record.get("coverage_status", "ACTIVE")
        office_name = record.get("office_name", "")
        state = record.get("state", "")

        # Compare fields
        id_match = VerificationMatchStatus.MATCH
        name_match, name_confidence = compare_names(claimed_name, registry_name)

        match_summary: Dict[str, str] = {
            "identifier": id_match,
            "establishment_name": name_match,
            "registration_status": registry_status,
        }

        normalized_claim_payload: Dict[str, Any] = {
            "epfo_registration_number": code,
            "establishment_name": claimed_name,
        }

        normalized_verified_payload: Dict[str, Any] = {
            "epfo_registration_number": registry_code,
            "establishment_code": registry_code,
            "establishment_name": registry_name,
            "registration_status": registry_status,
            "office_name": office_name,
            "state": state,
            "coverage_date": record.get("coverage_date"),
        }

        # Determine Verification Status and Confidence
        if claimed_name and name_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.60
            reason_msg = f"EPFO establishment '{code}' found, but claimed name '{claimed_name}' differs from registry name '{registry_name}'."
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else VerificationMatchStatus.PARTIAL_MATCH
            confidence = 1.0 if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else 0.95
            reason_msg = f"EPFO establishment '{code}' authenticated against Mock EPFO Registry (Status: {registry_status}, Office: {office_name})."

        evidence_payload: Dict[str, Any] = {
            "field": "epfo_registration_number",
            "claimed_value": code,
            "verified_value": registry_code,
            "source": self.source_name,
            "matched": v_status == VerificationStatus.VERIFIED,
            "name_match": name_match,
            "claimed_establishment_name": claimed_name,
            "establishment_name": registry_name,
            "registry_establishment_name": registry_name,
            "registration_status": registry_status,
            "office_name": office_name,
            "state": state,
            "reason": reason_msg,
        }

        return VerificationResult(
            verification_type=VerificationType.EPFO,
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
