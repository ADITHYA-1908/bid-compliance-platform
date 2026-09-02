"""
Mock Udyam Verification Adapter for Part 5B
Provides deterministic MSME Udyam registration and enterprise verification against synthetic fixtures.
Validates enterprise identity and preserves MSME classification metadata (Micro, Small, Medium).
Does NOT invoke external Ministry of MSME / Udyam portal APIs.
"""

import re
from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_UDYAM_REGISTRY
from app.verification.normalizers import (
    compare_names,
    compare_strings,
    normalize_identifier,
    normalize_udyam_number,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)

# Standard Indian Udyam Number Regex: UDYAM-StateCode(2)-DistrictCode(2)-Number(7 digits)
UDYAM_PATTERN = re.compile(r'^UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}$')


class MockUdyamVerificationAdapter(VerificationAdapter):
    """
    Deterministic Mock Udyam MSME Verification Adapter for development and testing.
    """

    @property
    def source_name(self) -> str:
        return "Mock MSME Udyam Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.UDYAM

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if not claimed_value or not isinstance(claimed_value, str):
            return False, "Udyam Registration Number must be a non-empty string."

        cleaned = normalize_udyam_number(claimed_value)
        if not UDYAM_PATTERN.match(cleaned):
            return False, f"Invalid Udyam number format '{cleaned}'. Must follow standard format 'UDYAM-XX-00-0000000'."

        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        if not request.claimed_value:
            return VerificationResult(
                verification_type=VerificationType.UDYAM,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "MISSING_VERIFICATION_VALUE"},
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="No Udyam Registration Number was provided for verification.",
            )

        is_valid, validation_err = self.validate_input(request.claimed_value)
        if not is_valid:
            return VerificationResult(
                verification_type=VerificationType.UDYAM,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                evidence={
                    "field": "udyam_registration_number",
                    "claimed_value": request.claimed_value,
                    "validation_error": validation_err,
                    "matched": False,
                },
                error_code=VerificationErrorCode.VERIFICATION_INPUT_INVALID,
                error_message=validation_err,
            )

        udyam_no = normalize_udyam_number(request.claimed_value)
        record = MOCK_UDYAM_REGISTRY.get(udyam_no)

        # 1. Simulated Source Outage
        if record and record.get("status") == "UNAVAILABLE":
            return VerificationResult(
                verification_type=VerificationType.UDYAM,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=udyam_no,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={
                    "field": "udyam_registration_number",
                    "claimed_value": udyam_no,
                    "source": self.source_name,
                    "simulated_outage": True,
                },
                raw_response=record,
                error_code=record.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=record.get("error_message", "Mock MSME Udyam Registry is currently unavailable."),
            )

        # 2. Not Found in Mock Registry
        if not record:
            return VerificationResult(
                verification_type=VerificationType.UDYAM,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=udyam_no,
                verified_value=None,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                match_summary={"identifier": VerificationMatchStatus.MISMATCH},
                evidence={
                    "field": "udyam_registration_number",
                    "claimed_value": udyam_no,
                    "source": self.source_name,
                    "matched": False,
                    "details": "Udyam registration number not found in Mock Udyam Registry records.",
                },
                raw_response={"found": False, "udyam_registration_number": udyam_no},
                error_code=None,
                error_message="Udyam registration number was not found in Mock Udyam Registry records.",
            )

        # 3. Found in Registry: Compare Primary and Supporting Claims
        claimed_enterprise_name = (
            request.supporting_claims.get("enterprise_name")
            or request.supporting_claims.get("legal_name")
            or request.supporting_claims.get("company_name")
            or request.extra_context.get("enterprise_name")
        )
        claimed_org_type = request.supporting_claims.get("organization_type")
        claimed_major_activity = request.supporting_claims.get("major_activity")

        registry_udyam = record.get("udyam_registration_number") or record.get("udyam_number", udyam_no)
        registry_enterprise_name = record.get("enterprise_name", "")
        registry_classification = record.get("enterprise_classification") or record.get("enterprise_type", "Micro")
        registry_activity = record.get("major_activity", "Services")
        registry_org_type = record.get("organization_type", "Private Limited Company")
        registry_date = record.get("registration_date") or record.get("udyam_registration_date")
        is_active = record.get("is_active", True)
        registry_status = "ACTIVE" if is_active else "CANCELLED"

        # Compare fields
        id_match = VerificationMatchStatus.MATCH
        name_match, name_confidence = compare_names(claimed_enterprise_name, registry_enterprise_name)
        org_type_match, _ = compare_strings(claimed_org_type, registry_org_type) if claimed_org_type else (VerificationMatchStatus.NOT_APPLICABLE, 1.0)
        activity_match, _ = compare_strings(claimed_major_activity, registry_activity) if claimed_major_activity else (VerificationMatchStatus.NOT_APPLICABLE, 1.0)

        match_summary: Dict[str, str] = {
            "identifier": id_match,
            "enterprise_name": name_match,
            "organization_type": org_type_match,
            "major_activity": activity_match,
            "enterprise_classification": registry_classification,
            "registration_status": registry_status,
        }

        normalized_claim_payload: Dict[str, Any] = {
            "udyam_registration_number": udyam_no,
            "enterprise_name": claimed_enterprise_name,
            "organization_type": claimed_org_type,
            "major_activity": claimed_major_activity,
        }

        normalized_verified_payload: Dict[str, Any] = {
            "udyam_registration_number": registry_udyam,
            "enterprise_name": registry_enterprise_name,
            "enterprise_classification": registry_classification,
            "major_activity": registry_activity,
            "organization_type": registry_org_type,
            "registration_date": registry_date,
            "registration_status": registry_status,
            "is_active": is_active,
        }

        # Determine Verification Status and Confidence
        if claimed_enterprise_name and name_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.60
            reason_msg = f"Udyam registration '{udyam_no}' found in registry, but enterprise name '{claimed_enterprise_name}' differs from registry name '{registry_enterprise_name}'."
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else VerificationMatchStatus.PARTIAL_MATCH
            confidence = 1.0 if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else 0.95
            reason_msg = f"Udyam registration '{udyam_no}' authenticated against Mock MSME Registry (Classification: {registry_classification}, Status: {registry_status})."

        evidence_payload: Dict[str, Any] = {
            "field": "udyam_registration_number",
            "claimed_value": udyam_no,
            "verified_value": registry_udyam,
            "source": self.source_name,
            "matched": v_status == VerificationStatus.VERIFIED,
            "name_match": name_match,
            "claimed_enterprise_name": claimed_enterprise_name,
            "enterprise_name": registry_enterprise_name,
            "registry_enterprise_name": registry_enterprise_name,
            "enterprise_type": registry_classification,
            "enterprise_classification": registry_classification,
            "major_activity": registry_activity,
            "organization_type": registry_org_type,
            "registration_date": registry_date,
            "registration_status": registry_status,
            "reason": reason_msg,
        }

        return VerificationResult(
            verification_type=VerificationType.UDYAM,
            verification_status=v_status,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=udyam_no,
            verified_value=registry_udyam,
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
