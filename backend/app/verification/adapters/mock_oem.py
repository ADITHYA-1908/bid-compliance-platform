"""
Mock OEM Authorization Verification Adapter for Part 5D
Provides deterministic OEM authorization claim verification against synthetic manufacturer fixtures.
Validates OEM name, authorized entity, reference number, product scope, and validity window.
Does NOT claim universal public government registry authority.
"""

from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_OEM_REGISTRY
from app.verification.normalizers import (
    compare_names,
    compare_scope,
    compare_strings,
    normalize_identifier,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)


class MockOEMAuthorizationAdapter(VerificationAdapter):
    """
    Deterministic Mock OEM Authorization Verification Adapter.
    """

    @property
    def source_name(self) -> str:
        return "Mock OEM Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.OEM_AUTHORIZATION

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if not claimed_value or not isinstance(claimed_value, str):
            return False, "OEM Authorization reference number or identifier must be a non-empty string."

        cleaned = str(claimed_value).strip()
        if len(cleaned) < 3:
            return False, f"Invalid OEM Authorization reference '{cleaned}'. Must be at least 3 characters."

        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        if not request.claimed_value:
            return VerificationResult(
                verification_type=VerificationType.OEM_AUTHORIZATION,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "MISSING_VERIFICATION_VALUE"},
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="No OEM Authorization reference number was provided for verification.",
            )

        is_valid, validation_err = self.validate_input(request.claimed_value)
        if not is_valid:
            return VerificationResult(
                verification_type=VerificationType.OEM_AUTHORIZATION,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                evidence={
                    "field": "reference_number",
                    "claimed_value": request.claimed_value,
                    "validation_error": validation_err,
                    "matched": False,
                },
                error_code=VerificationErrorCode.VERIFICATION_INPUT_INVALID,
                error_message=validation_err,
            )

        ref_number = normalize_identifier(request.claimed_value)
        record = MOCK_OEM_REGISTRY.get(ref_number)

        # 1. Simulated Source Outage
        if record and record.get("status") == "UNAVAILABLE":
            return VerificationResult(
                verification_type=VerificationType.OEM_AUTHORIZATION,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=ref_number,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={
                    "field": "reference_number",
                    "claimed_value": ref_number,
                    "source": self.source_name,
                    "simulated_outage": True,
                },
                raw_response=record,
                error_code=record.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=record.get("error_message", "Mock OEM Registry is currently unavailable."),
            )

        # 2. Not Found in Mock Registry
        if not record:
            return VerificationResult(
                verification_type=VerificationType.OEM_AUTHORIZATION,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=ref_number,
                verified_value=None,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                match_summary={"reference_number": VerificationMatchStatus.MISMATCH},
                evidence={
                    "field": "reference_number",
                    "claimed_value": ref_number,
                    "source": self.source_name,
                    "matched": False,
                    "details": "OEM authorization reference number not found in Mock OEM Registry records.",
                },
                raw_response={"found": False, "reference_number": ref_number},
                error_code=None,
                error_message="OEM authorization reference number was not found in Mock OEM Registry records.",
            )

        # 3. Found in Registry: Compare OEM Name, Authorized Bidder Entity, and Product Scope
        claimed_oem = request.supporting_claims.get("oem_name") or request.extra_context.get("oem_name")
        claimed_authorized_entity = (
            request.supporting_claims.get("authorized_entity")
            or request.supporting_claims.get("bidder_name")
            or request.supporting_claims.get("legal_name")
            or request.supporting_claims.get("company_name")
            or request.extra_context.get("bidder_name")
        )
        claimed_scope = (
            request.supporting_claims.get("product_scope")
            or request.supporting_claims.get("product_or_scope")
            or request.supporting_claims.get("product_name")
        )

        registry_ref = record.get("reference_number") or record.get("authorization_number", ref_number)
        registry_oem = record.get("oem_name", "")
        registry_auth_entity = record.get("authorized_entity", "")
        registry_scope = record.get("product_scope", "")
        registry_status = record.get("authorization_status", "VALID")
        valid_from = record.get("valid_from")
        valid_until = record.get("valid_until")

        # Compare fields
        id_match = VerificationMatchStatus.MATCH
        oem_match, oem_conf = compare_names(claimed_oem, registry_oem)
        entity_match, entity_conf = compare_names(claimed_authorized_entity, registry_auth_entity)
        scope_match, scope_conf = compare_scope(claimed_scope, registry_scope)

        match_summary: Dict[str, str] = {
            "reference_number": id_match,
            "oem_name": oem_match,
            "authorized_entity": entity_match,
            "product_scope": scope_match,
            "authorization_status": registry_status,
        }

        normalized_claim_payload: Dict[str, Any] = {
            "reference_number": ref_number,
            "oem_name": claimed_oem,
            "authorized_entity": claimed_authorized_entity,
            "product_scope": claimed_scope,
        }

        normalized_verified_payload: Dict[str, Any] = {
            "reference_number": registry_ref,
            "oem_name": registry_oem,
            "authorized_entity": registry_auth_entity,
            "product_scope": registry_scope,
            "authorization_status": registry_status,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "signatory_name": record.get("signatory_name"),
        }

        # Determine Verification Status and Confidence
        if claimed_authorized_entity and entity_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.60
            reason_msg = f"OEM Authorization '{ref_number}' found, but authorized entity '{claimed_authorized_entity}' differs from registry grantee '{registry_auth_entity}'."
        elif claimed_scope and scope_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.65
            reason_msg = f"OEM Authorization '{ref_number}' found, but claimed product scope does not match authorized scope in registry."
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH if entity_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else VerificationMatchStatus.PARTIAL_MATCH
            confidence = 1.0 if entity_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else 0.90
            reason_msg = f"OEM Authorization '{ref_number}' authenticated against Mock OEM Registry (Status: {registry_status})."

        evidence_payload: Dict[str, Any] = {
            "field": "reference_number",
            "claimed_value": ref_number,
            "verified_value": registry_ref,
            "source": self.source_name,
            "matched": v_status == VerificationStatus.VERIFIED,
            "oem_name_match": oem_match,
            "authorized_entity_match": entity_match,
            "scope_match": scope_match,
            "claimed_oem": claimed_oem,
            "oem_name": registry_oem,
            "authorized_entity": registry_auth_entity,
            "product_scope": registry_scope,
            "authorization_status": registry_status,
            "registration_status": registry_status,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "reason": reason_msg,
        }

        return VerificationResult(
            verification_type=VerificationType.OEM_AUTHORIZATION,
            verification_status=v_status,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=ref_number,
            verified_value=registry_ref,
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
