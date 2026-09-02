"""
Generic Compliance Rule Evaluator for Part 6A
Evaluates standard scalar and presence requirements (BOOLEAN, NUMBER, TEXT, DATE, STATUS, DOCUMENT)
against verified bidder data, organization profile, or document presence.
"""

from typing import Any, Dict, List, Optional, Tuple

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
    VerificationRecord,
    VerificationStatus,
)


class GenericRuleEvaluator(ComplianceRuleEvaluator):
    """
    Standard rule evaluator for generic criteria.
    Maps tender requirements to corresponding verified claims, organization fields,
    or active document submissions.
    """

    @property
    def evaluator_name(self) -> str:
        return "GenericRuleEvaluator"

    def supports(self, requirement: TenderRequirement) -> bool:
        """
        Generic evaluator acts as default handler for standard scalar types.
        """
        return True

    def _find_matching_verifications(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> List[VerificationRecord]:
        """
        Finds any verification records corresponding to this requirement's code,
        category, or verification type.
        """
        code_norm = (requirement.code or "").strip().lower()
        cat_norm = (requirement.category or "").strip().lower()
        name_norm = (requirement.name or "").strip().lower()

        matched: List[VerificationRecord] = []

        for v in context.verifications:
            v_type_norm = (v.verification_type or "").strip().lower()
            v_claim_src = (v.claim_source or "").strip().lower()

            # Direct verification type match
            if v_type_norm in (code_norm, cat_norm) or v_type_norm.replace("_", "") in code_norm.replace("_", ""):
                matched.append(v)
                continue

            # Check keyword match
            if any(k in v_type_norm for k in ("gst", "pan", "udyam", "mca", "startup", "nsic", "epfo", "esic", "oem", "local_content", "bis", "blacklist", "debarment")):
                if any(k in code_norm or k in cat_norm or k in name_norm for k in (v_type_norm, v_claim_src)):
                    matched.append(v)
                    continue

            # Match on claim source field name
            if v_claim_src and (v_claim_src in code_norm or code_norm in v_claim_src):
                matched.append(v)

        return matched

    def _extract_actual_value_from_context(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
        verifications: List[VerificationRecord],
    ) -> Tuple[Optional[Any], Optional[str], List[str], Dict[str, Any]]:
        """
        Extracts the candidate actual value for comparison from verified records,
        organization profile, or document presence.
        """
        source_ids = [str(v.id) for v in verifications]
        evidence_dict: Dict[str, Any] = {}

        # 1. If we have verified records, extract from verified_payload or verified_value
        if verifications:
            primary_v = verifications[0]
            evidence_dict["verification_type"] = primary_v.verification_type
            evidence_dict["verification_status"] = primary_v.verification_status
            evidence_dict["source_name"] = primary_v.source_name
            evidence_dict["confidence"] = primary_v.confidence
            evidence_dict["match_status"] = primary_v.match_status

            v_payload = primary_v.response_payload or primary_v.evidence or {}
            req_type_upper = (requirement.requirement_type or "TEXT").upper()

            if isinstance(v_payload, dict):
                code_lower = requirement.code.lower()
                clean_code = code_lower.replace("req_", "").replace("rule_", "").replace("min_", "")

                # 1. Look for direct match on requirement code
                if code_lower in v_payload:
                    evidence_dict["extracted_field"] = code_lower
                    return v_payload[code_lower], None, source_ids, evidence_dict
                if clean_code in v_payload:
                    evidence_dict["extracted_field"] = clean_code
                    return v_payload[clean_code], None, source_ids, evidence_dict

                # 2. Key priority based on requirement type
                if req_type_upper in ("NUMBER", "NUMERIC", "FLOAT", "DECIMAL", "INTEGER", "PERCENTAGE", "CURRENCY"):
                    for key in (
                        "turnover",
                        "local_content_percentage",
                        "net_worth",
                        "experience_years",
                        "years",
                        "percentage",
                        "amount",
                        "value",
                    ):
                        if key in v_payload and v_payload[key] is not None:
                            evidence_dict["extracted_field"] = key
                            return v_payload[key], None, source_ids, evidence_dict
                elif req_type_upper in ("DATE", "DATETIME"):
                    for key in ("valid_until", "valid_to", "expiry_date", "valid_from", "registration_date", "issue_date"):
                        if key in v_payload and v_payload[key] is not None:
                            evidence_dict["extracted_field"] = key
                            return v_payload[key], None, source_ids, evidence_dict
                elif req_type_upper in ("STATUS", "BOOLEAN"):
                    for key in ("status", "registry_status", "registration_status", "authorization_status"):
                        if key in v_payload and v_payload[key] is not None:
                            evidence_dict["extracted_field"] = key
                            return v_payload[key], None, source_ids, evidence_dict

                # 3. Keyword search in payload keys
                for k, v in v_payload.items():
                    if k in clean_code or clean_code in k:
                        evidence_dict["extracted_field"] = k
                        return v, None, source_ids, evidence_dict

            # Fallback to verified_value or claimed_value
            actual = primary_v.verified_value if primary_v.verified_value is not None else primary_v.claimed_value
            return actual, None, source_ids, evidence_dict

        # 2. Check Document Presence if requirement_type == DOCUMENT or category == DOCUMENT
        req_type = (requirement.requirement_type or "").upper()
        req_cat = (requirement.category or "").upper()
        if req_type == "DOCUMENT" or req_cat == "DOCUMENT":
            code_lower = requirement.code.lower()
            matching_docs = [
                d for d in context.bid_documents
                if d.document_type.lower() in code_lower
                or code_lower in d.document_type.lower()
                or (d.tender_requirement_id and d.tender_requirement_id == requirement.id)
            ]
            if matching_docs:
                evidence_dict["matching_documents"] = [d.document_name for d in matching_docs]
                return True, "DOCUMENT_PRESENT", source_ids, evidence_dict
            return False, "DOCUMENT_MISSING", source_ids, evidence_dict

        # 3. Check Organization profile attributes
        org = context.bidder_organization
        if org:
            code_clean = requirement.code.lower().replace("req_", "").replace("rule_", "")
            if hasattr(org, code_clean):
                return getattr(org, code_clean), "ORGANIZATION_PROFILE", source_ids, evidence_dict
            if hasattr(org, requirement.code):
                return getattr(org, requirement.code), "ORGANIZATION_PROFILE", source_ids, evidence_dict

        return None, "NO_DATA_SOURCE", source_ids, evidence_dict

    def evaluate(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> ComplianceRuleResult:
        """
        Executes generic rule evaluation.
        """
        matched_v = self._find_matching_verifications(requirement, context)

        # 1. Prerequisite Verification Status Handling
        if matched_v:
            # Check for non-terminal / failure statuses
            unavail = [v for v in matched_v if v.verification_status == VerificationStatus.UNAVAILABLE]
            if unavail:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.REVIEW,
                    actual_value=unavail[0].verification_status,
                    expected_value=requirement.expected_value,
                    operator=requirement.operator,
                    reason=(
                        f"External verification source ({unavail[0].source_name}) is temporarily unavailable. "
                        "Requirement is placed under review without penalizing bidder."
                    ),
                    evidence={"source_error": unavail[0].evidence, "verification_type": unavail[0].verification_type},
                    source_verification_ids=[str(v.id) for v in matched_v],
                    is_mandatory=requirement.is_mandatory,
                    weight=requirement.weight,
                )

            pending = [v for v in matched_v if v.verification_status in (VerificationStatus.PENDING, VerificationStatus.IN_PROGRESS)]
            if pending:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.PENDING,
                    actual_value=pending[0].verification_status,
                    expected_value=requirement.expected_value,
                    operator=requirement.operator,
                    reason=f"Verification for {pending[0].verification_type} is still in progress.",
                    evidence={"verification_type": pending[0].verification_type},
                    source_verification_ids=[str(v.id) for v in matched_v],
                    is_mandatory=requirement.is_mandatory,
                    weight=requirement.weight,
                )

            needs_review = [v for v in matched_v if v.verification_status == VerificationStatus.NEEDS_REVIEW]
            if needs_review:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.REVIEW,
                    actual_value=needs_review[0].verified_value,
                    expected_value=requirement.expected_value,
                    operator=requirement.operator,
                    reason=(
                        f"Underlying verification for {needs_review[0].verification_type} requires manual review "
                        f"(Match Status: {needs_review[0].match_status}, Confidence: {needs_review[0].confidence})."
                    ),
                    evidence=needs_review[0].evidence,
                    source_verification_ids=[str(v.id) for v in matched_v],
                    is_mandatory=requirement.is_mandatory,
                    weight=requirement.weight,
                )

            not_verified = [v for v in matched_v if v.verification_status == VerificationStatus.NOT_VERIFIED]
            if not_verified and requirement.operator not in (ComplianceOperator.NOT_EXISTS,):
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.FAIL,
                    actual_value="NOT_VERIFIED",
                    expected_value=requirement.expected_value,
                    operator=requirement.operator,
                    reason=f"Required statutory/technical credential ({not_verified[0].verification_type}) could not be verified in the authoritative registry.",
                    evidence=not_verified[0].evidence,
                    source_verification_ids=[str(v.id) for v in matched_v],
                    is_mandatory=requirement.is_mandatory,
                    weight=requirement.weight,
                )

        # 2. Extract actual candidate value
        actual_val, src_type, src_ids, evidence_info = self._extract_actual_value_from_context(
            requirement, context, matched_v
        )

        # Handle missing data
        if actual_val is None:
            if requirement.operator in (ComplianceOperator.EXISTS, ComplianceOperator.NOT_EXISTS):
                passed, err = evaluate_generic_operator(
                    actual_val, requirement.expected_value, requirement.operator, requirement.requirement_type
                )
                status = ComplianceStatus.PASS if passed else ComplianceStatus.FAIL
                reason = "Presence condition evaluated on empty/absent data."
                return ComplianceRuleResult(
                    compliance_status=status,
                    actual_value=None,
                    expected_value=requirement.expected_value,
                    operator=requirement.operator,
                    reason=reason,
                    evidence=evidence_info,
                    source_verification_ids=src_ids,
                    is_mandatory=requirement.is_mandatory,
                    weight=requirement.weight,
                )

            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=requirement.expected_value,
                operator=requirement.operator,
                reason="No matching verified evidence, document, or bidder attribute found for this requirement.",
                evidence=evidence_info,
                source_verification_ids=src_ids,
                is_mandatory=requirement.is_mandatory,
                weight=requirement.weight,
            )

        # 3. Evaluate operator
        passed, err_detail = evaluate_generic_operator(
            actual=actual_val,
            expected=requirement.expected_value,
            operator=requirement.operator,
            requirement_type=requirement.requirement_type,
        )

        if err_detail:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=str(actual_val),
                expected_value=requirement.expected_value,
                operator=requirement.operator,
                reason=f"Evaluation could not complete deterministically: {err_detail}",
                evidence=evidence_info,
                source_verification_ids=src_ids,
                is_mandatory=requirement.is_mandatory,
                weight=requirement.weight,
            )

        final_status = ComplianceStatus.PASS if passed else ComplianceStatus.FAIL
        if passed:
            reason = f"Actual value ('{actual_val}') satisfies requirement condition ({requirement.operator} '{requirement.expected_value}')."
        else:
            reason = f"Actual value ('{actual_val}') does not satisfy requirement condition ({requirement.operator} '{requirement.expected_value}')."

        return ComplianceRuleResult(
            compliance_status=final_status,
            actual_value=actual_val,
            expected_value=requirement.expected_value,
            operator=requirement.operator,
            reason=reason,
            evidence=evidence_info,
            source_verification_ids=src_ids,
            is_mandatory=requirement.is_mandatory,
            weight=requirement.weight,
        )
