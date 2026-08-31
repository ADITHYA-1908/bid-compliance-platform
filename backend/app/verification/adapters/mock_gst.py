"""
Mock GST Verification Adapter for Part 5B
Provides deterministic GSTIN and taxpayer profile verification against synthetic test fixtures.
Performs primary claim validation (GSTIN) and supporting claim comparison (legal name, trade name, state).
Does NOT invoke external GSTN / ClearTax APIs.
"""

import re
from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_GST_REGISTRY
from app.verification.normalizers import (
    compare_names,
    compare_strings,
    normalize_identifier,
    normalize_org_name,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)

# Standard Indian GSTIN Regex: 2 digit state code + 10 char PAN + 1 entity num + 'Z' + 1 checksum char
GSTIN_PATTERN = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')


class MockGSTVerificationAdapter(VerificationAdapter):
    """
    Deterministic Mock GST Verification Adapter for development, testing, and sandbox validation.
    """

    @property
    def source_name(self) -> str:
        return "Mock GST Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.GST

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if not claimed_value or not isinstance(claimed_value, str):
            return False, "GSTIN value must be a non-empty string."

        cleaned = normalize_identifier(claimed_value)
        if not GSTIN_PATTERN.match(cleaned):
            return False, f"Invalid GSTIN format '{cleaned}'. Must be 15 alphanumeric characters matching Indian GSTIN standard."

        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        if not request.claimed_value:
            return VerificationResult(
                verification_type=VerificationType.GST,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "MISSING_VERIFICATION_VALUE"},
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="No GSTIN value was provided for verification.",
            )

        is_valid, validation_err = self.validate_input(request.claimed_value)
        if not is_valid:
            return VerificationResult(
                verification_type=VerificationType.GST,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                evidence={
                    "field": "gstin",
                    "claimed_value": request.claimed_value,
                    "validation_error": validation_err,
                    "matched": False,
                },
                error_code=VerificationErrorCode.VERIFICATION_INPUT_INVALID,
                error_message=validation_err,
            )

        gstin = normalize_identifier(request.claimed_value)
        record = MOCK_GST_REGISTRY.get(gstin)

        # 1. Simulated Source Outage
        if record and record.get("status") == "UNAVAILABLE":
            return VerificationResult(
                verification_type=VerificationType.GST,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=gstin,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={
                    "field": "gstin",
                    "claimed_value": gstin,
                    "source": self.source_name,
                    "simulated_outage": True,
                },
                raw_response=record,
                error_code=record.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=record.get("error_message", "Mock GST Registry is currently unavailable."),
            )

        # 2. Not Found in Mock Registry
        if not record:
            return VerificationResult(
                verification_type=VerificationType.GST,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=gstin,
                verified_value=None,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                match_summary={"identifier": VerificationMatchStatus.MISMATCH},
                evidence={
                    "field": "gstin",
                    "claimed_value": gstin,
                    "source": self.source_name,
                    "matched": False,
                    "details": "GSTIN not found in Mock GST Registry records.",
                },
                raw_response={"found": False, "gstin": gstin},
                error_code=None,
                error_message="GSTIN was not found in Mock GST Registry records.",
            )

        # 3. Found in Registry: Compare Primary and Supporting Claims
        claimed_legal_name = (
            request.supporting_claims.get("legal_name")
            or request.supporting_claims.get("company_name")
            or request.extra_context.get("legal_name")
        )
        claimed_trade_name = request.supporting_claims.get("trade_name") or request.extra_context.get("trade_name")
        claimed_state = request.supporting_claims.get("state")

        registry_gstin = record.get("gstin", gstin)
        registry_legal_name = record.get("legal_name", "")
        registry_trade_name = record.get("trade_name", "")
        registry_state = record.get("state") or record.get("state_name", "")
        registry_status = record.get("gst_status", "ACTIVE")
        registry_date = record.get("registration_date")

        # Compare fields
        id_match = VerificationMatchStatus.MATCH
        legal_name_match, name_confidence = compare_names(claimed_legal_name, registry_legal_name)
        trade_name_match, _ = compare_names(claimed_trade_name, registry_trade_name) if claimed_trade_name else (VerificationMatchStatus.NOT_APPLICABLE, 1.0)
        state_match, _ = compare_strings(claimed_state, registry_state) if claimed_state else (VerificationMatchStatus.NOT_APPLICABLE, 1.0)

        match_summary: Dict[str, str] = {
            "identifier": id_match,
            "legal_name": legal_name_match,
            "trade_name": trade_name_match,
            "state": state_match,
            "registration_status": registry_status,
        }

        normalized_claim_payload: Dict[str, Any] = {
            "gstin": gstin,
            "legal_name": claimed_legal_name,
            "trade_name": claimed_trade_name,
            "state": claimed_state,
        }

        normalized_verified_payload: Dict[str, Any] = {
            "gstin": registry_gstin,
            "legal_name": registry_legal_name,
            "trade_name": registry_trade_name,
            "state": registry_state,
            "registration_status": registry_status,
            "registration_date": registry_date,
            "taxpayer_type": record.get("taxpayer_type", "Regular"),
        }

        # Determine Verification Status and Confidence
        # Case A: Name Mismatch (when a distinct legal name was claimed but differs from registry)
        if claimed_legal_name and legal_name_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.60
            reason_msg = f"GSTIN '{gstin}' found in registry, but claimed legal name '{claimed_legal_name}' does not match registry name '{registry_legal_name}'."
        # Case B: Verified (Exact or Partial Name Match, or Name not claimed in document)
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH if legal_name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else VerificationMatchStatus.PARTIAL_MATCH
            confidence = 1.0 if legal_name_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else 0.95
            reason_msg = f"GSTIN '{gstin}' authenticated against Mock GST Registry (Status: {registry_status})."

        evidence_payload: Dict[str, Any] = {
            "field": "gstin",
            "claimed_value": gstin,
            "verified_value": registry_gstin,
            "source": self.source_name,
            "matched": v_status == VerificationStatus.VERIFIED,
            "legal_name": registry_legal_name,
            "legal_name_match": legal_name_match,
            "claimed_legal_name": claimed_legal_name,
            "registry_legal_name": registry_legal_name,
            "trade_name": registry_trade_name,
            "trade_name_match": trade_name_match,
            "claimed_trade_name": claimed_trade_name,
            "registry_trade_name": registry_trade_name,
            "state_match": state_match,
            "registry_state": registry_state,
            "registration_status": registry_status,
            "registration_date": registry_date,
            "taxpayer_type": record.get("taxpayer_type", "Regular"),
            "reason": reason_msg,
        }

        return VerificationResult(
            verification_type=VerificationType.GST,
            verification_status=v_status,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=gstin,
            verified_value=registry_gstin,
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
