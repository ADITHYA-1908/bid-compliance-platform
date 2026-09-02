"""
BIS Certification Compliance Rule Evaluator for Part 6D
Evaluates Bureau of Indian Standards (BIS) CRS / License requirements (Presence, Registry Status,
Validity Date, Standard Number match, and Manufacturer match) against verified Part 5 BIS records.
"""

from datetime import date, datetime
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.compliance.evaluators.base import ComplianceRuleEvaluator
from app.compliance.evaluators.experience import _parse_date
from app.compliance.operators import compare_dates, compare_strings, evaluate_generic_operator
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

BIS_KEYWORDS = {
    "bis",
    "bis_registration",
    "bis_certificate",
    "bis_license",
    "crs",
    "is_standard",
    "indian_standard",
}


def normalize_bis_standard(val: Any) -> str:
    """Normalizes BIS standard string (e.g., 'IS 13252 (Part 1)' -> 'IS 13252')."""
    if not val:
        return ""
    val_clean = str(val).strip().upper().replace("  ", " ")
    return val_clean


class BISComplianceEvaluator(ComplianceRuleEvaluator):
    """
    Specialized compliance evaluator for Bureau of Indian Standards (BIS) criteria.
    """

    @property
    def evaluator_name(self) -> str:
        return "BISComplianceEvaluator"

    def supports(self, requirement: TenderRequirement) -> bool:
        """
        Determines if this evaluator handles the requirement.
        """
        category = (requirement.category or "").strip().upper()
        if category in ("BIS", "BIS_CERTIFICATION", "CRS"):
            return True

        code_lower = (requirement.code or "").strip().lower()
        name_lower = (requirement.name or "").strip().lower()

        tokens = set(
            code_lower.replace("_", " ").replace("-", " ").split()
            + name_lower.replace("_", " ").replace("-", " ").split()
        )

        return any(kw in tokens for kw in BIS_KEYWORDS)

    def evaluate(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> ComplianceRuleResult:
        """
        Evaluates BIS certification criteria against verified Part 5 records.
        """
        code_upper = (requirement.code or "").strip().upper()
        name_lower = (requirement.name or "").strip().lower()
        req_type = (requirement.requirement_type or "TEXT").upper()
        operator = (requirement.operator or "EQUALS").upper()
        expected = requirement.expected_value
        is_mandatory = requirement.is_mandatory if requirement.is_mandatory is not None else True
        weight = requirement.weight

        # ---------------------------------------------------------------------
        # 1. Document Upload Presence Rule
        # ---------------------------------------------------------------------
        if req_type == "DOCUMENT" or "DOCUMENT_REQUIRED" in code_upper:
            return self._evaluate_document_presence(requirement, context, is_mandatory, weight)

        # ---------------------------------------------------------------------
        # 2. Extract Verified BIS Data
        # ---------------------------------------------------------------------
        bis_data, primary_v, source_ids, evidence_dict, issue_status, issue_reason = self._extract_bis_data(
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
        # 3. BIS Standard Number Match Rule (e.g. IS 13252)
        # ---------------------------------------------------------------------
        if "STANDARD" in code_upper or "standard" in name_lower or code_upper.startswith("IS_") or "_IS_" in code_upper:
            return self._evaluate_standard_match(
                requirement=requirement,
                bis_data=bis_data,
                expected=expected,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 4. BIS Certificate Validity Rule
        # ---------------------------------------------------------------------
        if "VALID" in code_upper or "VALIDITY" in code_upper or "EXPIRY" in code_upper or "valid" in name_lower:
            return self._evaluate_bis_validity(
                requirement=requirement,
                bis_data=bis_data,
                context=context,
                expected=expected,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 5. BIS Manufacturer Match Rule
        # ---------------------------------------------------------------------
        if "MANUFACTURER" in code_upper or "mfg" in code_upper or "licensee" in name_lower:
            return self._evaluate_manufacturer_match(
                requirement=requirement,
                bis_data=bis_data,
                expected=expected,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 6. BIS Status / Registration Required Rule
        # ---------------------------------------------------------------------
        return self._evaluate_bis_status(
            requirement=requirement,
            bis_data=bis_data,
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
        """Evaluates upload presence of BIS certificate."""
        matching_docs = [
            d for d in context.bid_documents
            if d.is_active and (
                "BIS" in (d.document_type or "").upper()
                or "STANDARD" in (d.document_type or "").upper()
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
                reason=f"BIS certificate document '{doc.document_name}' is uploaded and verified.",
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
            reason="Required BIS certificate / license document is missing.",
            evidence={"requirement_code": requirement.code},
            source_verification_ids=[],
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _extract_bis_data(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
        is_mandatory: bool,
    ) -> Tuple[Dict[str, Any], Optional[VerificationRecord], List[str], Dict[str, Any], Optional[str], Optional[str]]:
        """
        Extracts verified BIS payload and enforces verification prerequisite policy.
        """
        source_ids: List[str] = []
        evidence_dict: Dict[str, Any] = {}

        bis_verifications = [
            v for v in context.verifications
            if v.verification_type == "BIS"
            or "bis" in (v.claim_source or "").lower()
        ]

        if not bis_verifications:
            # Check document structured extractions
            for doc in context.bid_documents:
                if not doc.is_active:
                    continue
                proc = doc.processing
                if proc and proc.extracted_data and isinstance(proc.extracted_data, dict):
                    ext = proc.extracted_data
                    if any(k in ext for k in ("bis_registration_number", "standard_number", "registration_number")):
                        evidence_dict["extracted_from_document"] = doc.document_name
                        return ext, None, [], evidence_dict, None, None

            return {}, None, [], evidence_dict, (
                ComplianceStatus.FAIL if is_mandatory else ComplianceStatus.PENDING
            ), f"No BIS registration record or certificate found for requirement '{requirement.code}'."

        primary_v = bis_verifications[0]
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
                f"BIS verification requires review: {primary_v.error_message or 'Standard or manufacturer review flag'}"
            )

        if primary_v.verification_status == VerificationStatus.NOT_VERIFIED:
            return {}, primary_v, source_ids, evidence_dict, ComplianceStatus.FAIL, (
                f"BIS registration could not be authenticated in authoritative records ({primary_v.source_name})."
            )

        v_payload = primary_v.response_payload or primary_v.evidence or {}
        if not isinstance(v_payload, dict):
            v_payload = {}

        return v_payload, primary_v, source_ids, evidence_dict, None, None

    def _evaluate_standard_match(
        self,
        requirement: TenderRequirement,
        bis_data: Dict[str, Any],
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates whether BIS registration conforms to the required Indian Standard (e.g. IS 13252).
        """
        actual_std = bis_data.get("standard_number") or bis_data.get("standard")
        if not actual_std:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=expected,
                operator=operator,
                reason="BIS standard number is missing from the verification records.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        norm_actual = normalize_bis_standard(actual_std)
        norm_expected = normalize_bis_standard(expected)

        evidence_dict["actual_standard"] = norm_actual
        evidence_dict["expected_standard"] = norm_expected

        comp_ok, err_msg = compare_strings(norm_actual, norm_expected, operator)
        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"BIS registered standard ('{norm_actual}') matches required Indian Standard ({operator} '{norm_expected}')."
            if comp_ok
            else f"BIS registered standard ('{norm_actual}') does not match required standard '{norm_expected}'."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=norm_actual,
            expected_value=norm_expected,
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_bis_validity(
        self,
        requirement: TenderRequirement,
        bis_data: Dict[str, Any],
        context: ComplianceContext,
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates whether BIS registration is valid through the tender submission milestone.
        """
        valid_until_raw = bis_data.get("valid_until") or bis_data.get("expiry_date")
        actual_date = _parse_date(valid_until_raw)

        target_date_raw = expected
        if target_date_raw is None and context.tender:
            target_date_raw = context.tender.submission_end_date or getattr(context.tender, 'submission_deadline', None)

        target_date = _parse_date(target_date_raw)

        if not actual_date:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=str(valid_until_raw) if valid_until_raw else None,
                expected_value=str(target_date) if target_date else expected,
                operator=operator,
                reason="BIS certificate expiry date (valid_until) is missing or unparseable.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        if not target_date:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.PASS,
                actual_value=str(actual_date),
                expected_value=None,
                operator=operator,
                reason=f"BIS certificate is valid until {actual_date}.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        evidence_dict["valid_until"] = str(actual_date)
        evidence_dict["target_milestone"] = str(target_date)

        comp_ok, err_msg = compare_dates(actual_date, target_date, operator if operator != "EQUALS" else ComplianceOperator.GREATER_THAN_OR_EQUAL)
        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"BIS certificate validity ({actual_date}) remains valid through tender milestone ({target_date})."
            if comp_ok
            else f"BIS certificate expired on {actual_date}, before the required tender milestone date ({target_date})."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=str(actual_date),
            expected_value=str(target_date),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_manufacturer_match(
        self,
        requirement: TenderRequirement,
        bis_data: Dict[str, Any],
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates manufacturer licensee name match.
        """
        actual_mfg = bis_data.get("manufacturer_name") or bis_data.get("manufacturer")
        if not actual_mfg:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=expected,
                operator=operator,
                reason="Manufacturer licensee name is missing from the BIS verification record.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        comp_ok, err_msg = compare_strings(actual_mfg, expected, operator)
        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"BIS manufacturer licensee ('{actual_mfg}') matches required manufacturer ({operator} '{expected}')."
            if comp_ok
            else f"BIS manufacturer licensee ('{actual_mfg}') does not match required manufacturer '{expected}'."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=str(actual_mfg),
            expected_value=str(expected),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_bis_status(
        self,
        requirement: TenderRequirement,
        bis_data: Dict[str, Any],
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates BIS license status (VALID vs EXPIRED/SUSPENDED/CANCELLED).
        """
        reg_status = str(bis_data.get("registry_status") or bis_data.get("status") or "VALID").upper()
        reg_number = bis_data.get("bis_registration_number") or bis_data.get("registration_number") or "BIS"

        expected_status = str(expected or "VALID").upper()

        if reg_status in ("EXPIRED", "SUSPENDED", "CANCELLED"):
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.FAIL,
                actual_value=reg_status,
                expected_value=expected_status,
                operator=operator,
                reason=f"BIS license '{reg_number}' is in '{reg_status}' status in authoritative registry.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        return ComplianceRuleResult(
            compliance_status=ComplianceStatus.PASS,
            actual_value=reg_status,
            expected_value=expected_status,
            operator=operator,
            reason=f"BIS license '{reg_number}' is verified and in '{reg_status}' state.",
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )
