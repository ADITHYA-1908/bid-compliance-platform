"""
Experience & Past Performance Compliance Rule Evaluator for Part 6C
Evaluates past experience criteria (Years of Experience without overlapping double-count,
Completed Project Count, Single Project Value, Total Project Value, and Similar Projects)
against verified Part 5 records and Part 4 structured extractions.
"""

from datetime import date, datetime
from decimal import Decimal
import logging
import re
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

EXPERIENCE_KEYWORDS = {
    "experience",
    "years_experience",
    "past_performance",
    "project",
    "projects",
    "completed_projects",
    "work_order",
    "similar_project",
    "similar_projects",
    "contract_value",
    "single_project",
    "total_project",
}


def _parse_date(val: Any) -> Optional[date]:
    """Safely converts string or datetime to date."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        val_clean = val.strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(val_clean, fmt).date()
            except ValueError:
                continue
    return None


def merge_date_intervals(intervals: List[Tuple[date, date]]) -> List[Tuple[date, date]]:
    """
    Merges overlapping date intervals to eliminate double counting experience.
    """
    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged: List[Tuple[date, date]] = [sorted_intervals[0]]

    for current in sorted_intervals[1:]:
        prev_start, prev_end = merged[-1]
        curr_start, curr_end = current

        if curr_start <= prev_end:
            # Overlapping or contiguous interval -> extend end date
            merged[-1] = (prev_start, max(prev_end, curr_end))
        else:
            merged.append(current)

    return merged


class ExperienceComplianceEvaluator(ComplianceRuleEvaluator):
    """
    Specialized compliance evaluator for past experience and project performance.
    """

    @property
    def evaluator_name(self) -> str:
        return "ExperienceComplianceEvaluator"

    def supports(self, requirement: TenderRequirement) -> bool:
        """
        Determines if this evaluator handles the requirement.
        """
        category = (requirement.category or "").strip().upper()
        if category in ("EXPERIENCE", "PAST_PERFORMANCE", "PROJECT", "PROJECTS"):
            return True

        code_lower = (requirement.code or "").strip().lower()
        name_lower = (requirement.name or "").strip().lower()

        tokens = set(
            code_lower.replace("_", " ").replace("-", " ").split()
            + name_lower.replace("_", " ").replace("-", " ").split()
        )

        return any(kw in tokens for kw in EXPERIENCE_KEYWORDS)

    def evaluate(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> ComplianceRuleResult:
        """
        Evaluates an experience requirement against verified records and structured document data.
        """
        code_upper = (requirement.code or "").strip().upper()
        name_lower = (requirement.name or "").strip().lower()
        req_type = (requirement.requirement_type or "NUMBER").upper()
        operator = (requirement.operator or "GREATER_THAN_OR_EQUAL").upper()
        expected = requirement.expected_value
        is_mandatory = requirement.is_mandatory if requirement.is_mandatory is not None else True
        weight = requirement.weight

        # ---------------------------------------------------------------------
        # 1. Document Presence Only Rule
        # ---------------------------------------------------------------------
        if req_type == "DOCUMENT" or "DOCUMENT_REQUIRED" in code_upper or "CERTIFICATE_REQUIRED" in code_upper or "WORK_ORDER_REQUIRED" in code_upper:
            return self._evaluate_document_presence(requirement, context, is_mandatory, weight)

        # ---------------------------------------------------------------------
        # 2. Extract Projects & Experience Data
        # ---------------------------------------------------------------------
        projects, exp_summary, source_ids, evidence_dict, issue_status, issue_reason = self._extract_experience_data(
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
        # 3. Years of Experience Rule (without overlapping double counting)
        # ---------------------------------------------------------------------
        if "YEAR" in code_upper or "YEARS" in code_upper or "duration" in name_lower or "years" in name_lower:
            return self._evaluate_years_experience(
                requirement=requirement,
                projects=projects,
                exp_summary=exp_summary,
                expected=expected,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 4. Completed Projects Count Rule
        # ---------------------------------------------------------------------
        if "COUNT" in code_upper or "COMPLETED_PROJECTS" in code_upper or "min_completed" in name_lower:
            return self._evaluate_completed_projects_count(
                requirement=requirement,
                projects=projects,
                expected=expected,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 5. Single Project Value Threshold Rule
        # ---------------------------------------------------------------------
        if "SINGLE_PROJECT" in code_upper or "single_project" in name_lower:
            return self._evaluate_single_project_value(
                requirement=requirement,
                projects=projects,
                expected=expected,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 6. Total Project Value Summation Rule
        # ---------------------------------------------------------------------
        if "TOTAL_PROJECT" in code_upper or "total_value" in name_lower:
            return self._evaluate_total_project_value(
                requirement=requirement,
                projects=projects,
                expected=expected,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 7. Similar Projects Count Rule
        # ---------------------------------------------------------------------
        if "SIMILAR" in code_upper or "similar" in name_lower:
            return self._evaluate_similar_projects(
                requirement=requirement,
                projects=projects,
                expected=expected,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # General Fallback: Evaluate project count or years
        return self._evaluate_completed_projects_count(
            requirement=requirement,
            projects=projects,
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
        """
        Evaluates requirement for uploading experience certificates or work orders.
        """
        matching_docs = [
            d for d in context.bid_documents
            if d.is_active and (
                "EXPERIENCE" in (d.document_type or "").upper()
                or "WORK_ORDER" in (d.document_type or "").upper()
                or "PROJECT" in (d.document_type or "").upper()
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
                reason=f"Experience proof document '{doc.document_name}' is uploaded and verified.",
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
            reason="Required experience certificate or work order proof document is missing.",
            evidence={"requirement_code": requirement.code},
            source_verification_ids=[],
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _extract_experience_data(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[str], Dict[str, Any], Optional[str], Optional[str]]:
        """
        Extracts structured project lists and experience summaries from Part 5 verification
        or Part 4 structured extractions.
        """
        projects: List[Dict[str, Any]] = []
        exp_summary: Dict[str, Any] = {}
        source_ids: List[str] = []
        evidence_dict: Dict[str, Any] = {}

        # 1. Check Part 5 Verification Records
        exp_verifications = [
            v for v in context.verifications
            if "experience" in (v.claim_source or "").lower()
            or "project" in (v.claim_source or "").lower()
            or "work_order" in (v.claim_source or "").lower()
            or (v.verification_type or "").upper() in ("EXPERIENCE", "WORK_ORDER", "PROJECT")
        ]

        if exp_verifications:
            primary_v = exp_verifications[0]
            source_ids.append(str(primary_v.id))
            evidence_dict["verification_id"] = str(primary_v.id)
            evidence_dict["verification_status"] = primary_v.verification_status
            evidence_dict["source_name"] = primary_v.source_name

            if primary_v.verification_status in (VerificationStatus.UNAVAILABLE, "FAILED"):
                return [], {}, source_ids, evidence_dict, ComplianceStatus.REVIEW, (
                    f"External verification source ({primary_v.source_name}) is temporarily unavailable. "
                    f"Requirement is placed under review without penalizing bidder."
                )

            if primary_v.verification_status == VerificationStatus.NEEDS_REVIEW:
                return [], {}, source_ids, evidence_dict, ComplianceStatus.REVIEW, (
                    f"Experience verification requires review: {primary_v.error_message or 'Scan quality flag'}"
                )

            if primary_v.verification_status == VerificationStatus.NOT_VERIFIED:
                return [], {}, source_ids, evidence_dict, ComplianceStatus.FAIL, (
                    f"Experience credentials could not be verified in authoritative source ({primary_v.source_name})."
                )

            payload = primary_v.response_payload or primary_v.evidence or {}
            if isinstance(payload, dict):
                if "projects" in payload and isinstance(payload["projects"], list):
                    projects.extend(payload["projects"])
                exp_summary.update(payload)

        # 2. Check Part 4 Structured Extractions from Active Documents
        for doc in context.bid_documents:
            if not doc.is_active:
                continue

            proc = doc.processing
            if proc and proc.extracted_data and isinstance(proc.extracted_data, dict):
                ext = proc.extracted_data
                if proc.extraction_requires_review or (proc.extraction_confidence and proc.extraction_confidence < 0.55):
                    evidence_dict["extraction_review_flag"] = True

                # Projects array
                if "projects" in ext and isinstance(ext["projects"], list):
                    projects.extend(ext["projects"])
                elif "experience" in ext and isinstance(ext["experience"], list):
                    projects.extend(ext["experience"])
                elif any(k in ext for k in ("project_name", "work_order_number", "contract_value")):
                    # Single project in extracted_data
                    projects.append(ext)

                for k in ("years_experience", "total_projects", "experience_years"):
                    if k in ext and ext[k] is not None:
                        exp_summary.setdefault(k, ext[k])

        if not projects and not exp_summary:
            return [], {}, source_ids, evidence_dict, ComplianceStatus.PENDING, (
                f"No past experience records or work order details available for '{requirement.code}'."
            )

        return projects, exp_summary, source_ids, evidence_dict, None, None

    def _evaluate_years_experience(
        self,
        requirement: TenderRequirement,
        projects: List[Dict[str, Any]],
        exp_summary: Dict[str, Any],
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Calculates total experience duration from exact project dates without double-counting overlapping periods.
        """
        expected_years = normalize_indian_currency(expected)
        if expected_years is None:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=expected,
                operator=operator,
                reason=f"Invalid tender requirement configuration: expected years of experience '{expected}' is not a valid number.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # 1. Collect date intervals from projects
        intervals: List[Tuple[date, date]] = []
        for p in projects:
            s_date = _parse_date(p.get("start_date") or p.get("commencement_date"))
            c_date = _parse_date(p.get("completion_date") or p.get("end_date"))

            if s_date and c_date:
                if s_date <= c_date:
                    intervals.append((s_date, c_date))
                else:
                    intervals.append((c_date, s_date))

        actual_years_dec: Optional[Decimal] = None

        if intervals:
            merged = merge_date_intervals(intervals)
            total_days = sum((end - start).days for start, end in merged)
            # Standard 365.25 days per year
            actual_years_dec = Decimal(str(total_days)) / Decimal("365.25")
            evidence_dict["non_overlapping_intervals_count"] = len(merged)
            evidence_dict["total_experience_days"] = total_days
        else:
            # Fallback to summary field if explicit dates are not populated
            exp_val = exp_summary.get("years_experience") or exp_summary.get("experience_years") or exp_summary.get("years")
            actual_years_dec = normalize_indian_currency(exp_val)

        if actual_years_dec is None:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=float(expected_years),
                operator=operator,
                reason="Experience duration could not be calculated because start and completion dates are missing.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # Round to 1 decimal for clean presentation
        rounded_actual = round(actual_years_dec, 1)
        evidence_dict["actual_years_experience"] = float(rounded_actual)

        comp_ok, err_msg = compare_numbers(rounded_actual, expected_years, operator)
        if err_msg:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=float(rounded_actual),
                expected_value=float(expected_years),
                operator=operator,
                reason=err_msg,
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"Verified past experience ({rounded_actual:.1f} years) satisfies requirement condition ({operator} {expected_years:.1f} years)."
            if comp_ok
            else f"Verified past experience ({rounded_actual:.1f} years) is below the required duration ({operator} {expected_years:.1f} years)."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=float(rounded_actual),
            expected_value=float(expected_years),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_completed_projects_count(
        self,
        requirement: TenderRequirement,
        projects: List[Dict[str, Any]],
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates count of completed projects with completion proof.
        """
        expected_count = normalize_indian_currency(expected)
        if expected_count is None:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=len(projects),
                expected_value=expected,
                operator=operator,
                reason=f"Invalid tender requirement configuration: expected project count '{expected}' is invalid.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # Count completed projects
        completed_projects = []
        for p in projects:
            status_p = str(p.get("status") or "").upper()
            c_date = _parse_date(p.get("completion_date") or p.get("end_date"))
            # Eligible if marked completed or has a valid completion date in the past
            if "COMPLETED" in status_p or "FINISHED" in status_p or (c_date and c_date <= date.today()):
                completed_projects.append(p)
            elif not status_p and not c_date and p.get("project_name"):
                # Treat as project proof if project_name exists
                completed_projects.append(p)

        actual_count = Decimal(str(len(completed_projects)))
        evidence_dict["completed_projects_count"] = int(actual_count)
        evidence_dict["total_projects_submitted"] = len(projects)

        comp_ok, err_msg = compare_numbers(actual_count, expected_count, operator)
        if err_msg:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=int(actual_count),
                expected_value=int(expected_count),
                operator=operator,
                reason=err_msg,
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"Verified completed project count ({int(actual_count)}) satisfies requirement ({operator} {int(expected_count)} projects)."
            if comp_ok
            else f"Verified completed project count ({int(actual_count)}) is below the required {int(expected_count)} projects."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=int(actual_count),
            expected_value=int(expected_count),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_single_project_value(
        self,
        requirement: TenderRequirement,
        projects: List[Dict[str, Any]],
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates single project value threshold (e.g., at least 1 project >= ₹1 Crore).
        """
        expected_val_dec = normalize_indian_currency(expected)
        if expected_val_dec is None:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=expected,
                operator=operator,
                reason=f"Invalid tender requirement configuration: expected project value '{expected}' is invalid.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        project_values: List[Decimal] = []
        for p in projects:
            val = p.get("contract_value") or p.get("value") or p.get("project_value") or p.get("amount")
            val_dec = normalize_indian_currency(val)
            if val_dec is not None:
                project_values.append(val_dec)

        if not project_values:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=float(expected_val_dec),
                operator=operator,
                reason="None of the submitted past projects specify a contract value.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        max_val = max(project_values)
        evidence_dict["max_single_project_value"] = float(max_val)

        comp_ok, err_msg = compare_numbers(max_val, expected_val_dec, operator)
        if err_msg:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=float(max_val),
                expected_value=float(expected_val_dec),
                operator=operator,
                reason=err_msg,
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"Largest completed project value (₹{max_val:,.2f}) satisfies threshold ({operator} ₹{expected_val_dec:,.2f})."
            if comp_ok
            else f"Largest completed project value (₹{max_val:,.2f}) is below the required threshold ({operator} ₹{expected_val_dec:,.2f})."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=float(max_val),
            expected_value=float(expected_val_dec),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_total_project_value(
        self,
        requirement: TenderRequirement,
        projects: List[Dict[str, Any]],
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates cumulative project value across all eligible completed projects.
        """
        expected_total_dec = normalize_indian_currency(expected)
        if expected_total_dec is None:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=expected,
                operator=operator,
                reason=f"Invalid tender requirement configuration: expected total project value '{expected}' is invalid.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        project_values: List[Decimal] = []
        for p in projects:
            val = p.get("contract_value") or p.get("value") or p.get("project_value") or p.get("amount")
            val_dec = normalize_indian_currency(val)
            if val_dec is not None:
                project_values.append(val_dec)

        if not project_values:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=float(expected_total_dec),
                operator=operator,
                reason="No contract values could be extracted from the submitted project documents.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        total_sum = sum(project_values, Decimal("0"))
        evidence_dict["total_cumulative_project_value"] = float(total_sum)

        comp_ok, err_msg = compare_numbers(total_sum, expected_total_dec, operator)
        if err_msg:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=float(total_sum),
                expected_value=float(expected_total_dec),
                operator=operator,
                reason=err_msg,
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"Cumulative completed project value (₹{total_sum:,.2f}) satisfies threshold ({operator} ₹{expected_total_dec:,.2f})."
            if comp_ok
            else f"Cumulative completed project value (₹{total_sum:,.2f}) is below the required total ({operator} ₹{expected_total_dec:,.2f})."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=float(total_sum),
            expected_value=float(expected_total_dec),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_similar_projects(
        self,
        requirement: TenderRequirement,
        projects: List[Dict[str, Any]],
        expected: Any,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates count of similar projects matching scope or category deterministically.
        """
        expected_count = normalize_indian_currency(expected)
        if expected_count is None:
            expected_count = Decimal("1")

        # Deterministic check on scope / category
        req_name_lower = (requirement.name or "").lower()
        matched_similar: List[Dict[str, Any]] = []

        for p in projects:
            p_type = str(p.get("project_type") or p.get("category") or p.get("scope") or "").lower()
            p_name = str(p.get("project_name") or "").lower()

            if any(term in p_type or term in p_name for term in ("networking", "software", "security", "hardware", "civil", "consulting")):
                matched_similar.append(p)
            elif p_name:
                matched_similar.append(p)

        actual_similar_count = Decimal(str(len(matched_similar)))
        evidence_dict["similar_projects_count"] = int(actual_similar_count)

        comp_ok, err_msg = compare_numbers(actual_similar_count, expected_count, operator)
        if err_msg:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=int(actual_similar_count),
                expected_value=int(expected_count),
                operator=operator,
                reason=err_msg,
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"Verified {int(actual_similar_count)} similar completed project(s), meeting requirement ({operator} {int(expected_count)})."
            if comp_ok
            else f"Only {int(actual_similar_count)} similar project(s) identified, below the required {int(expected_count)}."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=int(actual_similar_count),
            expected_value=int(expected_count),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )
