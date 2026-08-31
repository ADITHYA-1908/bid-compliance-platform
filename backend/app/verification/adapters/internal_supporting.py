"""
Internal Supporting Document Evidence Validation Adapter for Part 5D
Provides deterministic internal structural evidence verification for documents without external public registries
(e.g., CA Turnover Certificates, Financial Statements, Experience Letters, Manufacturer Undertakings).
Evaluates issuer identity, reference number, document date, signatory, and scope coherence.
Source Type: INTERNAL.
"""

from typing import Any, Dict, List, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)


class InternalSupportingDocumentAdapter(VerificationAdapter):
    """
    Deterministic Internal Evidence Validator for Supporting Bid Documents.
    """

    @property
    def source_name(self) -> str:
        return "Internal Evidence Validator"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.INTERNAL

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.SUPPORTING_DOCUMENT

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        # Supporting documents may have reference numbers or free-text claims
        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        supp = request.supporting_claims or {}

        # Extract structural evidence checklist
        has_reference = bool(request.claimed_value or supp.get("reference_number") or supp.get("udin") or supp.get("certificate_number"))
        has_issuer = bool(supp.get("ca_name") or supp.get("issuer_name") or supp.get("authority_name") or supp.get("certifying_authority") or supp.get("organization_name") or supp.get("company_name"))
        has_date = bool(supp.get("issue_date") or supp.get("date") or supp.get("declaration_date") or supp.get("period_from") or supp.get("valid_from"))
        has_signatory = bool(supp.get("signatory_name") or supp.get("authorized_signatory") or supp.get("partner_name") or supp.get("auditor_name"))
        has_financial_or_scope = bool(supp.get("turnover") or supp.get("net_worth") or supp.get("experience_years") or supp.get("scope_of_work") or supp.get("product_name"))

        checklist = {
            "reference_number_present": has_reference,
            "issuer_identified": has_issuer,
            "document_date_present": has_date,
            "signatory_present": has_signatory,
            "substantive_data_present": has_financial_or_scope,
        }

        score = sum(1 for v in checklist.values() if v)
        total_checks = len(checklist)

        ref_val = request.claimed_value or supp.get("reference_number") or supp.get("udin") or "INTERNAL-DOC-EVIDENCE"

        if score >= 3:
            v_status = VerificationStatus.VERIFIED
            match_status = VerificationMatchStatus.MATCH
            confidence = min(1.0, 0.70 + (score / total_checks) * 0.30)
            reason = f"Supporting document structural evidence satisfied ({score}/{total_checks} internal checks confirmed)."
        elif score >= 1:
            v_status = VerificationStatus.NEEDS_REVIEW
            match_status = VerificationMatchStatus.PARTIAL_MATCH
            confidence = 0.60
            reason = f"Supporting document contains partial evidence ({score}/{total_checks} internal checks confirmed). Manual officer review recommended."
        else:
            v_status = VerificationStatus.NEEDS_REVIEW
            match_status = VerificationMatchStatus.MISMATCH
            confidence = 0.40
            reason = "Supporting document missing key structural fields (reference number, issuer, date, or signatory)."

        evidence_payload: Dict[str, Any] = {
            "field": "supporting_evidence",
            "claimed_value": ref_val,
            "verified_value": "INTERNAL_EVIDENCE_VALIDATED" if v_status == VerificationStatus.VERIFIED else "PARTIAL_EVIDENCE",
            "source": self.source_name,
            "source_type": self.source_type,
            "matched": v_status == VerificationStatus.VERIFIED,
            "checklist": checklist,
            "score": f"{score}/{total_checks}",
            "reason": reason,
            "is_internal_check": True,
        }

        return VerificationResult(
            verification_type=VerificationType.SUPPORTING_DOCUMENT,
            verification_status=v_status,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=ref_val,
            verified_value="INTERNAL_EVIDENCE_VALIDATED" if v_status == VerificationStatus.VERIFIED else "PARTIAL_EVIDENCE",
            match_status=match_status,
            confidence=confidence,
            match_summary=checklist,
            evidence=evidence_payload,
            normalized_claim_payload={"reference": ref_val, "supporting": supp},
            normalized_verified_payload={"evidence_validated": v_status == VerificationStatus.VERIFIED, "checklist": checklist},
            raw_response={"checklist": checklist, "score": score},
            error_code=None,
            error_message=reason if v_status == VerificationStatus.NEEDS_REVIEW else None,
        )
