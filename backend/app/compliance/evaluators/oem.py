"""
OEM Authorization Compliance Rule Evaluator for Part 6D
Evaluates OEM Authorization requirements (Presence, Authorized Entity Match, Validity Date,
and Product Scope Match) against verified Part 5 OEM records and active document extractions.
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

OEM_KEYWORDS = {
    "oem",
    "oem_authorization",
    "maf",
    "manufacturer_authorization",
    "oem_auth",
    "oem_certificate",
    "oem_letter",
}


class OEMComplianceEvaluator(ComplianceRuleEvaluator):
    """
    Specialized compliance evaluator for OEM Authorization requirements.
    """

    @property
    def evaluator_name(self) -> str:
        return "OEMComplianceEvaluator"

    def supports(self, requirement: TenderRequirement) -> bool:
        """
        Determines if this evaluator handles the requirement.
        """
        category = (requirement.category or "").strip().upper()
        if category in ("OEM", "OEM_AUTHORIZATION", "MANUFACTURER_AUTHORIZATION"):
            return True

        code_lower = (requirement.code or "").strip().lower()
        name_lower = (requirement.name or "").strip().lower()

        tokens = set(
            code_lower.replace("_", " ").replace("-", " ").split()
            + name_lower.replace("_", " ").replace("-", " ").split()
        )

        return any(kw in tokens for kw in OEM_KEYWORDS)

    def evaluate(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> ComplianceRuleResult:
        """
        Evaluates OEM Authorization criteria against verified Part 5 records.
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
        # 2. Extract OEM Verification Records
        # ---------------------------------------------------------------------
        oem_data, primary_v, source_ids, evidence_dict, issue_status, issue_reason = self._extract_oem_data(
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
        # 3. Authorized Entity Match Rule
        # ---------------------------------------------------------------------
        if "ENTITY" in code_upper or "BIDDER" in code_upper or "entity" in name_lower:
            return self._evaluate_authorized_entity(
                requirement=requirement,
                primary_v=primary_v,
                oem_data=oem_data,
                context=context,
                expected=expected,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 4. OEM Authorization Validity Rule
        # ---------------------------------------------------------------------
        if "VALID" in code_upper or "VALIDITY" in code_upper or "EXPIRY" in code_upper or "valid" in name_lower:
            return self._evaluate_oem_validity(
                requirement=requirement,
                primary_v=primary_v,
                oem_data=oem_data,
                context=context,
                expected=expected,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 5. Product / Scope Match Rule
        # ---------------------------------------------------------------------
        if "SCOPE" in code_upper or "PRODUCT" in code_upper or "scope" in name_lower:
            return self._evaluate_product_scope(
                requirement=requirement,
                primary_v=primary_v,
                oem_data=oem_data,
                expected=expected,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 6. General OEM Authorization Required Rule
        # ---------------------------------------------------------------------
        return self._evaluate_general_authorization(
            requirement=requirement,
            primary_v=primary_v,
            oem_data=oem_data,
            context=context,
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
        """Evaluates upload presence of OEM authorization document."""
        matching_docs = [
            d for d in context.bid_documents
            if d.is_active and (
                "OEM" in (d.document_type or "").upper()
                or "AUTHORIZATION" in (d.document_type or "").upper()
                or "MAF" in (d.document_type or "").upper()
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
                reason=f"OEM authorization document '{doc.document_name}' is uploaded and verified.",
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
            reason="Required OEM authorization document is missing.",
            evidence={"requirement_code": requirement.code},
            source_verification_ids=[],
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _extract_oem_data(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
        is_mandatory: bool,
    ) -> Tuple[Dict[str, Any], Optional[VerificationRecord], List[str], Dict[str, Any], Optional[str], Optional[str]]:
        """
        Extracts verified OEM data and handles prerequisite verification states.
        """
        source_ids: List[str] = []
        evidence_dict: Dict[str, Any] = {}

        # 1. Search Part 5 OEM Verification Records
        oem_verifications = [
            v for v in context.verifications
            if v.verification_type == "OEM_AUTHORIZATION"
            or "oem" in (v.claim_source or "").lower()
            or "authorization" in (v.claim_source or "").lower()
        ]

        if not oem_verifications:
            # Fallback to structured document extraction if verified record not created yet
            for doc in context.bid_documents:
                if not doc.is_active:
                    continue
                proc = doc.processing
                if proc and proc.extracted_data and isinstance(proc.extracted_data, dict):
                    ext = proc.extracted_data
                    if any(k in ext for k in ("oem_name", "authorization_number", "authorized_entity", "product_scope")):
                        evidence_dict["extracted_from_document"] = doc.document_name
                        return ext, None, [], evidence_dict, None, None

            return {}, None, [], evidence_dict, (
                ComplianceStatus.FAIL if is_mandatory else ComplianceStatus.PENDING
            ), f"No OEM authorization record or document evidence found for requirement '{requirement.code}'."

        primary_v = oem_verifications[0]
        source_ids.append(str(primary_v.id))
        evidence_dict["verification_id"] = str(primary_v.id)
        evidence_dict["verification_status"] = primary_v.verification_status
        evidence_dict["source_name"] = primary_v.source_name
        evidence_dict["source_type"] = primary_v.source_type

        # Prerequisite Status Policy
        if primary_v.verification_status in (VerificationStatus.UNAVAILABLE, "FAILED"):
            return {}, primary_v, source_ids, evidence_dict, ComplianceStatus.REVIEW, (
                f"External verification source ({primary_v.source_name}) is temporarily unavailable. "
                f"Requirement is placed under review without penalizing bidder."
            )

        if primary_v.verification_status == VerificationStatus.NEEDS_REVIEW:
            return {}, primary_v, source_ids, evidence_dict, ComplianceStatus.REVIEW, (
                f"OEM authorization verification requires review: {primary_v.error_message or 'Entity or scope review flag'}"
            )

        if primary_v.verification_status == VerificationStatus.NOT_VERIFIED:
            return {}, primary_v, source_ids, evidence_dict, ComplianceStatus.FAIL, (
                f"OEM authorization could not be authenticated in authoritative records ({primary_v.source_name})."
            )

        # Verified payload
        v_payload = primary_v.response_payload or primary_v.evidence or {}
        if not isinstance(v_payload, dict):
            v_payload = {}

        return v_payload, primary_v, source_ids, evidence_dict, None, None

    def _evaluate_authorized_entity(
        self,
        requirement: TenderRequirement,
        primary_v: Optional[VerificationRecord],
        oem_data: Dict[str, Any],
        context: ComplianceContext,
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates whether OEM authorization authorizes the specific bidding organization.
        """
        auth_entity = oem_data.get("authorized_entity")
        target_bidder = expected or (context.bidder_organization.name if context.bidder_organization else None)

        if not auth_entity:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=target_bidder,
                operator=operator,
                reason="Authorized entity is missing in the OEM verification payload.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        evidence_dict["authorized_entity"] = auth_entity
        evidence_dict["target_bidder"] = target_bidder

        if primary_v and primary_v.match_status == VerificationMatchStatus.MISMATCH:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.FAIL,
                actual_value=auth_entity,
                expected_value=target_bidder,
                operator=operator,
                reason=f"OEM Authorization was issued to '{auth_entity}', which does not match bidder entity '{target_bidder}'.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        comp_ok, err_msg = compare_strings(auth_entity, target_bidder, operator)
        status = ComplianceStatus.PASS if comp_ok else (ComplianceStatus.FAIL if is_mandatory else ComplianceStatus.REVIEW)
        reason = (
            f"OEM Authorization correctly authorizes the bidder entity ('{auth_entity}')."
            if comp_ok
            else f"OEM Authorization issued to '{auth_entity}' does not match requirement target '{target_bidder}'."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=str(auth_entity),
            expected_value=str(target_bidder),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_oem_validity(
        self,
        requirement: TenderRequirement,
        primary_v: Optional[VerificationRecord],
        oem_data: Dict[str, Any],
        context: ComplianceContext,
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates whether OEM authorization remains valid through the required tender deadline.
        """
        valid_until_raw = oem_data.get("valid_until") or oem_data.get("expiry_date")
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
                reason="OEM authorization expiry date (valid_until) is missing or unparseable. Review required.",
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
                reason=f"OEM authorization is valid until {actual_date}.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        evidence_dict["valid_until"] = str(actual_date)
        evidence_dict["target_deadline"] = str(target_date)

        comp_ok, err_msg = compare_dates(actual_date, target_date, operator if operator != "EQUALS" else ComplianceOperator.GREATER_THAN_OR_EQUAL)
        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"OEM authorization validity ({actual_date}) remains valid through required milestone ({target_date})."
            if comp_ok
            else f"OEM authorization expired on {actual_date}, before the required tender milestone date ({target_date})."
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

    def _evaluate_product_scope(
        self,
        requirement: TenderRequirement,
        primary_v: Optional[VerificationRecord],
        oem_data: Dict[str, Any],
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates product or item scope coverage of OEM authorization.
        """
        actual_scope = oem_data.get("product_scope") or oem_data.get("product_name") or oem_data.get("scope")
        if not actual_scope:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=expected,
                operator=operator,
                reason="Product scope is missing from the OEM authorization verification payload.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        evidence_dict["actual_scope"] = actual_scope
        evidence_dict["expected_scope"] = expected

        if primary_v and primary_v.match_status == VerificationMatchStatus.PARTIAL_MATCH:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=actual_scope,
                expected_value=expected,
                operator=operator,
                reason=f"OEM Authorization product scope ('{actual_scope}') only partially matches required scope '{expected}'. Manual review required.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        comp_ok, err_msg = compare_strings(actual_scope, expected, operator)
        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"OEM authorization product scope ('{actual_scope}') satisfies requirement condition ({operator} '{expected}')."
            if comp_ok
            else f"OEM authorization product scope ('{actual_scope}') does not match required scope '{expected}'."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=str(actual_scope),
            expected_value=str(expected),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_general_authorization(
        self,
        requirement: TenderRequirement,
        primary_v: Optional[VerificationRecord],
        oem_data: Dict[str, Any],
        context: ComplianceContext,
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        General OEM authorization evaluation validating issuer authenticity and status.
        """
        auth_status = str(oem_data.get("authorization_status") or "VALID").upper()
        oem_name = oem_data.get("oem_name") or "OEM"

        if auth_status in ("EXPIRED", "REVOKED", "CANCELLED"):
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.FAIL,
                actual_value=auth_status,
                expected_value=expected or "VALID",
                operator=operator,
                reason=f"OEM authorization from {oem_name} is in '{auth_status}' state in authoritative records.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        return ComplianceRuleResult(
            compliance_status=ComplianceStatus.PASS,
            actual_value=auth_status,
            expected_value=expected or "VALID",
            operator=operator,
            reason=f"OEM authorization from {oem_name} is verified and in '{auth_status}' state.",
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )
