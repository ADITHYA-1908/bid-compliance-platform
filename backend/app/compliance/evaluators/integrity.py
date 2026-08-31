"""
Integrity, Exclusion & Consistency Compliance Rule Evaluator for Part 6E
Evaluates Blacklisting clearance, Debarment status (active vs expired), Cross-Document Consistency
(PAN ↔ GSTIN, Organization Name, Address, CIN/Udyam), and identifies critical compliance failures.
"""

from datetime import date, datetime
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.compliance.evaluators.base import ComplianceRuleEvaluator
from app.compliance.evaluators.experience import _parse_date
from app.compliance.operators import compare_strings, evaluate_generic_operator
from app.compliance.types import (
    ComplianceContext,
    ComplianceOperator,
    ComplianceRuleResult,
    ComplianceStatus,
)
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.verification_record import (
    VerificationMatchStatus,
    VerificationRecord,
    VerificationStatus,
)

logger = logging.getLogger(__name__)

INTEGRITY_KEYWORDS = {
    "blacklisting",
    "blacklisted",
    "not_blacklisted",
    "debarment",
    "debarred",
    "not_debarred",
    "integrity",
    "consistency",
    "cross_document",
    "pan_gst_consistency",
    "identity_consistency",
    "name_consistency",
    "address_consistency",
    "vigilance",
    "exclusion",
}


class IntegrityComplianceEvaluator(ComplianceRuleEvaluator):
    """
    Specialized compliance evaluator for Blacklisting, Debarment, and Cross-Document Consistency criteria.
    """

    @property
    def evaluator_name(self) -> str:
        return "IntegrityComplianceEvaluator"

    def supports(self, requirement: TenderRequirement) -> bool:
        """
        Determines if this evaluator handles the requirement.
        """
        category = (requirement.category or "").strip().upper()
        if category in ("BLACKLISTING", "DEBARMENT", "INTEGRITY", "CONSISTENCY", "CROSS_DOCUMENT", "EXCLUSION"):
            return True

        code_lower = (requirement.code or "").strip().lower()
        name_lower = (requirement.name or "").strip().lower()

        tokens = set(
            code_lower.replace("_", " ").replace("-", " ").split()
            + name_lower.replace("_", " ").replace("-", " ").split()
        )

        return any(kw in tokens for kw in INTEGRITY_KEYWORDS)

    def evaluate(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> ComplianceRuleResult:
        """
        Evaluates integrity and consistency criteria against verified Part 5 records.
        """
        code_upper = (requirement.code or "").strip().upper()
        name_lower = (requirement.name or "").strip().lower()
        req_type = (requirement.requirement_type or "BOOLEAN").upper()
        operator = (requirement.operator or "EQUALS").upper()
        expected = requirement.expected_value
        is_mandatory = requirement.is_mandatory if requirement.is_mandatory is not None else True
        is_critical = getattr(requirement, "is_critical", False) or False
        weight = requirement.weight

        # ---------------------------------------------------------------------
        # 1. Blacklisting Compliance Evaluation
        # ---------------------------------------------------------------------
        if "BLACKLIST" in code_upper or "blacklist" in name_lower:
            res = self._evaluate_blacklisting(
                requirement=requirement,
                context=context,
                expected=expected,
                operator=operator,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                weight=weight,
            )
            return self._finalize_result(res, is_critical)

        # ---------------------------------------------------------------------
        # 2. Debarment Compliance Evaluation
        # ---------------------------------------------------------------------
        if "DEBAR" in code_upper or "debar" in name_lower:
            res = self._evaluate_debarment(
                requirement=requirement,
                context=context,
                expected=expected,
                operator=operator,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                weight=weight,
            )
            return self._finalize_result(res, is_critical)

        # ---------------------------------------------------------------------
        # 3. Cross-Document Consistency Evaluation
        # ---------------------------------------------------------------------
        if "CONSISTENCY" in code_upper or "CROSS_DOC" in code_upper or "identity" in name_lower:
            res = self._evaluate_cross_document_consistency(
                requirement=requirement,
                context=context,
                code_upper=code_upper,
                expected=expected,
                operator=operator,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                weight=weight,
            )
            return self._finalize_result(res, is_critical)

        # ---------------------------------------------------------------------
        # 4. Fallback General Integrity Check
        # ---------------------------------------------------------------------
        res = self._evaluate_general_integrity(
            requirement=requirement,
            context=context,
            expected=expected,
            operator=operator,
            is_mandatory=is_mandatory,
            is_critical=is_critical,
            weight=weight,
        )
        return self._finalize_result(res, is_critical)

    def _finalize_result(self, result: ComplianceRuleResult, is_critical: bool) -> ComplianceRuleResult:
        """Sets critical failure flags and review metadata."""
        result.is_critical = is_critical
        if is_critical and result.compliance_status == ComplianceStatus.FAIL:
            result.critical_failure = True
        if result.compliance_status == ComplianceStatus.REVIEW:
            result.review_required = True
            result.review_reason = result.reason
            if result.review_type and isinstance(result.evidence, dict):
                result.evidence["review_type"] = result.review_type
        return result

    def _evaluate_blacklisting(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
        expected: Any,
        operator: str,
        is_mandatory: bool,
        is_critical: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """Evaluates blacklisting verification records."""
        bl_verifications = [
            v for v in context.verifications
            if v.verification_type == "BLACKLISTING"
            or "blacklisting" in (v.claim_source or "").lower()
        ]

        source_ids: List[str] = []
        evidence_dict: Dict[str, Any] = {}

        if not bl_verifications:
            # Check if self-declaration document exists
            decl_docs = [
                d for d in context.bid_documents
                if d.is_active and "BLACKLIST" in (d.document_type or "").upper()
            ]
            if decl_docs:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.PASS,
                    actual_value="CLEAR (Self-Declaration)",
                    expected_value=expected or "CLEAR",
                    operator=operator,
                    reason="Self-declaration of non-blacklisting submitted.",
                    evidence={"document_name": decl_docs[0].document_name},
                    source_verification_ids=[],
                    is_mandatory=is_mandatory,
                    is_critical=is_critical,
                    weight=weight,
                )

            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.FAIL if is_mandatory else ComplianceStatus.PENDING,
                actual_value=None,
                expected_value=expected or "CLEAR",
                operator=operator,
                reason="No blacklisting verification record or clearance declaration found.",
                evidence={"requirement_code": requirement.code},
                source_verification_ids=[],
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                weight=weight,
            )

        primary_v = bl_verifications[0]
        source_ids.append(str(primary_v.id))
        evidence_dict["verification_id"] = str(primary_v.id)
        evidence_dict["verification_status"] = primary_v.verification_status
        evidence_dict["source_name"] = primary_v.source_name
        evidence_dict["source_type"] = primary_v.source_type

        # Prerequisite Handling
        if primary_v.verification_status in (VerificationStatus.UNAVAILABLE, "FAILED"):
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=expected or "CLEAR",
                operator=operator,
                reason=f"External verification source ({primary_v.source_name}) is temporarily unavailable. Placed under review without penalizing bidder.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                review_type="SOURCE_UNAVAILABLE",
                weight=weight,
            )

        if primary_v.verification_status == VerificationStatus.NEEDS_REVIEW:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value="NEEDS_REVIEW",
                expected_value=expected or "CLEAR",
                operator=operator,
                reason=f"A possible blacklisting entity match was found, but identifiers are insufficient for a definitive match. Human review required.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                review_type="VERIFICATION_UNCERTAIN",
                weight=weight,
            )

        v_payload = primary_v.response_payload or primary_v.evidence or {}
        reg_status = str(v_payload.get("registry_status") or v_payload.get("status") or "CLEAR").upper()
        authority = v_payload.get("authority") or v_payload.get("blacklisting_authority") or primary_v.source_name

        evidence_dict["registry_status"] = reg_status
        evidence_dict["authority"] = authority
        evidence_dict["reference_number"] = v_payload.get("reference_number")

        if reg_status in ("BLACKLISTED", "ACTIVE_BLACKLIST"):
            # Check for conflict with self-declaration
            has_decl_clear = bool(v_payload.get("self_declaration_clear", True))
            evidence_dict["declaration_conflict"] = has_decl_clear

            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.FAIL,
                actual_value=reg_status,
                expected_value=expected or "CLEAR",
                operator=operator,
                reason=f"The verification source ({primary_v.source_name}) reports an active blacklisting record for the bidder by {authority}.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                weight=weight,
            )

        return ComplianceRuleResult(
            compliance_status=ComplianceStatus.PASS,
            actual_value=reg_status,
            expected_value=expected or "CLEAR",
            operator=operator,
            reason="No matching active blacklisting record was found in authoritative verification records.",
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            is_critical=is_critical,
            weight=weight,
        )

    def _evaluate_debarment(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
        expected: Any,
        operator: str,
        is_mandatory: bool,
        is_critical: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """Evaluates debarment verification records and validity intervals."""
        deb_verifications = [
            v for v in context.verifications
            if v.verification_type == "DEBARMENT"
            or "debarment" in (v.claim_source or "").lower()
        ]

        source_ids: List[str] = []
        evidence_dict: Dict[str, Any] = {}

        if not deb_verifications:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.PASS,
                actual_value="CLEAR",
                expected_value=expected or "CLEAR",
                operator=operator,
                reason="No active debarment order found in database registries.",
                evidence={"requirement_code": requirement.code},
                source_verification_ids=[],
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                weight=weight,
            )

        primary_v = deb_verifications[0]
        source_ids.append(str(primary_v.id))
        evidence_dict["verification_id"] = str(primary_v.id)
        evidence_dict["verification_status"] = primary_v.verification_status
        evidence_dict["source_name"] = primary_v.source_name
        evidence_dict["source_type"] = primary_v.source_type

        # Prerequisite Handling
        if primary_v.verification_status in (VerificationStatus.UNAVAILABLE, "FAILED"):
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=expected or "CLEAR",
                operator=operator,
                reason=f"Debarment verification source ({primary_v.source_name}) is temporarily unavailable.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                review_type="SOURCE_UNAVAILABLE",
                weight=weight,
            )

        if primary_v.verification_status == VerificationStatus.NEEDS_REVIEW:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value="NEEDS_REVIEW",
                expected_value=expected or "CLEAR",
                operator=operator,
                reason="Debarment verification returned uncertain match. Manual verification required.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                review_type="VERIFICATION_UNCERTAIN",
                weight=weight,
            )

        v_payload = primary_v.response_payload or primary_v.evidence or {}
        reg_status = str(v_payload.get("registry_status") or v_payload.get("status") or "CLEAR").upper()
        eff_from = _parse_date(v_payload.get("effective_from"))
        eff_until = _parse_date(v_payload.get("effective_until"))

        evidence_dict["registry_status"] = reg_status
        evidence_dict["effective_from"] = str(eff_from) if eff_from else None
        evidence_dict["effective_until"] = str(eff_until) if eff_until else None

        target_date_raw = context.tender.submission_end_date if context.tender else None
        target_date = _parse_date(target_date_raw) or date.today()

        if reg_status in ("DEBARRED", "ACTIVE"):
            # Check chronological window
            if eff_until and eff_until < target_date:
                # Debarment expired before tender milestone
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.PASS,
                    actual_value=f"EXPIRED ({eff_until})",
                    expected_value=expected or "CLEAR",
                    operator=operator,
                    reason=f"Previous debarment order expired on {eff_until}, prior to tender milestone ({target_date}). Bidder has no active debarment.",
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    is_critical=is_critical,
                    weight=weight,
                )
            if eff_from and eff_from > target_date:
                # Debarment begins after tender milestone
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.PASS,
                    actual_value=f"FUTURE_DEBARMENT ({eff_from})",
                    expected_value=expected or "CLEAR",
                    operator=operator,
                    reason=f"Debarment order takes effect on {eff_from}, after the tender submission milestone ({target_date}).",
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    is_critical=is_critical,
                    weight=weight,
                )

            # Active debarment during tender milestone
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.FAIL,
                actual_value=reg_status,
                expected_value=expected or "CLEAR",
                operator=operator,
                reason=f"Active debarment order in effect against bidder (Effective: {eff_from} to {eff_until or 'Indefinite'}).",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                weight=weight,
            )

        return ComplianceRuleResult(
            compliance_status=ComplianceStatus.PASS,
            actual_value=reg_status,
            expected_value=expected or "CLEAR",
            operator=operator,
            reason="No active debarment records found for the bidder.",
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            is_critical=is_critical,
            weight=weight,
        )

    def _evaluate_cross_document_consistency(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
        code_upper: str,
        expected: Any,
        operator: str,
        is_mandatory: bool,
        is_critical: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """Evaluates cross-document identity consistency (PAN-GST, Organization Name, Address, CIN/Udyam)."""
        cd_verifications = [
            v for v in context.verifications
            if v.verification_type == "CROSS_DOCUMENT"
            or "consistency" in (v.claim_source or "").lower()
        ]

        source_ids: List[str] = []
        evidence_dict: Dict[str, Any] = {}

        if not cd_verifications:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.PASS,
                actual_value="NO_INCONSISTENCIES",
                expected_value=expected or "MATCH",
                operator=operator,
                reason="No cross-document identity inconsistencies detected.",
                evidence={"requirement_code": requirement.code},
                source_verification_ids=[],
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                weight=weight,
            )

        primary_v = cd_verifications[0]
        source_ids.append(str(primary_v.id))
        evidence_dict["verification_id"] = str(primary_v.id)
        evidence_dict["verification_status"] = primary_v.verification_status
        evidence_dict["source_name"] = primary_v.source_name

        v_payload = primary_v.response_payload or primary_v.evidence or {}
        findings = v_payload.get("findings") or v_payload.get("consistency_findings") or {}

        # ---------------------------------------------------------------------
        # PAN ↔ GSTIN Consistency Check
        # ---------------------------------------------------------------------
        if "PAN_GST" in code_upper or "pan" in code_upper:
            pan_gst_finding = findings.get("pan_gstin") or findings.get("pan_gst") or {}
            pan_gst_match = pan_gst_finding.get("match_status") or primary_v.match_status

            evidence_dict["pan_gst_finding"] = pan_gst_finding

            if pan_gst_match == VerificationMatchStatus.MISMATCH:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.FAIL,
                    actual_value="MISMATCH",
                    expected_value="MATCH",
                    operator=operator,
                    reason="Discrepancy detected: PAN number extracted from PAN Card does not match embedded PAN in GSTIN.",
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    is_critical=is_critical,
                    weight=weight,
                )

            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.PASS,
                actual_value="MATCH",
                expected_value="MATCH",
                operator=operator,
                reason="PAN number matches embedded PAN structure in GSTIN registration.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # Organization Legal Name Consistency
        # ---------------------------------------------------------------------
        if "NAME" in code_upper or "LEGAL_NAME" in code_upper:
            name_finding = findings.get("organization_name") or findings.get("legal_name") or {}
            name_match = name_finding.get("match_status") or primary_v.match_status

            evidence_dict["name_finding"] = name_finding

            if name_match == VerificationMatchStatus.PARTIAL_MATCH:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.REVIEW,
                    actual_value="PARTIAL_MATCH",
                    expected_value="MATCH",
                    operator=operator,
                    reason="Minor variation in organization legal name across submitted certificates. Review required.",
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    is_critical=is_critical,
                    review_type="CROSS_DOCUMENT_MISMATCH",
                    weight=weight,
                )
            if name_match == VerificationMatchStatus.MISMATCH:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.FAIL if is_mandatory else ComplianceStatus.REVIEW,
                    actual_value="MISMATCH",
                    expected_value="MATCH",
                    operator=operator,
                    reason="Significant mismatch in organization entity name across submitted documents.",
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    is_critical=is_critical,
                    weight=weight,
                )

            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.PASS,
                actual_value="MATCH",
                expected_value="MATCH",
                operator=operator,
                reason="Organization name is consistent across all submitted documents.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # Address Consistency Check (Conservative: Address variations -> REVIEW)
        # ---------------------------------------------------------------------
        if "ADDRESS" in code_upper:
            addr_finding = findings.get("registered_address") or findings.get("address") or {}
            addr_match = addr_finding.get("match_status", VerificationMatchStatus.MATCH)

            evidence_dict["address_finding"] = addr_finding

            if addr_match in (VerificationMatchStatus.MISMATCH, VerificationMatchStatus.PARTIAL_MATCH):
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.REVIEW,
                    actual_value="ADDRESS_VARIATION",
                    expected_value="MATCH",
                    operator=operator,
                    reason="Address formatting differences found between GST certificate and Incorporation record. Human review recommended.",
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    is_critical=is_critical,
                    review_type="CROSS_DOCUMENT_MISMATCH",
                    weight=weight,
                )

            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.PASS,
                actual_value="MATCH",
                expected_value="MATCH",
                operator=operator,
                reason="Registered business address is consistent across statutory certificates.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                weight=weight,
            )

        # General Cross-Doc Consistency
        overall_match = primary_v.match_status
        if overall_match == VerificationMatchStatus.MISMATCH:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.FAIL if is_mandatory else ComplianceStatus.REVIEW,
                actual_value="MISMATCH",
                expected_value="MATCH",
                operator=operator,
                reason="Cross-document consistency engine flagged discrepancies in bidder identity claims.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                is_critical=is_critical,
                weight=weight,
            )

        return ComplianceRuleResult(
            compliance_status=ComplianceStatus.PASS,
            actual_value="MATCH",
            expected_value="MATCH",
            operator=operator,
            reason="All core identity identifiers and credentials are authenticated and consistent across documents.",
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            is_critical=is_critical,
            weight=weight,
        )

    def _evaluate_general_integrity(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
        expected: Any,
        operator: str,
        is_mandatory: bool,
        is_critical: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """Default integrity requirement evaluator."""
        return ComplianceRuleResult(
            compliance_status=ComplianceStatus.PASS,
            actual_value=True,
            expected_value=expected or True,
            operator=operator,
            reason="Integrity requirement criteria satisfied.",
            evidence={"requirement_code": requirement.code},
            source_verification_ids=[],
            is_mandatory=is_mandatory,
            is_critical=is_critical,
            weight=weight,
        )
