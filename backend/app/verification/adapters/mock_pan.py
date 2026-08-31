"""
Mock PAN Verification Adapter for Part 5B
Provides deterministic PAN and entity holder verification against synthetic test fixtures.
Extracts PAN taxpayer category signal from the 4th character and validates holder identity.
Does NOT invoke external Income Tax Department / NSDL APIs.
"""

import re
from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_PAN_REGISTRY
from app.verification.normalizers import (
    compare_names,
    extract_pan_entity_type,
    normalize_identifier,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)

# Standard Indian PAN Regex: 5 letters + 4 digits + 1 letter
PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')


class MockPANVerificationAdapter(VerificationAdapter):
    """
    Deterministic Mock PAN Verification Adapter for development and testing.
    """

    @property
    def source_name(self) -> str:
        return "Mock PAN Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.PAN

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if not claimed_value or not isinstance(claimed_value, str):
            return False, "PAN value must be a non-empty string."

        cleaned = normalize_identifier(claimed_value)
        if not PAN_PATTERN.match(cleaned):
            return False, f"Invalid PAN format '{cleaned}'. Must be 10 characters (5 uppercase letters, 4 digits, 1 uppercase letter)."

        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        if not request.claimed_value:
            return VerificationResult(
                verification_type=VerificationType.PAN,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "MISSING_VERIFICATION_VALUE"},
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="No PAN value was provided for verification.",
            )

        is_valid, validation_err = self.validate_input(request.claimed_value)
        if not is_valid:
            return VerificationResult(
                verification_type=VerificationType.PAN,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                evidence={
                    "field": "pan_number",
                    "claimed_value": request.claimed_value,
                    "validation_error": validation_err,
                    "matched": False,
                },
                error_code=VerificationErrorCode.VERIFICATION_INPUT_INVALID,
                error_message=validation_err,
            )

        pan = normalize_identifier(request.claimed_value)
        entity_signal = extract_pan_entity_type(pan)
        record = MOCK_PAN_REGISTRY.get(pan)

        # 1. Simulated Source Outage
        if record and record.get("status") == "UNAVAILABLE":
            return VerificationResult(
                verification_type=VerificationType.PAN,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=pan,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={
                    "field": "pan_number",
                    "claimed_value": pan,
                    "source": self.source_name,
                    "simulated_outage": True,
                    **entity_signal,
                },
                raw_response=record,
                error_code=record.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=record.get("error_message", "Mock PAN Registry is currently unavailable."),
            )

        # 2. Not Found in Mock Registry
        if not record:
            return VerificationResult(
                verification_type=VerificationType.PAN,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=pan,
                verified_value=None,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                match_summary={"identifier": VerificationMatchStatus.MISMATCH},
                evidence={
                    "field": "pan_number",
                    "claimed_value": pan,
                    "source": self.source_name,
                    "matched": False,
                    "details": "PAN not found in Mock PAN Registry records.",
                    **entity_signal,
                },
                raw_response={"found": False, "pan_number": pan},
                error_code=None,
                error_message="PAN was not found in Mock PAN Registry records.",
            )

        # 3. Found in Registry: Compare Primary and Supporting Claims
        claimed_name = (
            request.supporting_claims.get("name")
            or request.supporting_claims.get("holder_name")
            or request.supporting_claims.get("legal_name")
            or request.supporting_claims.get("entity_name")
            or request.extra_context.get("name")
        )

        registry_pan = record.get("pan_number", pan)
        registry_name = record.get("name") or record.get("entity_name", "")
        registry_status = record.get("pan_status", "ACTIVE")
        registry_category = record.get("pan_category", entity_signal.get("entity_type_description"))

        # Compare fields
        id_match = VerificationMatchStatus.MATCH
        name_match, name_confidence = compare_names(claimed_name, registry_name)

        match_summary: Dict[str, str] = {
            "identifier": id_match,
            "name": name_match,
            "pan_status": registry_status,
        }

        normalized_claim_payload: Dict[str, Any] = {
            "pan_number": pan,
            "name": claimed_name,
        }

        normalized_verified_payload: Dict[str, Any] = {
            "pan_number": registry_pan,
            "name": registry_name,
            "pan_status": registry_status,
            "pan_category": registry_category,
            "entity_type_code": entity_signal.get("entity_type_code"),
            "entity_type_description": entity_signal.get("entity_type_description"),
        }

        # Determine Verification Status and Confidence
        if claimed_name and name_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.60
            reason_msg = f"PAN '{pan}' found in registry, but holder name '{claimed_name}' differs from registry name '{registry_name}'."
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else VerificationMatchStatus.PARTIAL_MATCH
            confidence = 1.0 if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else 0.95
            reason_msg = f"PAN '{pan}' authenticated against Mock PAN Registry (Status: {registry_status})."

        evidence_payload: Dict[str, Any] = {
            "field": "pan_number",
            "claimed_value": pan,
            "verified_value": registry_pan,
            "source": self.source_name,
            "matched": v_status == VerificationStatus.VERIFIED,
            "name_match": name_match,
            "claimed_name": claimed_name,
            "name": registry_name,
            "entity_name": registry_name,
            "registry_name": registry_name,
            "pan_status": registry_status,
            "pan_category": registry_category,
            **entity_signal,
            "reason": reason_msg,
        }

        return VerificationResult(
            verification_type=VerificationType.PAN,
            verification_status=v_status,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=pan,
            verified_value=registry_pan,
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
