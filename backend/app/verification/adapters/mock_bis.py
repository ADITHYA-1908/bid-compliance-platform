"""
Mock BIS Verification Adapter for Part 5D
Provides deterministic Bureau of Indian Standards (BIS) CRS / License verification against synthetic fixtures.
Validates registration number (e.g. R-12345678), standard number (e.g. IS 13252), manufacturer name, and validity.
Does NOT invoke external e-BIS portal APIs.
"""

from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_BIS_REGISTRY
from app.verification.normalizers import (
    compare_names,
    compare_scope,
    compare_strings,
    normalize_bis_number,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)


class MockBISAdapter(VerificationAdapter):
    """
    Deterministic Mock BIS Registration/License Verification Adapter.
    """

    @property
    def source_name(self) -> str:
        return "Mock BIS Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.BIS

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if not claimed_value or not isinstance(claimed_value, str):
            return False, "BIS registration or license number must be a non-empty string."

        cleaned = normalize_bis_number(claimed_value)
        if len(cleaned) < 4:
            return False, f"Invalid BIS identifier format '{cleaned}'."

        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        if not request.claimed_value:
            return VerificationResult(
                verification_type=VerificationType.BIS,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "MISSING_VERIFICATION_VALUE"},
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="No BIS registration or license number was provided for verification.",
            )

        is_valid, validation_err = self.validate_input(request.claimed_value)
        if not is_valid:
            return VerificationResult(
                verification_type=VerificationType.BIS,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                evidence={
                    "field": "bis_registration_number",
                    "claimed_value": request.claimed_value,
                    "validation_error": validation_err,
                    "matched": False,
                },
                error_code=VerificationErrorCode.VERIFICATION_INPUT_INVALID,
                error_message=validation_err,
            )

        reg_number = normalize_bis_number(request.claimed_value)
        record = MOCK_BIS_REGISTRY.get(reg_number)

        # 1. Simulated Source Outage
        if record and record.get("status") == "UNAVAILABLE":
            return VerificationResult(
                verification_type=VerificationType.BIS,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=reg_number,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={
                    "field": "bis_registration_number",
                    "claimed_value": reg_number,
                    "source": self.source_name,
                    "simulated_outage": True,
                },
                raw_response=record,
                error_code=record.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=record.get("error_message", "Mock BIS Registry is currently unavailable."),
            )

        # 2. Not Found in Mock Registry
        if not record:
            return VerificationResult(
                verification_type=VerificationType.BIS,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=reg_number,
                verified_value=None,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                match_summary={"registration_number": VerificationMatchStatus.MISMATCH},
                evidence={
                    "field": "bis_registration_number",
                    "claimed_value": reg_number,
                    "source": self.source_name,
                    "matched": False,
                    "details": "BIS registration number not found in Mock BIS Registry records.",
                },
                raw_response={"found": False, "registration_number": reg_number},
                error_code=None,
                error_message="BIS registration number was not found in Mock BIS Registry records.",
            )

        # 3. Found in Registry: Compare Manufacturer Name, Standard, Product
        claimed_mfg = (
            request.supporting_claims.get("manufacturer_name")
            or request.supporting_claims.get("company_name")
            or request.supporting_claims.get("legal_name")
            or request.extra_context.get("bidder_name")
        )
        claimed_standard = request.supporting_claims.get("standard_number") or request.supporting_claims.get("standard")
        claimed_product = request.supporting_claims.get("product_name") or request.supporting_claims.get("model_number")

        registry_reg = record.get("registration_number") or record.get("bis_registration_number", reg_number)
        registry_mfg = record.get("manufacturer_name", "")
        registry_std = record.get("standard_number", "")
        registry_prod = record.get("product_name", "")
        registry_status = record.get("registry_status", "VALID")
        valid_from = record.get("valid_from")
        valid_until = record.get("valid_until")

        # Compare fields
        id_match = VerificationMatchStatus.MATCH
        mfg_match, _ = compare_names(claimed_mfg, registry_mfg)
        std_match, _ = compare_strings(claimed_standard, registry_std) if claimed_standard else (VerificationMatchStatus.NOT_APPLICABLE, 1.0)
        prod_match, _ = compare_scope(claimed_product, registry_prod) if claimed_product else (VerificationMatchStatus.NOT_APPLICABLE, 1.0)

        match_summary: Dict[str, str] = {
            "registration_number": id_match,
            "manufacturer_name": mfg_match,
            "standard_number": std_match,
            "product_name": prod_match,
            "registry_status": registry_status,
        }

        normalized_claim_payload: Dict[str, Any] = {
            "bis_registration_number": reg_number,
            "manufacturer_name": claimed_mfg,
            "standard_number": claimed_standard,
            "product_name": claimed_product,
        }

        normalized_verified_payload: Dict[str, Any] = {
            "bis_registration_number": registry_reg,
            "manufacturer_name": registry_mfg,
            "standard_number": registry_std,
            "product_name": registry_prod,
            "model_number": record.get("model_number"),
            "registry_status": registry_status,
            "valid_from": valid_from,
            "valid_until": valid_until,
        }

        # Determine Verification Status and Confidence
        if claimed_mfg and mfg_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.60
            reason_msg = f"BIS license '{reg_number}' found, but claimed manufacturer '{claimed_mfg}' differs from registry licensee '{registry_mfg}'."
        elif claimed_standard and std_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.65
            reason_msg = f"BIS license '{reg_number}' found, but claimed standard '{claimed_standard}' does not match registry standard '{registry_std}'."
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH if mfg_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else VerificationMatchStatus.PARTIAL_MATCH
            confidence = 1.0 if mfg_match in [VerificationMatchStatus.MATCH, VerificationMatchStatus.NOT_APPLICABLE] else 0.90
            reason_msg = f"BIS license '{reg_number}' authenticated against Mock BIS Registry (Standard: {registry_std}, Status: {registry_status})."

        evidence_payload: Dict[str, Any] = {
            "field": "bis_registration_number",
            "claimed_value": reg_number,
            "verified_value": registry_reg,
            "source": self.source_name,
            "matched": v_status == VerificationStatus.VERIFIED,
            "manufacturer_name_match": mfg_match,
            "standard_number_match": std_match,
            "claimed_manufacturer": claimed_mfg,
            "manufacturer_name": registry_mfg,
            "standard_number": registry_std,
            "product_name": registry_prod,
            "registry_status": registry_status,
            "registration_status": registry_status,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "reason": reason_msg,
        }

        return VerificationResult(
            verification_type=VerificationType.BIS,
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
