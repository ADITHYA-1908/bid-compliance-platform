"""
Mock MCA Verification Adapter for Part 5C
Provides deterministic Corporate Identification Number (CIN) and LLPIN verification
against synthetic Ministry of Corporate Affairs test fixtures.
Validates company/LLP identity and preserves corporate status (ACTIVE, DORMANT, etc.).
Does NOT invoke external MCA V3 portal APIs.
"""

import re
from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_MCA_REGISTRY
from app.verification.normalizers import (
    compare_names,
    compare_strings,
    extract_cin_metadata,
    normalize_cin,
    normalize_llpin,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)

# Standard Indian CIN Pattern: [LU] + 5 digits + 2 letters + 4 digits + 3 letters + 6 digits (21 chars)
CIN_PATTERN = re.compile(r'^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$')
# Standard Indian LLPIN Pattern: e.g. AAA-1234 or AAB-1234
LLPIN_PATTERN = re.compile(r'^[A-Z]{3}-[0-9]{4}$')


class MockMCAVerificationAdapter(VerificationAdapter):
    """
    Deterministic Mock MCA Verification Adapter for development and testing.
    """

    @property
    def source_name(self) -> str:
        return "Mock MCA Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.MCA

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if not claimed_value or not isinstance(claimed_value, str):
            return False, "CIN or LLPIN must be a non-empty string."

        cleaned = str(claimed_value).strip().upper()
        if CIN_PATTERN.match(cleaned):
            return True, None
        if LLPIN_PATTERN.match(cleaned):
            return True, None

        return False, f"Invalid CIN/LLPIN format '{cleaned}'. Must be 21-character CIN (e.g. U72900TN2018PTC123456) or valid LLPIN (e.g. AAA-1234)."

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        if not request.claimed_value:
            return VerificationResult(
                verification_type=VerificationType.MCA,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "MISSING_VERIFICATION_VALUE"},
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="No CIN or LLPIN was provided for MCA verification.",
            )

        is_valid, validation_err = self.validate_input(request.claimed_value)
        if not is_valid:
            return VerificationResult(
                verification_type=VerificationType.MCA,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                evidence={
                    "field": "cin",
                    "claimed_value": request.claimed_value,
                    "validation_error": validation_err,
                    "matched": False,
                },
                error_code=VerificationErrorCode.VERIFICATION_INPUT_INVALID,
                error_message=validation_err,
            )

        identifier = str(request.claimed_value).strip().upper()
        cin_signal = extract_cin_metadata(identifier)
        record = MOCK_MCA_REGISTRY.get(identifier)

        # 1. Simulated Source Outage
        if record and record.get("status") == "UNAVAILABLE":
            return VerificationResult(
                verification_type=VerificationType.MCA,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=identifier,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={
                    "field": "cin",
                    "claimed_value": identifier,
                    "source": self.source_name,
                    "simulated_outage": True,
                },
                raw_response=record,
                error_code=record.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=record.get("error_message", "Mock MCA Registry is currently unavailable."),
            )

        # 2. Not Found in Mock Registry
        if not record:
            return VerificationResult(
                verification_type=VerificationType.MCA,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=identifier,
                verified_value=None,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                match_summary={"identifier": VerificationMatchStatus.MISMATCH},
                evidence={
                    "field": "cin",
                    "claimed_value": identifier,
                    "source": self.source_name,
                    "matched": False,
                    "details": "CIN/LLPIN not found in Mock MCA Registry records.",
                },
                raw_response={"found": False, "identifier": identifier},
                error_code=None,
                error_message="CIN or LLPIN was not found in Mock MCA Registry records.",
            )

        # 3. Found in Registry: Compare Primary and Supporting Claims
        claimed_name = (
            request.supporting_claims.get("company_name")
            or request.supporting_claims.get("legal_name")
            or request.supporting_claims.get("entity_name")
            or request.extra_context.get("company_name")
        )
        claimed_state = request.supporting_claims.get("state") or request.supporting_claims.get("registered_office_state")

        registry_id = record.get("cin") or record.get("llpin", identifier)
        registry_name = record.get("company_name", "")
        registry_status = record.get("company_status", "ACTIVE")
        registry_type = record.get("company_type", cin_signal.get("company_type", "Company"))
        registry_inc_date = record.get("date_of_incorporation")
        registry_state = record.get("registered_office_state", "")

        # Compare fields
        id_match = VerificationMatchStatus.MATCH
        name_match, name_confidence = compare_names(claimed_name, registry_name)
        state_match, _ = compare_strings(claimed_state, registry_state) if claimed_state else (VerificationMatchStatus.NOT_APPLICABLE, 1.0)

        match_summary: Dict[str, str] = {
            "identifier": id_match,
            "company_name": name_match,
            "state": state_match,
            "company_status": registry_status,
        }

        normalized_claim_payload: Dict[str, Any] = {
            "cin": identifier,
            "company_name": claimed_name,
            "state": claimed_state,
        }

        normalized_verified_payload: Dict[str, Any] = {
            "cin": registry_id,
            "company_name": registry_name,
            "company_status": registry_status,
            "company_type": registry_type,
            "date_of_incorporation": registry_inc_date,
            "registered_office_state": registry_state,
            "registered_office_address": record.get("registered_office_address"),
            "roc": record.get("roc"),
            "listing_status": cin_signal.get("listing_status"),
        }

        # Determine Verification Status and Confidence
        if claimed_name and name_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.60
            reason_msg = f"CIN/LLPIN '{identifier}' found in registry, but claimed company name '{claimed_name}' differs from registry name '{registry_name}'."
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else VerificationMatchStatus.PARTIAL_MATCH
            confidence = 1.0 if name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else 0.95
            reason_msg = f"CIN/LLPIN '{identifier}' authenticated against Mock MCA Registry (Status: {registry_status})."

        evidence_payload: Dict[str, Any] = {
            "field": "cin",
            "claimed_value": identifier,
            "verified_value": registry_id,
            "source": self.source_name,
            "matched": v_status == VerificationStatus.VERIFIED,
            "name_match": name_match,
            "claimed_company_name": claimed_name,
            "company_name": registry_name,
            "registry_company_name": registry_name,
            "company_status": registry_status,
            "registration_status": registry_status,
            "company_type": registry_type,
            "date_of_incorporation": registry_inc_date,
            "registered_office_state": registry_state,
            "listing_status": cin_signal.get("listing_status"),
            "reason": reason_msg,
        }

        return VerificationResult(
            verification_type=VerificationType.MCA,
            verification_status=v_status,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=identifier,
            verified_value=registry_id,
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
