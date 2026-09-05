"""
Statutory & Registration Compliance Rule Evaluator for Part 6B
Evaluates statutory and registration tender criteria (GST, PAN, Udyam/MSME, MCA,
Startup India, NSIC, EPFO, ESIC) against verified Part 5 records.
"""

from datetime import date, datetime
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.compliance.evaluators.base import ComplianceRuleEvaluator
from app.compliance.operators import compare_dates, evaluate_generic_operator
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

# Standard statutory keywords mapped to verification types
STATUTORY_KEYWORD_MAPPING = {
    "gst": "GST",
    "gstin": "GST",
    "pan": "PAN",
    "udyam": "UDYAM",
    "msme": "UDYAM",
    "mca": "MCA",
    "cin": "MCA",
    "llpin": "MCA",
    "company_status": "MCA",
    "startup": "STARTUP_INDIA",
    "dpiit": "STARTUP_INDIA",
    "nsic": "NSIC",
    "epfo": "EPFO",
    "pf": "EPFO",
    "esic": "ESIC",
    "esi": "ESIC",
}


class StatutoryRuleEvaluator(ComplianceRuleEvaluator):
    """
    Specialized compliance evaluator for statutory and registration rules.
    Handles GST, PAN, Udyam/MSME, MCA, Startup India, NSIC, EPFO, and ESIC.
    """

    @property
    def evaluator_name(self) -> str:
        return "StatutoryRuleEvaluator"

    def supports(self, requirement: TenderRequirement) -> bool:
        """
        Determines whether this evaluator supports the given tender requirement.
        """
        category = (requirement.category or "").strip().upper()
        if category in ("CONSISTENCY", "CROSS_DOCUMENT", "INTEGRITY", "BLACKLISTING", "DEBARMENT", "EXCLUSION"):
            return False

        code_lower = (requirement.code or "").strip().lower()
        if "consistency" in code_lower or "cross_doc" in code_lower or "blacklist" in code_lower or "debar" in code_lower:
            return False

        if category in ("STATUTORY", "REGISTRATION", "STATUTORY_LEGAL"):
            return True
        return self.resolve_verification_type(requirement) is not None

    def resolve_verification_type(self, requirement: TenderRequirement) -> Optional[str]:
        """
        Resolves the canonical Part 5 verification type for this statutory requirement.
        Uses tokenized word-boundary matching to prevent substring collisions (e.g. 'pan' in 'company').
        """
        # 1. Direct Category Match
        cat_upper = (requirement.category or "").strip().upper()
        if cat_upper in ("GST", "PAN", "UDYAM", "MCA", "STARTUP_INDIA", "NSIC", "EPFO", "ESIC"):
            return cat_upper

        code_lower = (requirement.code or "").strip().lower()
        name_lower = (requirement.name or "").strip().lower()

        # Tokenize code and name by non-alphanumeric separators
        tokens = set(
            code_lower.replace("_", " ").replace("-", " ").replace("/", " ").split()
            + name_lower.replace("_", " ").replace("-", " ").replace("/", " ").split()
        )

        # 2. Priority Token Checks
        if "gst" in tokens or "gstin" in tokens or "gst_status" in code_lower:
            return "GST"
        if "mca" in tokens or "cin" in tokens or "llpin" in tokens or "incorporation" in tokens or "company" in tokens:
            return "MCA"
        if "udyam" in tokens or "msme" in tokens:
            return "UDYAM"
        if "startup" in tokens or "dpiit" in tokens or "dipp" in tokens:
            return "STARTUP_INDIA"
        if "nsic" in tokens:
            return "NSIC"
        if "epfo" in tokens or "epf" in tokens or "pf" in tokens or "provident" in tokens:
            return "EPFO"
        if "esic" in tokens or "esi" in tokens:
            return "ESIC"
        if "pan" in tokens or "pancard" in tokens:
            return "PAN"

        return None

    def _find_matching_verifications(
        self,
        v_type: Optional[str],
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> List[VerificationRecord]:
        """
        Retrieves active, non-superseded verification records corresponding to the resolved type.
        """
        if not v_type:
            return []

        # Try context pre-indexed dictionary
        records = context.verifications_by_type.get(v_type, [])
        if records:
            return records

        # Filter from global verifications list
        v_type_lower = v_type.lower()
        matched = []
        for v in context.verifications:
            if (v.verification_type or "").strip().lower() == v_type_lower:
                matched.append(v)

        return matched

    def evaluate(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> ComplianceRuleResult:
        """
        Executes statutory compliance evaluation for a single requirement.
        """
        v_type = self.resolve_verification_type(requirement)
        code_upper = (requirement.code or "").strip().upper()
        req_type = (requirement.requirement_type or "TEXT").upper()
        operator = (requirement.operator or "EQUALS").upper()
        expected = requirement.expected_value
        is_mandatory = requirement.is_mandatory if requirement.is_mandatory is not None else True
        weight = requirement.weight

        # ---------------------------------------------------------------------
        # 1. Applicability Check (e.g., MCA for Proprietorship / Partnerships)
        # ---------------------------------------------------------------------
        if v_type == "MCA":
            org = context.bidder_organization
            if org and org.organization_type:
                struct_upper = org.organization_type.upper()
                if "PROPRIETOR" in struct_upper or "INDIVIDUAL" in struct_upper:
                    # Check if requirement is explicitly only for companies/LLPs
                    if "COMPANY" in code_upper or "LLP" in code_upper or not is_mandatory:
                        return ComplianceRuleResult(
                            compliance_status=ComplianceStatus.NOT_APPLICABLE,
                            actual_value=org.organization_type,
                            expected_value=expected,
                            operator=operator,
                            reason=f"MCA registration is NOT APPLICABLE for organization type: '{org.organization_type}'.",
                            evidence={"organization_type": org.organization_type, "verification_type": "MCA"},
                            source_verification_ids=[],
                            is_mandatory=is_mandatory,
                            weight=weight,
                        )

        # ---------------------------------------------------------------------
        # 2. Find Associated Verification Records
        # ---------------------------------------------------------------------
        matching_verifications = self._find_matching_verifications(v_type, requirement, context)
        source_ids = [str(v.id) for v in matching_verifications]

        if not matching_verifications:
            # No verification record exists
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.PENDING if is_mandatory else ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=expected,
                operator=operator,
                reason=f"No active verification record found for '{v_type or requirement.code}'. Verification has not been executed yet.",
                evidence={"verification_type": v_type, "requirement_code": requirement.code},
                source_verification_ids=[],
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # Use the latest active verification record
        primary_v = matching_verifications[0]
        v_status = primary_v.verification_status
        v_source_name = primary_v.source_name or "Official Registry"
        v_source_type = primary_v.source_type or "EXTERNAL"
        v_match_status = primary_v.match_status
        v_payload = primary_v.response_payload or primary_v.evidence or {}
        if not isinstance(v_payload, dict):
            v_payload = {}

        evidence_dict: Dict[str, Any] = {
            "verification_record_id": str(primary_v.id),
            "verification_type": primary_v.verification_type,
            "verification_status": v_status,
            "source_name": v_source_name,
            "source_type": v_source_type,
            "match_status": v_match_status,
            "confidence": primary_v.confidence,
        }

        # ---------------------------------------------------------------------
        # 3. Verification Prerequisite Status Handling
        # ---------------------------------------------------------------------
        if v_status in (VerificationStatus.UNAVAILABLE, "FAILED"):
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=expected,
                operator=operator,
                reason=(
                    f"External verification source ({v_source_name}) is temporarily unavailable. "
                    f"Requirement is placed under review without penalizing bidder."
                ),
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                review_required=True,
                review_type="SOURCE_UNAVAILABLE",
                weight=weight,
            )

        if v_status == VerificationStatus.NEEDS_REVIEW:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=primary_v.verified_value or primary_v.claimed_value,
                expected_value=expected,
                operator=operator,
                reason=(
                    f"{v_type} verification requires manual review: "
                    f"{primary_v.error_message or 'Holder name mismatch or low scan confidence flag.'}"
                ),
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                review_required=True,
                review_type="VERIFICATION_UNCERTAIN",
                weight=weight,
            )

        if v_status == VerificationStatus.NOT_VERIFIED:
            reason = self._build_verification_failure_reason(
                v_type=v_type,
                requirement=requirement,
                primary_v=primary_v,
                v_payload=v_payload,
                v_source_name=v_source_name,
            )
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.FAIL,
                actual_value="NOT_VERIFIED",
                expected_value=expected,
                operator=operator,
                reason=reason,
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        if v_status != VerificationStatus.VERIFIED:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.PENDING,
                actual_value=primary_v.verified_value,
                expected_value=expected,
                operator=operator,
                reason=f"{v_type} verification is currently in '{v_status}' state.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 4. Extract Actual Value & Registry Status by Domain
        # ---------------------------------------------------------------------
        actual_val, extracted_field = self._extract_statutory_value(
            v_type=v_type,
            requirement=requirement,
            primary_v=primary_v,
            v_payload=v_payload,
            context=context,
        )
        evidence_dict["extracted_field"] = extracted_field
        evidence_dict["actual_value_evaluated"] = actual_val

        # ---------------------------------------------------------------------
        # Special Check: GST Registration Presence
        # A GST_REGISTRATION BOOLEAN requirement is satisfied when GST
        # verification succeeds and the registration status is ACTIVE/VALID,
        # rather than comparing the GSTIN string to True.
        # ---------------------------------------------------------------------
        if v_type == "GST" and code_upper == "GST_REGISTRATION" and req_type in ("BOOLEAN", "BOOL"):
            expected_bool = str(expected).strip().lower() in (
                "true",
                "yes",
                "1",
                "y",
                "active",
                "valid",
                "verified",
            )

            registration_status = str(
                v_payload.get("registration_status")
                or v_payload.get("gst_status")
                or v_payload.get("status")
                or "UNKNOWN"
            ).strip().upper()

            actual_bool = (
                v_status == VerificationStatus.VERIFIED
                and registration_status in ("ACTIVE", "VALID")
            )

            evidence_dict["extracted_field"] = "registration_status"
            evidence_dict["actual_value_evaluated"] = actual_bool
            evidence_dict["gstin"] = primary_v.verified_value or primary_v.claimed_value
            evidence_dict["registration_status"] = registration_status

            if actual_bool == expected_bool:
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.PASS,
                    actual_value=actual_bool,
                    expected_value=expected_bool,
                    operator=operator,
                    reason=(
                        f"GST registration is verified as valid and active by "
                        f"{v_source_name}. GSTIN: "
                        f"'{primary_v.verified_value or primary_v.claimed_value}'."
                    ),
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    weight=weight,
                )

            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.FAIL,
                actual_value=actual_bool,
                expected_value=expected_bool,
                operator=operator,
                reason=(
                    f"GST registration verification result ({actual_bool}) "
                    f"does not satisfy required value ({expected_bool})."
                ),
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )
        # Special Check: PAN Holder Name Mismatch
        if v_type == "PAN" and v_match_status == VerificationMatchStatus.MISMATCH:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=actual_val,
                expected_value=expected,
                operator=operator,
                reason="PAN verification was source-confirmed, but bidder name does not perfectly match registered PAN cardholder name.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # If expected is not specified for NSIC validity, fallback to tender deadline
        if expected is None and v_type == "NSIC" and "VALID" in code_upper and context.tender:
            expected = context.tender.submission_end_date or getattr(context.tender, 'submission_deadline', None)

        # ---------------------------------------------------------------------
        # 5. Requirement Configuration Validation
        # ---------------------------------------------------------------------
        if operator not in (ComplianceOperator.EXISTS, ComplianceOperator.NOT_EXISTS) and expected is None:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=actual_val,
                expected_value=None,
                operator=operator,
                reason=f"Invalid tender requirement configuration: expected_value is missing for rule '{requirement.code}'.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 6. Evaluate Rule Condition using Operators
        # ---------------------------------------------------------------------
        # Special NSIC Validity Rule vs Tender Submission Deadline
        if v_type == "NSIC" and "VALID" in code_upper and (req_type in ("DATE", "DATETIME") or isinstance(actual_val, (date, datetime, str))):
            target_date = expected
            if target_date is None and context.tender:
                target_date = context.tender.submission_end_date or getattr(context.tender, 'submission_deadline', None)

            if target_date is not None:
                comp_ok, err_msg = compare_dates(actual_val, target_date, operator if operator != "EQUALS" else ComplianceOperator.GREATER_THAN_OR_EQUAL)
                if err_msg:
                    return ComplianceRuleResult(
                        compliance_status=ComplianceStatus.REVIEW,
                        actual_value=actual_val,
                        expected_value=target_date,
                        operator=operator,
                        reason=f"Date comparison failed: {err_msg}",
                        evidence=evidence_dict,
                        source_verification_ids=source_ids,
                        is_mandatory=is_mandatory,
                        weight=weight,
                    )
                status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
                reason = (
                    f"NSIC certificate validity ({actual_val}) is valid through tender milestone ({target_date})."
                    if comp_ok
                    else f"NSIC certificate validity ({actual_val}) has expired or is invalid for tender deadline ({target_date})."
                )
                return ComplianceRuleResult(
                    compliance_status=status,
                    actual_value=str(actual_val),
                    expected_value=str(target_date),
                    operator=operator,
                    reason=reason,
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    weight=weight,
                )

        # General Operator Evaluation
        comp_ok, err_msg = evaluate_generic_operator(
            actual=actual_val,
            expected=expected,
            operator=operator,
            requirement_type=req_type,
        )

        if err_msg:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=actual_val,
                expected_value=expected,
                operator=operator,
                reason=f"Evaluation could not complete deterministically: {err_msg}",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = self._build_human_reason(
            v_type=v_type,
            requirement=requirement,
            actual_val=actual_val,
            expected_val=expected,
            operator=operator,
            passed=comp_ok,
            v_source_name=v_source_name,
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=actual_val,
            expected_value=expected,
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _extract_statutory_value(
        self,
        v_type: Optional[str],
        requirement: TenderRequirement,
        primary_v: VerificationRecord,
        v_payload: Dict[str, Any],
        context: ComplianceContext,
    ) -> Tuple[Any, str]:
        """
        Extracts and normalizes the target statutory field for evaluation.
        """
        code_upper = (requirement.code or "").strip().upper()
        req_type = (requirement.requirement_type or "TEXT").upper()

        if v_type == "GST":
            expected_str = str(requirement.expected_value or "").strip().upper()
            # Status check
            if "STATUS" in code_upper or expected_str in ("ACTIVE", "VALID", "CANCELLED", "SUSPENDED", "INACTIVE"):
                status_val = v_payload.get("status") or v_payload.get("registry_status") or v_payload.get("gst_status") or primary_v.verified_value or "ACTIVE"
                return str(status_val).upper() if status_val else "UNKNOWN", "status"
            # Registration presence check
            return primary_v.verified_value or v_payload.get("gstin") or "ACTIVE", "gstin"

        elif v_type == "PAN":
            expected_str = str(requirement.expected_value or "").strip().upper()
            if "STATUS" in code_upper or expected_str in ("VALID", "ACTIVE", "INVALID", "INOPERATIVE", "CANCELLED"):
                status_val = v_payload.get("status") or v_payload.get("pan_status") or primary_v.verified_value or "VALID"
                return str(status_val).upper() if status_val else "VALID", "status"
            return primary_v.verified_value or v_payload.get("pan") or "VALID", "pan"

        elif v_type == "UDYAM":
            # MSME Classification check
            if "CLASSIFICATION" in code_upper or "CATEGORY" in code_upper or "TYPE" in code_upper:
                class_val = (
                    v_payload.get("enterprise_type")
                    or v_payload.get("classification")
                    or v_payload.get("category")
                    or primary_v.verified_value
                )
                return str(class_val).upper() if class_val else "UNKNOWN", "enterprise_type"
            # Status check
            if "STATUS" in code_upper:
                status_val = v_payload.get("status") or primary_v.verified_value
                return str(status_val).upper() if status_val else "ACTIVE", "status"
            # General MSME registration
            return v_payload.get("status") or primary_v.verified_value or "ACTIVE", "udyam_registration"

        elif v_type == "MCA":
            if "STATUS" in code_upper or "COMPANY_STATUS" in code_upper:
                status_val = v_payload.get("company_status") or v_payload.get("status") or primary_v.verified_value
                return str(status_val).upper() if status_val else "UNKNOWN", "company_status"
            return v_payload.get("company_status") or primary_v.verified_value or "ACTIVE", "mca_registration"

        elif v_type == "STARTUP_INDIA":
            if "STATUS" in code_upper:
                status_val = v_payload.get("recognition_status") or v_payload.get("status") or primary_v.verified_value
                return str(status_val).upper() if status_val else "UNKNOWN", "recognition_status"
            rec_status = v_payload.get("recognition_status") or v_payload.get("status") or primary_v.verified_value
            return str(rec_status).upper() if rec_status else "RECOGNIZED", "recognition_status"

        elif v_type == "NSIC":
            if "VALID" in code_upper or "EXPIR" in code_upper or req_type in ("DATE", "DATETIME"):
                val_until = v_payload.get("valid_until") or v_payload.get("expiry_date") or primary_v.verified_value
                return val_until, "valid_until"
            return v_payload.get("status") or primary_v.verified_value or "ACTIVE", "status"

        elif v_type in ("EPFO", "ESIC"):
            if "STATUS" in code_upper:
                status_val = v_payload.get("status") or primary_v.verified_value
                return str(status_val).upper() if status_val else "ACTIVE", "status"
            return v_payload.get("status") or primary_v.verified_value or "ACTIVE", "status"

        # General fallback
        return primary_v.verified_value or primary_v.claimed_value or "ACTIVE", "verified_value"

    def _build_verification_failure_reason(
        self,
        v_type: Optional[str],
        requirement: TenderRequirement,
        primary_v: VerificationRecord,
        v_payload: Dict[str, Any],
        v_source_name: str,
    ) -> str:
        """
        Prefer the verifier's bidder-specific failure detail over a generic
        statutory compliance sentence.
        """
        evidence = primary_v.evidence if isinstance(primary_v.evidence, dict) else {}
        claim = primary_v.claimed_value

        for message in (
            primary_v.error_message,
            evidence.get("reason"),
            evidence.get("details"),
            v_payload.get("reason") if isinstance(v_payload, dict) else None,
            v_payload.get("details") if isinstance(v_payload, dict) else None,
            v_payload.get("error_message") if isinstance(v_payload, dict) else None,
        ):
            if message:
                prefix = f"{v_type or requirement.code} verification failed"
                claim_text = f" for bidder claim '{claim}'" if claim else ""
                return f"{prefix}{claim_text}: {message}"

        return (
            f"{v_type or requirement.code} statutory credential"
            f"{f' ({claim})' if claim else ''} could not be verified in authoritative source ({v_source_name})."
        )

    def _build_human_reason(
        self,
        v_type: Optional[str],
        requirement: TenderRequirement,
        actual_val: Any,
        expected_val: Any,
        operator: str,
        passed: bool,
        v_source_name: str,
    ) -> str:
        """
        Constructs an unambiguous, human-readable justification for the compliance determination.
        """
        name = requirement.name or requirement.code
        if passed:
            if operator == ComplianceOperator.EQUALS:
                return f"{v_type or name} is verified by {v_source_name} and matches required '{expected_val}' (Actual: '{actual_val}')."
            elif operator in (ComplianceOperator.IN, "IN_LIST"):
                return f"{v_type or name} is verified as '{actual_val}', which satisfies required category in {expected_val}."
            elif operator == ComplianceOperator.EXISTS:
                return f"{v_type or name} is confirmed and active in authoritative source ({v_source_name})."
            else:
                return f"{v_type or name} ({actual_val}) satisfies requirement criteria ({operator} '{expected_val}')."
        else:
            if operator == ComplianceOperator.EQUALS:
                return f"{v_type or name} is verified by {v_source_name} as '{actual_val}', but requirement mandates '{expected_val}'."
            elif operator in (ComplianceOperator.IN, "IN_LIST"):
                return f"{v_type or name} is verified as '{actual_val}', which is not in permitted categories {expected_val}."
            elif operator == ComplianceOperator.EXISTS:
                return f"{v_type or name} credential is missing or unverified in authoritative source."
            else:
                return f"{v_type or name} actual value ('{actual_val}') fails condition ({operator} '{expected_val}')."
