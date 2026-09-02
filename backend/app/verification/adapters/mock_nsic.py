"""
Mock NSIC Verification Adapter for Part 5C
Provides deterministic NSIC Single Point Registration Scheme claim verification against synthetic fixtures.
Validates enterprise identity and preserves validity dates (valid_from, valid_until) and registration category.
Does NOT invoke external NSIC portal APIs.
"""

import re
from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_NSIC_REGISTRY
from app.verification.normalizers import (
    compare_names,
    compare_strings,
    normalize_nsic_number,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)

# Standard NSIC registration number regex pattern
NSIC_PATTERN = re.compile(r'^NSIC[\-_/0-9A-Z]+$', re.IGNORECASE)


class MockNSICVerificationAdapter(VerificationAdapter):
    """
    Deterministic Mock NSIC Verification Adapter.
    """

    @property
    def source_name(self) -> str:
        return "Mock NSIC Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.NSIC

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if not claimed_value or not isinstance(claimed_value, str):
            return False, "NSIC registration number must be a non-empty string."

        cleaned = normalize_nsic_number(claimed_value)
        if not NSIC_PATTERN.match(cleaned) and len(cleaned) < 5:
            return False, f"Invalid NSIC registration number format '{cleaned}'. Must be a valid NSIC identifier."

        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        if not request.claimed_value:
            return VerificationResult(
                verification_type=VerificationType.NSIC,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "MISSING_VERIFICATION_VALUE"},
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="No NSIC registration number was provided for verification.",
            )

        is_valid, validation_err = self.validate_input(request.claimed_value)
        if not is_valid:
            return VerificationResult(
                verification_type=VerificationType.NSIC,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                evidence={
                    "field": "nsic_registration_number",
                    "claimed_value": request.claimed_value,
                    "validation_error": validation_err,
                    "matched": False,
                },
                error_code=VerificationErrorCode.VERIFICATION_INPUT_INVALID,
                error_message=validation_err,
            )

        reg_number = normalize_nsic_number(request.claimed_value)
        record = MOCK_NSIC_REGISTRY.get(reg_number)

        # 1. Simulated Source Outage
        if record and record.get("status") == "UNAVAILABLE":
            return VerificationResult(
                verification_type=VerificationType.NSIC,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=reg_number,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={
                    "field": "nsic_registration_number",
                    "claimed_value": reg_number,
                    "source": self.source_name,
                    "simulated_outage": True,
                },
                raw_response=record,
                error_code=record.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=record.get("error_message", "Mock NSIC Registry is currently unavailable."),
            )

        # 2. Not Found in Mock Registry
        if not record:
            return VerificationResult(
                verification_type=VerificationType.NSIC,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=reg_number,
                verified_value=None,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                match_summary={"identifier": VerificationMatchStatus.MISMATCH},
                evidence={
                    "field": "nsic_registration_number",
                    "claimed_value": reg_number,
                    "source": self.source_name,
                    "matched": False,
                    "details": "NSIC registration number not found in Mock NSIC Registry records.",
                },
                raw_response={"found": False, "registration_number": reg_number},
                error_code=None,
                error_message="NSIC registration number was not found in Mock NSIC Registry records.",
            )

        # 3. Found in Registry: Compare Primary and Supporting Claims
        claimed_name = (
            request.supporting_claims.get("enterprise_name")
            or request.supporting_claims.get("company_name")
            or request.supporting_claims.get("legal_name")
            or request.extra_context.get("enterprise_name")
        )

        registry_reg = record.get("registration_number") or record.get("nsic_registration_number", reg_number)
        registry_name = record.get("enterprise_name", "")
        registry_status = record.get("registration_status", "VALID")
        valid_from = record.get("valid_from")
        valid_until = record.get("valid_until")
        category = record.get("category", "")
        products_services = record.get("products_services", "")

        # Compare fields
        id_match = VerificationMatchStatus.MATCH
        name_match, name_confidence = compare_names(claimed_name, registry_name)

        match_summary: Dict[str, str] = {
            "identifier": id_match,
            "enterprise_name": name_match,
            "registration_status": registry_status,
        }

        normalized_claim_payload: Dict[str, Any] = {
            "nsic_registration_number": reg_number,
            "enterprise_name": claimed_name,
        }

        normalized_verified_payload: Dict[str, Any] = {
            "nsic_registration_number": registry_reg,
            "enterprise_name": registry_name,
            "registration_status": registry_status,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "category": category,
            "products_services": products_services,
            "state": record.get("state"),
        }

        # Determine Verification Status and Confidence
        if claimed_name and name_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.60
            reason_msg = f"NSIC registration '{reg_number}' found, but claimed enterprise name '{claimed_name}' differs from registry name '{registry_name}'."
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else VerificationMatchStatus.PARTIAL_MATCH
            confidence = 1.0 if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else 0.95
            reason_msg = f"NSIC registration '{reg_number}' authenticated against Mock NSIC Registry (Status: {registry_status}, Valid Until: {valid_until})."

        evidence_payload: Dict[str, Any] = {
            "field": "nsic_registration_number",
            "claimed_value": reg_number,
            "verified_value": registry_reg,
            "source": self.source_name,
            "matched": v_status == VerificationStatus.VERIFIED,
            "name_match": name_match,
            "claimed_enterprise_name": claimed_name,
            "enterprise_name": registry_name,
            "registry_enterprise_name": registry_name,
            "registration_status": registry_status,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "category": category,
            "products_services": products_services,
            "reason": reason_msg,
        }

        return VerificationResult(
            verification_type=VerificationType.NSIC,
            verification_status=v_status,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=reg_number,
            verified_value=registry_reg,
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
