"""
Supporting Document Compliance Rule Evaluator for Part 6D
Evaluates generic supporting document presence, upload validity, document classification
alignment, and internal structural evidence for non-registry procurement requirements.
"""

from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional

from app.compliance.evaluators.base import ComplianceRuleEvaluator
from app.compliance.operators import evaluate_generic_operator
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

DOCUMENT_KEYWORDS = {
    "document",
    "document_required",
    "certificate",
    "declaration",
    "affidavit",
    "undertaking",
    "commercial_document",
    "technical_document",
    "authorization_document",
    "supporting_document",
}


class SupportingDocumentEvaluator(ComplianceRuleEvaluator):
    """
    Specialized compliance evaluator for document-presence and internal evidence requirements.
    """

    @property
    def evaluator_name(self) -> str:
        return "SupportingDocumentEvaluator"

    def supports(self, requirement: TenderRequirement) -> bool:
        """
        Determines if this evaluator handles the requirement.
        """
        category = (requirement.category or "").strip().upper()
        req_type = (requirement.requirement_type or "").strip().upper()

        if category in ("DOCUMENT", "DOCUMENTS", "SUPPORTING_DOCUMENT", "ATTACHMENT"):
            return True
        if req_type == "DOCUMENT":
            return True

        code_lower = (requirement.code or "").strip().lower()
        name_lower = (requirement.name or "").strip().lower()

        if code_lower.endswith("_required") and any(w in code_lower for w in ("doc", "document", "cert", "declaration", "letter", "affidavit")):
            return True

        tokens = set(
            code_lower.replace("_", " ").replace("-", " ").split()
            + name_lower.replace("_", " ").replace("-", " ").split()
        )

        return any(kw in tokens for kw in DOCUMENT_KEYWORDS)

    def evaluate(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> ComplianceRuleResult:
        """
        Evaluates document presence, processing health, and internal structural evidence.
        """
        code_upper = (requirement.code or "").strip().upper()
        name_lower = (requirement.name or "").strip().lower()
        operator = (requirement.operator or "EXISTS").upper()
        expected = requirement.expected_value if requirement.expected_value is not None else True
        is_mandatory = requirement.is_mandatory if requirement.is_mandatory is not None else True
        weight = requirement.weight

        # ---------------------------------------------------------------------
        # 1. Match Active Bid Documents
        # ---------------------------------------------------------------------
        matched_docs = []
        for doc in context.bid_documents:
            if not doc.is_active:
                continue

            # Direct link to requirement
            if doc.tender_requirement_id == requirement.id:
                matched_docs.append(doc)
                continue

            # Type keyword matching
            doc_type_upper = (doc.document_type or "").upper()
            doc_name_lower = (doc.document_name or "").lower()

            if "COMMERCIAL" in code_upper and "COMMERCIAL" in doc_type_upper:
                matched_docs.append(doc)
            elif "TECHNICAL" in code_upper and "TECHNICAL" in doc_type_upper:
                matched_docs.append(doc)
            elif "FINANCIAL" in code_upper and ("FINANCIAL" in doc_type_upper or "TURNOVER" in doc_type_upper):
                matched_docs.append(doc)
            elif "EXPERIENCE" in code_upper and ("EXPERIENCE" in doc_type_upper or "PROJECT" in doc_type_upper):
                matched_docs.append(doc)
            elif "DECLARATION" in code_upper and ("DECLARATION" in doc_type_upper or "UNDERTAKING" in doc_type_upper):
                matched_docs.append(doc)
            elif "OEM" in code_upper and ("OEM" in doc_type_upper or "AUTHORIZATION" in doc_type_upper):
                matched_docs.append(doc)
            elif "BIS" in code_upper and ("BIS" in doc_type_upper or "STANDARD" in doc_type_upper):
                matched_docs.append(doc)

        # ---------------------------------------------------------------------
        # 2. Handle Missing Document Case
        # ---------------------------------------------------------------------
        if not matched_docs:
            if not is_mandatory:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.NOT_APPLICABLE,
                    actual_value=None,
                    expected_value=expected,
                    operator=operator,
                    reason=f"Optional supporting document for '{requirement.name}' was not submitted (marked NOT_APPLICABLE).",
                    evidence={"is_mandatory": False, "requirement_code": requirement.code},
                    source_verification_ids=[],
                    is_mandatory=is_mandatory,
                    weight=weight,
                )

            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.FAIL,
                actual_value=None,
                expected_value=expected,
                operator=operator,
                reason=f"Mandatory supporting document '{requirement.name}' has not been uploaded.",
                evidence={"is_mandatory": True, "requirement_code": requirement.code},
                source_verification_ids=[],
                is_mandatory=is_mandatory,
                weight=weight,
            )

        primary_doc = matched_docs[0]
        evidence_dict: Dict[str, Any] = {
            "document_id": str(primary_doc.id),
            "document_name": primary_doc.document_name,
            "document_type": primary_doc.document_type,
            "file_size": primary_doc.file_size,
        }

        # ---------------------------------------------------------------------
        # 3. Check Document Processing & Extraction State
        # ---------------------------------------------------------------------
        proc = primary_doc.processing
        if proc:
            evidence_dict["processing_status"] = proc.processing_status
            evidence_dict["detected_document_type"] = proc.detected_document_type

            # Check if processing completely failed
            if proc.processing_status == "FAILED":
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.REVIEW,
                    actual_value=primary_doc.document_name,
                    expected_value=expected,
                    operator=operator,
                    reason=f"Uploaded document '{primary_doc.document_name}' failed processing: {proc.classification_reason or 'OCR parsing error'}. Manual review required.",
                    evidence=evidence_dict,
                    source_verification_ids=[],
                    is_mandatory=is_mandatory,
                    weight=weight,
                )

        # ---------------------------------------------------------------------
        # 4. Check Internal Supporting Verification Records if Linked
        # ---------------------------------------------------------------------
        source_ids: List[str] = []
        internal_v = None
        for v in context.verifications:
            if v.bid_document_id == primary_doc.id or v.verification_type == "SUPPORTING_DOCUMENT":
                internal_v = v
                source_ids.append(str(v.id))
                break

        if internal_v:
            evidence_dict["verification_id"] = str(internal_v.id)
            evidence_dict["verification_status"] = internal_v.verification_status
            evidence_dict["source_name"] = internal_v.source_name

            if internal_v.verification_status == VerificationStatus.NEEDS_REVIEW:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.REVIEW,
                    actual_value=primary_doc.document_name,
                    expected_value=expected,
                    operator=operator,
                    reason=f"Supporting document '{primary_doc.document_name}' internal evidence validation flag: {internal_v.error_message or 'Structure review needed'}.",
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    weight=weight,
                )

            if internal_v.verification_status == VerificationStatus.NOT_VERIFIED:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.FAIL if is_mandatory else ComplianceStatus.REVIEW,
                    actual_value=primary_doc.document_name,
                    expected_value=expected,
                    operator=operator,
                    reason=f"Supporting document '{primary_doc.document_name}' could not be verified by internal validator.",
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    weight=weight,
                )

        return ComplianceRuleResult(
            compliance_status=ComplianceStatus.PASS,
            actual_value=primary_doc.document_name,
            expected_value=expected,
            operator=operator,
            reason=f"Required supporting document '{primary_doc.document_name}' is uploaded and verified.",
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )
