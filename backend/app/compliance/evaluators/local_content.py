"""
Local Content & Make in India Compliance Rule Evaluator for Part 6D
Evaluates Make-in-India (MII) local content percentage thresholds, supplier classifications
(Class-I, Class-II), and declaration evidence against verified Part 5 records.
"""

from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.compliance.evaluators.base import ComplianceRuleEvaluator
from app.compliance.evaluators.financial import normalize_indian_currency
from app.compliance.operators import compare_numbers, evaluate_generic_operator
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

LOCAL_CONTENT_KEYWORDS = {
    "local_content",
    "make_in_india",
    "mii",
    "local_supplier",
    "supplier_class",
    "class_i",
    "class_ii",
    "domestic_content",
    "indigenous_content",
}


def normalize_supplier_class(val: Any) -> str:
    """Normalizes supplier class strings to standard format."""
    if not val:
        return "UNKNOWN"
    val_upper = str(val).strip().upper()
    if "CLASS_II" in val_upper or "CLASS-II" in val_upper or "CLASS 2" in val_upper or "CLASS-2" in val_upper:
        return "CLASS_II"
    if "CLASS_I" in val_upper or "CLASS-I" in val_upper or "CLASS 1" in val_upper or "CLASS-1" in val_upper:
        return "CLASS_I"
    if "NON_LOCAL" in val_upper or "NON-LOCAL" in val_upper:
        return "NON_LOCAL"
    return val_upper


class LocalContentComplianceEvaluator(ComplianceRuleEvaluator):
    """
    Specialized compliance evaluator for Make in India and Local Content requirements.
    """

    @property
    def evaluator_name(self) -> str:
        return "LocalContentComplianceEvaluator"

    def supports(self, requirement: TenderRequirement) -> bool:
        """
        Determines if this evaluator handles the requirement.
        """
        category = (requirement.category or "").strip().upper()
        if category in ("LOCAL_CONTENT", "MAKE_IN_INDIA", "MII"):
            return True

        code_lower = (requirement.code or "").strip().lower()
        name_lower = (requirement.name or "").strip().lower()

        tokens = set(
            code_lower.replace("_", " ").replace("-", " ").split()
            + name_lower.replace("_", " ").replace("-", " ").split()
        )

        return any(kw in tokens for kw in LOCAL_CONTENT_KEYWORDS)

    def evaluate(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> ComplianceRuleResult:
        """
        Evaluates local content criteria against verified Part 5 records.
        """
        code_upper = (requirement.code or "").strip().upper()
        name_lower = (requirement.name or "").strip().lower()
        req_type = (requirement.requirement_type or "NUMBER").upper()
        operator = (requirement.operator or "GREATER_THAN_OR_EQUAL").upper()
        expected = requirement.expected_value
        is_mandatory = requirement.is_mandatory if requirement.is_mandatory is not None else True
        weight = requirement.weight

        # ---------------------------------------------------------------------
        # 1. Document Upload Presence Rule
        # ---------------------------------------------------------------------
        if req_type == "DOCUMENT" or "DOCUMENT_REQUIRED" in code_upper or "DECLARATION_REQUIRED" in code_upper:
            return self._evaluate_document_presence(requirement, context, is_mandatory, weight)

        # ---------------------------------------------------------------------
        # 2. Extract Verified Local Content Data
        # ---------------------------------------------------------------------
        lc_data, primary_v, source_ids, evidence_dict, issue_status, issue_reason = self._extract_local_content_data(
            requirement, context, is_mandatory
        )

        if issue_status:
            return ComplianceRuleResult(
                compliance_status=issue_status,
                actual_value=None,
                expected_value=expected,
                operator=operator,
                reason=issue_reason,
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 3. Supplier Class Rule (Class-I / Class-II)
        # ---------------------------------------------------------------------
        if "CLASS" in code_upper or "supplier_class" in name_lower:
            return self._evaluate_supplier_class(
                requirement=requirement,
                lc_data=lc_data,
                expected=expected,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 4. Local Content Percentage Threshold Rule
        # ---------------------------------------------------------------------
        return self._evaluate_percentage_threshold(
            requirement=requirement,
            lc_data=lc_data,
            expected=expected,
            operator=operator,
            source_ids=source_ids,
            evidence_dict=evidence_dict,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_document_presence(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """Evaluates upload presence of Make in India declaration."""
        matching_docs = [
            d for d in context.bid_documents
            if d.is_active and (
                "LOCAL_CONTENT" in (d.document_type or "").upper()
                or "MII" in (d.document_type or "").upper()
                or "MAKE_IN_INDIA" in (d.document_type or "").upper()
                or d.tender_requirement_id == requirement.id
            )
        ]

        if matching_docs:
            doc = matching_docs[0]
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.PASS,
                actual_value=doc.document_name,
                expected_value=True,
                operator=ComplianceOperator.EXISTS,
                reason=f"Local content declaration document '{doc.document_name}' is uploaded and verified.",
                evidence={"document_id": str(doc.id), "document_name": doc.document_name},
                source_verification_ids=[],
                is_mandatory=is_mandatory,
                weight=weight,
            )

        return ComplianceRuleResult(
            compliance_status=ComplianceStatus.FAIL if is_mandatory else ComplianceStatus.REVIEW,
            actual_value=None,
            expected_value=True,
            operator=ComplianceOperator.EXISTS,
            reason="Required Local Content / Make in India declaration document is missing.",
            evidence={"requirement_code": requirement.code},
            source_verification_ids=[],
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _extract_local_content_data(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
        is_mandatory: bool,
    ) -> Tuple[Dict[str, Any], Optional[VerificationRecord], List[str], Dict[str, Any], Optional[str], Optional[str]]:
        """
        Extracts verified Local Content payload and enforces verification prerequisite policy.
        """
        source_ids: List[str] = []
        evidence_dict: Dict[str, Any] = {}

        lc_verifications = [
            v for v in context.verifications
            if v.verification_type in ("LOCAL_CONTENT", "DPIIT")
            or "local_content" in (v.claim_source or "").lower()
            or "mii" in (v.claim_source or "").lower()
        ]

        if not lc_verifications:
            # Check document structured extractions
            for doc in context.bid_documents:
                if not doc.is_active:
                    continue
                proc = doc.processing
                if proc and proc.extracted_data and isinstance(proc.extracted_data, dict):
                    ext = proc.extracted_data
                    if any(k in ext for k in ("local_content_percentage", "supplier_class", "mii_percentage")):
                        evidence_dict["extracted_from_document"] = doc.document_name
                        return ext, None, [], evidence_dict, None, None

            return {}, None, [], evidence_dict, (
                ComplianceStatus.FAIL if is_mandatory else ComplianceStatus.PENDING
            ), f"No Local Content verification record or declaration found for requirement '{requirement.code}'."

        primary_v = lc_verifications[0]
        source_ids.append(str(primary_v.id))
        evidence_dict["verification_id"] = str(primary_v.id)
        evidence_dict["verification_status"] = primary_v.verification_status
        evidence_dict["source_name"] = primary_v.source_name
        evidence_dict["source_type"] = primary_v.source_type

        # Prerequisite status handling
        if primary_v.verification_status in (VerificationStatus.UNAVAILABLE, "FAILED"):
            return {}, primary_v, source_ids, evidence_dict, ComplianceStatus.REVIEW, (
                f"External verification source ({primary_v.source_name}) is temporarily unavailable. "
                f"Requirement is placed under review without penalizing bidder."
            )

        if primary_v.verification_status == VerificationStatus.NEEDS_REVIEW:
            return {}, primary_v, source_ids, evidence_dict, ComplianceStatus.REVIEW, (
                f"Local Content verification requires review: {primary_v.error_message or 'Declaration consistency flag'}"
            )

        if primary_v.verification_status == VerificationStatus.NOT_VERIFIED:
            return {}, primary_v, source_ids, evidence_dict, ComplianceStatus.FAIL, (
                f"Local Content claim could not be verified in authoritative source ({primary_v.source_name})."
            )

        v_payload = primary_v.response_payload or primary_v.evidence or {}
        if not isinstance(v_payload, dict):
            v_payload = {}

        return v_payload, primary_v, source_ids, evidence_dict, None, None

    def _evaluate_percentage_threshold(
        self,
        requirement: TenderRequirement,
        lc_data: Dict[str, Any],
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates local content percentage threshold (e.g. >= 50%).
        """
        actual_raw = lc_data.get("local_content_percentage") or lc_data.get("percentage") or lc_data.get("mii_percentage")
        actual_dec = normalize_indian_currency(actual_raw)

        expected_dec = normalize_indian_currency(expected)
        if expected_dec is None:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=float(actual_dec) if actual_dec is not None else None,
                expected_value=expected,
                operator=operator,
                reason=f"Invalid tender requirement configuration: expected local content percentage '{expected}' is invalid.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        if actual_dec is None:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=float(expected_dec),
                operator=operator,
                reason="Local content percentage is missing or could not be determined reliably.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # Range check 0% to 100%
        if actual_dec < Decimal("0") or actual_dec > Decimal("100"):
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=float(actual_dec),
                expected_value=float(expected_dec),
                operator=operator,
                reason=f"Impossible local content percentage '{actual_dec}%' detected in submitted declaration (must be 0-100%). Manual review required.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        evidence_dict["verified_percentage"] = float(actual_dec)
        evidence_dict["required_percentage"] = float(expected_dec)

        comp_ok, err_msg = compare_numbers(actual_dec, expected_dec, operator)
        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"Verified local content is {actual_dec}%, meeting the minimum requirement of {expected_dec}%."
            if comp_ok
            else f"Verified local content is {actual_dec}%, below the required minimum of {expected_dec}%."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=float(actual_dec),
            expected_value=float(expected_dec),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_supplier_class(
        self,
        requirement: TenderRequirement,
        lc_data: Dict[str, Any],
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates Make in India supplier classification (Class-I, Class-II, Non-Local).
        """
        actual_raw = lc_data.get("supplier_class")
        actual_class = normalize_supplier_class(actual_raw)

        if actual_class == "UNKNOWN":
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=str(actual_raw) if actual_raw else None,
                expected_value=expected,
                operator=operator,
                reason="Supplier class is missing or unclassified in the Local Content declaration.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        evidence_dict["actual_supplier_class"] = actual_class
        evidence_dict["expected_supplier_class"] = expected

        comp_ok, err_msg = evaluate_generic_operator(
            actual=actual_class,
            expected=expected,
            operator=operator,
            requirement_type="TEXT",
        )

        status = ComplianceStatus.PASS if comp_ok else (ComplianceStatus.FAIL if is_mandatory else ComplianceStatus.REVIEW)
        reason = (
            f"Verified supplier classification ('{actual_class}') satisfies requirement condition ({operator} '{expected}')."
            if comp_ok
            else f"Verified supplier classification ('{actual_class}') does not meet required class '{expected}'."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=str(actual_class),
            expected_value=str(expected),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )
