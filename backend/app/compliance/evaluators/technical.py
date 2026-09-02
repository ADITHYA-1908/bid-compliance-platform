"""
Technical & Specification Compliance Rule Evaluator for Part 6C
Evaluates deterministic technical parameters (Product Name, Model Number, Manufacturer,
Technical Document Presence, and Structured Technical Specifications) against
verified Part 5 records and Part 4 structured extractions.
"""

from decimal import Decimal
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.compliance.evaluators.base import ComplianceRuleEvaluator
from app.compliance.evaluators.financial import normalize_indian_currency
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

TECHNICAL_KEYWORDS = {
    "technical",
    "specification",
    "specifications",
    "product",
    "product_name",
    "model",
    "model_number",
    "make",
    "manufacturer",
    "datasheet",
    "data_sheet",
    "capacity",
    "rating",
    "voltage",
    "dimensions",
    "standard",
}


def normalize_model_number(val: Any) -> str:
    """
    Normalizes model number by removing punctuation, spaces, and converting to upper case.
    Example: 'X-100' -> 'X100', 'PRO 2026/A' -> 'PRO2026A'.
    """
    if val is None:
        return ""
    val_str = str(val).strip().upper()
    return re.sub(r"[^A-Z0-9]", "", val_str)


class TechnicalComplianceEvaluator(ComplianceRuleEvaluator):
    """
    Specialized compliance evaluator for technical specifications and equipment parameters.
    """

    @property
    def evaluator_name(self) -> str:
        return "TechnicalComplianceEvaluator"

    def supports(self, requirement: TenderRequirement) -> bool:
        """
        Determines if this evaluator handles the requirement.
        """
        category = (requirement.category or "").strip().upper()
        if category in ("BIS", "BIS_CERTIFICATION", "CRS", "OEM", "OEM_AUTHORIZATION", "LOCAL_CONTENT", "MAKE_IN_INDIA", "MII", "STATUTORY", "FINANCIAL", "EXPERIENCE"):
            return False

        if category in ("TECHNICAL", "SPECIFICATION", "PRODUCT", "EQUIPMENT"):
            return True

        code_lower = (requirement.code or "").strip().lower()
        if any(code_lower.startswith(prefix) for prefix in ("bis_", "oem_", "mii_", "local_content_")):
            return False

        name_lower = (requirement.name or "").strip().lower()

        tokens = set(
            code_lower.replace("_", " ").replace("-", " ").split()
            + name_lower.replace("_", " ").replace("-", " ").split()
        )

        return any(kw in tokens for kw in TECHNICAL_KEYWORDS)

    def evaluate(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> ComplianceRuleResult:
        """
        Evaluates a technical requirement against structured document extractions and verified records.
        """
        code_upper = (requirement.code or "").strip().upper()
        name_lower = (requirement.name or "").strip().lower()
        req_type = (requirement.requirement_type or "TEXT").upper()
        operator = (requirement.operator or "EQUALS").upper()
        expected = requirement.expected_value
        is_mandatory = requirement.is_mandatory if requirement.is_mandatory is not None else True
        weight = requirement.weight

        # ---------------------------------------------------------------------
        # 1. Technical Document Presence Rule
        # ---------------------------------------------------------------------
        if req_type == "DOCUMENT" or "DOCUMENT_REQUIRED" in code_upper or "DATASHEET_REQUIRED" in code_upper:
            return self._evaluate_document_presence(requirement, context, is_mandatory, weight)

        # ---------------------------------------------------------------------
        # 2. Extract Technical Data from Context
        # ---------------------------------------------------------------------
        tech_data, source_ids, evidence_dict, issue_status, issue_reason = self._extract_technical_data(
            requirement, context
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
        # 3. Model Number Rule (Exact Normalized Match)
        # ---------------------------------------------------------------------
        if "MODEL" in code_upper or "model" in name_lower:
            actual_model = tech_data.get("model_number") or tech_data.get("model") or tech_data.get("item_model")
            if not actual_model:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.REVIEW,
                    actual_value=None,
                    expected_value=expected,
                    operator=operator,
                    reason="Model number could not be extracted from the submitted technical documentation.",
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    weight=weight,
                )

            norm_actual = normalize_model_number(actual_model)
            norm_expected = normalize_model_number(expected)
            evidence_dict["model_raw"] = str(actual_model)
            evidence_dict["model_normalized"] = norm_actual

            is_match = norm_actual == norm_expected if operator in ("EQUALS", "==") else norm_expected in norm_actual
            status = ComplianceStatus.PASS if is_match else ComplianceStatus.FAIL
            reason = (
                f"Offered model '{actual_model}' satisfies requirement model '{expected}'."
                if is_match
                else f"Offered model '{actual_model}' does not match required model '{expected}'."
            )

            return ComplianceRuleResult(
                compliance_status=status,
                actual_value=str(actual_model),
                expected_value=str(expected),
                operator=operator,
                reason=reason,
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 4. Product Name / Make / Manufacturer Rule
        # ---------------------------------------------------------------------
        if "PRODUCT" in code_upper or "MANUFACTURER" in code_upper or "MAKE" in code_upper or "product" in name_lower:
            actual_prod = (
                tech_data.get("product_name")
                or tech_data.get("product")
                or tech_data.get("manufacturer")
                or tech_data.get("make")
                or tech_data.get("equipment_name")
            )

            if not actual_prod:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.REVIEW,
                    actual_value=None,
                    expected_value=expected,
                    operator=operator,
                    reason="Product name or manufacturer details could not be extracted from submitted technical proofs.",
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    weight=weight,
                )

            comp_ok, err_msg = compare_strings(actual_prod, expected, operator)
            if err_msg:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.REVIEW,
                    actual_value=str(actual_prod),
                    expected_value=str(expected),
                    operator=operator,
                    reason=err_msg,
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    weight=weight,
                )

            status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
            reason = (
                f"Technical product parameter '{actual_prod}' satisfies condition ({operator} '{expected}')."
                if comp_ok
                else f"Technical product parameter '{actual_prod}' fails condition ({operator} '{expected}')."
            )

            return ComplianceRuleResult(
                compliance_status=status,
                actual_value=str(actual_prod),
                expected_value=str(expected),
                operator=operator,
                reason=reason,
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 5. Technical Specifications / Parametric Values
        # ---------------------------------------------------------------------
        spec_field_name = requirement.code.lower().replace("req_", "").replace("tech_", "").replace("spec_", "")
        actual_val = tech_data.get(spec_field_name)

        # Search nested specifications dictionary if present
        specs_dict = tech_data.get("specifications") or tech_data.get("technical_specs") or {}
        if isinstance(specs_dict, dict) and actual_val is None:
            actual_val = specs_dict.get(spec_field_name)
            if actual_val is None:
                for k, v in specs_dict.items():
                    if spec_field_name in k.lower() or k.lower() in spec_field_name:
                        actual_val = v
                        break

        if actual_val is None:
            # Fallback to direct field search in tech_data
            for k, v in tech_data.items():
                if spec_field_name in k.lower():
                    actual_val = v
                    break

        if actual_val is None:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=expected,
                operator=operator,
                reason=f"Technical parameter '{requirement.name or requirement.code}' could not be extracted structuredly from submitted documents.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # Evaluate using generic operator
        comp_ok, err_msg = evaluate_generic_operator(
            actual=actual_val,
            expected=expected,
            operator=operator,
            requirement_type=req_type,
        )

        if err_msg:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=str(actual_val),
                expected_value=str(expected),
                operator=operator,
                reason=f"Technical specification evaluation could not complete deterministically: {err_msg}",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"Technical parameter value ('{actual_val}') satisfies requirement ({operator} '{expected}')."
            if comp_ok
            else f"Technical parameter value ('{actual_val}') fails requirement ({operator} '{expected}')."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=str(actual_val) if actual_val is not None else None,
            expected_value=str(expected) if expected is not None else None,
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
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
        """
        Evaluates requirement for uploading technical data sheets or catalogs.
        """
        matching_docs = [
            d for d in context.bid_documents
            if d.is_active and (
                "TECHNICAL" in (d.document_type or "").upper()
                or "DATASHEET" in (d.document_type or "").upper()
                or "CATALOGUE" in (d.document_type or "").upper()
                or "SPECIFICATION" in (d.document_type or "").upper()
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
                reason=f"Technical document '{doc.document_name}' is uploaded and verified.",
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
            reason="Required technical datasheet or product catalog document is missing.",
            evidence={"requirement_code": requirement.code},
            source_verification_ids=[],
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _extract_technical_data(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> Tuple[Dict[str, Any], List[str], Dict[str, Any], Optional[str], Optional[str]]:
        """
        Extracts technical parameters from Part 5 verification records or Part 4 extractions.
        """
        tech_data: Dict[str, Any] = {}
        source_ids: List[str] = []
        evidence_dict: Dict[str, Any] = {}

        # 1. Check Part 5 Verification Records
        tech_verifications = [
            v for v in context.verifications
            if "technical" in (v.claim_source or "").lower()
            or "product" in (v.claim_source or "").lower()
            or "model" in (v.claim_source or "").lower()
        ]

        if tech_verifications:
            primary_v = tech_verifications[0]
            source_ids.append(str(primary_v.id))
            evidence_dict["verification_id"] = str(primary_v.id)
            evidence_dict["verification_status"] = primary_v.verification_status
            evidence_dict["source_name"] = primary_v.source_name

            if primary_v.verification_status in (VerificationStatus.UNAVAILABLE, "FAILED"):
                return {}, source_ids, evidence_dict, ComplianceStatus.REVIEW, (
                    f"External verification source ({primary_v.source_name}) is temporarily unavailable. "
                    f"Requirement is placed under review without penalizing bidder."
                )

            if primary_v.verification_status == VerificationStatus.NEEDS_REVIEW:
                return {}, source_ids, evidence_dict, ComplianceStatus.REVIEW, (
                    f"Technical verification requires review: {primary_v.error_message or 'Scan quality flag'}"
                )

            if primary_v.verification_status == VerificationStatus.NOT_VERIFIED:
                return {}, source_ids, evidence_dict, ComplianceStatus.FAIL, (
                    f"Technical parameters could not be verified in authoritative source ({primary_v.source_name})."
                )

            payload = primary_v.response_payload or primary_v.evidence or {}
            if isinstance(payload, dict):
                tech_data.update(payload)

        # 2. Check Part 4 Structured Extractions from Active Documents
        for doc in context.bid_documents:
            if not doc.is_active:
                continue

            proc = doc.processing
            if proc and proc.extracted_data and isinstance(proc.extracted_data, dict):
                ext = proc.extracted_data
                if proc.extraction_requires_review or (proc.extraction_confidence and proc.extraction_confidence < 0.55):
                    evidence_dict["extraction_review_flag"] = True

                for k, v in ext.items():
                    tech_data.setdefault(k, v)

        if not tech_data:
            return {}, source_ids, evidence_dict, ComplianceStatus.PENDING, (
                f"No technical specifications or product data available for '{requirement.code}'."
            )

        return tech_data, source_ids, evidence_dict, None, None
