"""
Mock DPIIT Public Procurement Policy Verification Adapter for Part 5D
Provides deterministic verification for DPIIT Make-in-India (MII) preference orders.
Avoids duplication with Part 5C (which handles Startup India recognition).
"""

from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_DPIIT_REGISTRY
from app.verification.normalizers import (
    compare_names,
    normalize_identifier,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)


class MockDPIITAdapter(VerificationAdapter):
    """
    Deterministic Mock DPIIT MII Public Procurement Preference Verification Adapter.
    """

    @property
    def source_name(self) -> str:
        return "Mock DPIIT Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.DPIIT

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if not claimed_value or not isinstance(claimed_value, str):
            return False, "DPIIT recognition or reference number must be a non-empty string."

        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        if not request.claimed_value:
            return VerificationResult(
                verification_type=VerificationType.DPIIT,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "MISSING_VERIFICATION_VALUE"},
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="No DPIIT reference number was provided for verification.",
            )

        ref_number = normalize_identifier(request.claimed_value)
        record = MOCK_DPIIT_REGISTRY.get(ref_number)

        # 1. Simulated Source Outage
        if record and record.get("status") == "UNAVAILABLE":
            return VerificationResult(
                verification_type=VerificationType.DPIIT,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=ref_number,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"field": "dpiit_number", "claimed_value": ref_number, "simulated_outage": True},
                raw_response=record,
                error_code=record.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=record.get("error_message", "Mock DPIIT Gateway is temporarily unavailable."),
            )

        # 2. Not Found
        if not record:
            return VerificationResult(
                verification_type=VerificationType.DPIIT,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=ref_number,
                verified_value=None,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                evidence={"field": "dpiit_number", "claimed_value": ref_number, "matched": False},
                raw_response={"found": False},
                error_message="DPIIT MII reference number was not found in Mock Registry.",
            )

        # 3. Found
        claimed_entity = (
            request.supporting_claims.get("entity_name")
            or request.supporting_claims.get("company_name")
            or request.supporting_claims.get("legal_name")
            or request.extra_context.get("bidder_name")
        )
        registry_entity = record.get("entity_name", "")
        registry_status = record.get("status", "VALID")

        entity_match, _ = compare_names(claimed_entity, registry_entity)

        if claimed_entity and entity_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.60
            reason_msg = f"DPIIT record '{ref_number}' found, but claimed entity '{claimed_entity}' differs from registry record '{registry_entity}'."
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH if entity_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else VerificationMatchStatus.PARTIAL_MATCH
            confidence = 1.0 if entity_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else 0.90
            reason_msg = f"DPIIT MII record '{ref_number}' verified against Mock DPIIT Registry (Status: {registry_status})."

        evidence_payload: Dict[str, Any] = {
            "field": "dpiit_number",
            "claimed_value": ref_number,
            "verified_value": record.get("recognition_number", ref_number),
            "source": self.source_name,
            "matched": v_status == VerificationStatus.VERIFIED,
            "entity_name": registry_entity,
            "recognition_type": record.get("recognition_type"),
            "registration_status": registry_status,
            "reason": reason_msg,
        }

        return VerificationResult(
            verification_type=VerificationType.DPIIT,
            verification_status=v_status,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=ref_number,
            verified_value=record.get("recognition_number", ref_number),
            match_status=overall_match,
            confidence=confidence,
            match_summary={"dpiit_number": VerificationMatchStatus.MATCH, "entity_name": entity_match},
            evidence=evidence_payload,
            normalized_claim_payload={"dpiit_number": ref_number, "entity_name": claimed_entity},
            normalized_verified_payload={"dpiit_number": record.get("recognition_number"), "entity_name": registry_entity, "status": registry_status},
            raw_response=record,
            error_code=None,
            error_message=reason_msg if v_status == VerificationStatus.NEEDS_REVIEW else None,
        )
