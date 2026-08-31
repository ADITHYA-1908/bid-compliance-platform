"""
Financial Compliance Rule Evaluator for Part 6C
Evaluates financial tender requirements (Annual Turnover, 3-Year Average Turnover,
Profitability / PAT, Total Revenue, Financial Statements) against verified Part 5
records and structured document extractions with strict Decimal precision.
"""

from decimal import Decimal, InvalidOperation
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from app.compliance.evaluators.base import ComplianceRuleEvaluator
from app.compliance.operators import compare_numbers, evaluate_generic_operator
from app.compliance.types import (
    ComplianceContext,
    ComplianceOperator,
    ComplianceRuleResult,
    ComplianceStatus,
)
from app.db.models.bid_document import BidDocument
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.verification_record import (
    VerificationMatchStatus,
    VerificationRecord,
    VerificationStatus,
)

logger = logging.getLogger(__name__)

FINANCIAL_KEYWORDS = {
    "turnover",
    "annual_turnover",
    "average_turnover",
    "revenue",
    "total_revenue",
    "profit",
    "pat",
    "pbt",
    "net_profit",
    "financial",
    "balance_sheet",
    "financial_statement",
    "net_worth",
}


def normalize_indian_currency(val: Any) -> Optional[Decimal]:
    """
    Normalizes Indian and international currency strings, words, and numbers to Decimal.
    Supports Crore (Cr), Lakh (L), Millions, commas, and currency symbols.
    Examples:
        '5 Crore' -> 50,000,000
        '5.4 Cr' -> 54,000,000
        '50 Lakh' -> 5,000,000
        '₹ 5,00,00,000' -> 50,000,000
    """
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, float)):
        return Decimal(str(val))

    val_str = str(val).strip().replace(",", "").replace("₹", "").replace("INR", "").replace("Rs.", "").replace("Rs", "").strip()

    # Check for Crore / Cr
    cr_match = re.search(r"^([\d\.]+)\s*(?:crore|crores|cr)\.?$", val_str, re.IGNORECASE)
    if cr_match:
        try:
            num = Decimal(cr_match.group(1))
            return num * Decimal("10000000")
        except InvalidOperation:
            return None

    # Check for Lakh / L
    lakh_match = re.search(r"^([\d\.]+)\s*(?:lakh|lakhs|lac|lacs|l)\.?$", val_str, re.IGNORECASE)
    if lakh_match:
        try:
            num = Decimal(lakh_match.group(1))
            return num * Decimal("100000")
        except InvalidOperation:
            return None

    # Check for Million / M
    m_match = re.search(r"^([\d\.]+)\s*(?:million|millions|m)\.?$", val_str, re.IGNORECASE)
    if m_match:
        try:
            num = Decimal(m_match.group(1))
            return num * Decimal("1000000")
        except InvalidOperation:
            return None

    # Standard numeric string
    try:
        cleaned = re.sub(r"[^\d\.\-]", "", val_str)
        if cleaned:
            return Decimal(cleaned)
    except InvalidOperation:
        return None

    return None


class FinancialComplianceEvaluator(ComplianceRuleEvaluator):
    """
    Specialized compliance evaluator for financial capability rules.
    """

    @property
    def evaluator_name(self) -> str:
        return "FinancialComplianceEvaluator"

    def supports(self, requirement: TenderRequirement) -> bool:
        """
        Determines if this evaluator handles the requirement based on category or code.
        """
        category = (requirement.category or "").strip().upper()
        if category in ("FINANCIAL", "FINANCE", "TURNOVER", "COMMERCIAL"):
            return True

        code_lower = (requirement.code or "").strip().lower()
        name_lower = (requirement.name or "").strip().lower()

        tokens = set(
            code_lower.replace("_", " ").replace("-", " ").split()
            + name_lower.replace("_", " ").replace("-", " ").split()
        )

        return any(kw in tokens for kw in FINANCIAL_KEYWORDS)

    def evaluate(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> ComplianceRuleResult:
        """
        Evaluates a financial requirement against verified records and structured document data.
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
        if req_type == "DOCUMENT" or "DOCUMENT_REQUIRED" in code_upper or "STATEMENT_REQUIRED" in code_upper:
            return self._evaluate_document_presence(requirement, context, is_mandatory, weight)

        # ---------------------------------------------------------------------
        # 2. Extract Financial Data (Verified Part 5 vs Structured Part 4)
        # ---------------------------------------------------------------------
        financial_data, source_ids, evidence_dict, issue_status, issue_reason = self._extract_financial_data(
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
        # 3. Validate Requirement Configuration
        # ---------------------------------------------------------------------
        expected_dec = normalize_indian_currency(expected)
        if expected_dec is None and operator not in (ComplianceOperator.EXISTS, ComplianceOperator.NOT_EXISTS):
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=expected,
                operator=operator,
                reason=f"Invalid tender requirement configuration: expected financial value '{expected}' is missing or not a valid number.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 4. Profitability / PAT Rules
        # ---------------------------------------------------------------------
        if "PROFIT" in code_upper or "PAT" in code_upper or "PROFITABILITY" in code_upper or "profit" in name_lower:
            return self._evaluate_profitability(
                requirement=requirement,
                financial_data=financial_data,
                expected_dec=expected_dec or Decimal("0"),
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 5. Average Annual Turnover Rules
        # ---------------------------------------------------------------------
        if "AVERAGE" in code_upper or "AVG" in code_upper or "average" in name_lower:
            return self._evaluate_average_turnover(
                requirement=requirement,
                financial_data=financial_data,
                expected_dec=expected_dec,
                operator=operator,
                source_ids=source_ids,
                evidence_dict=evidence_dict,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        # ---------------------------------------------------------------------
        # 6. Annual Turnover / Single Year / Revenue Rules
        # ---------------------------------------------------------------------
        return self._evaluate_annual_turnover(
            requirement=requirement,
            financial_data=financial_data,
            expected_dec=expected_dec,
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
        Evaluates requirement that only mandates uploading a financial document.
        """
        matching_docs = [
            d for d in context.bid_documents
            if d.is_active and (
                "FINANCIAL" in (d.document_type or "").upper()
                or "TURNOVER" in (d.document_type or "").upper()
                or "BALANCE" in (d.document_type or "").upper()
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
                reason=f"Financial statement document '{doc.document_name}' is uploaded and verified.",
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
            reason="Required financial statement / turnover certificate document is missing.",
            evidence={"requirement_code": requirement.code},
            source_verification_ids=[],
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _extract_financial_data(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> Tuple[Dict[str, Any], List[str], Dict[str, Any], Optional[str], Optional[str]]:
        """
        Extracts financial metrics from Part 5 verification records or Part 4 structured extractions.
        Returns (data_dict, source_ids, evidence_dict, issue_status, issue_reason).
        """
        source_ids: List[str] = []
        evidence_dict: Dict[str, Any] = {}
        data_dict: Dict[str, Any] = {}

        # 1. Check Part 5 Verification Records (Highest Priority)
        fin_verifications = [
            v for v in context.verifications
            if v.verification_type in ("SUPPORTING_DOCUMENT", "FINANCIAL", "OTHER")
            or "turnover" in (v.claim_source or "").lower()
            or "financial" in (v.claim_source or "").lower()
            or "profit" in (v.claim_source or "").lower()
        ]

        if fin_verifications:
            primary_v = fin_verifications[0]
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
                    f"Financial verification requires review: {primary_v.error_message or 'Scan ambiguity flag'}"
                )

            if primary_v.verification_status == VerificationStatus.NOT_VERIFIED:
                return {}, source_ids, evidence_dict, ComplianceStatus.FAIL, (
                    f"Financial credentials could not be verified in source ({primary_v.source_name})."
                )

            # Extract from verified payload
            payload = primary_v.response_payload or primary_v.evidence or {}
            if isinstance(payload, dict):
                data_dict.update(payload)
            if primary_v.verified_value is not None:
                data_dict["verified_value"] = primary_v.verified_value

        # 2. Check Part 4 Structured Extractions on Active Documents
        extracted_turnovers: List[Tuple[str, Decimal]] = []
        for doc in context.bid_documents:
            if not doc.is_active:
                continue

            proc = doc.processing
            if proc and proc.extracted_data and isinstance(proc.extracted_data, dict):
                ext = proc.extracted_data

                # Review flag gate
                if proc.extraction_requires_review or (proc.extraction_confidence and proc.extraction_confidence < 0.55):
                    evidence_dict["extraction_review_flag"] = True
                    evidence_dict["extraction_confidence"] = proc.extraction_confidence

                # Turnover fields
                for k in ("turnover", "annual_turnover", "average_turnover", "total_revenue", "profit_after_tax", "profit_before_tax", "net_profit", "financial_years"):
                    if k in ext and ext[k] is not None:
                        data_dict.setdefault(k, ext[k])

                # Track multiple turnovers to detect conflicts
                if "turnover" in ext and ext["turnover"] is not None:
                    t_dec = normalize_indian_currency(ext["turnover"])
                    if t_dec is not None:
                        extracted_turnovers.append((doc.document_name, t_dec))

        # Check for conflicting financial values across documents
        if len(extracted_turnovers) >= 2 and not fin_verifications:
            vals = [t[1] for t in extracted_turnovers]
            if len(set(vals)) > 1:
                conflict_details = ", ".join(f"{t[0]}: ₹{t[1]:,}" for t in extracted_turnovers)
                evidence_dict["conflicting_sources"] = conflict_details
                return {}, source_ids, evidence_dict, ComplianceStatus.REVIEW, (
                    f"Conflicting turnover values extracted from documents without authoritative verification ({conflict_details}). Human review required."
                )

        if not data_dict:
            return {}, source_ids, evidence_dict, ComplianceStatus.PENDING, (
                f"No financial data or turnover records available for evaluation of '{requirement.code}'."
            )

        return data_dict, source_ids, evidence_dict, None, None

    def _evaluate_profitability(
        self,
        requirement: TenderRequirement,
        financial_data: Dict[str, Any],
        expected_dec: Decimal,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates profitability / Net Profit After Tax criteria.
        """
        pat_val = (
            financial_data.get("profit_after_tax")
            or financial_data.get("net_profit")
            or financial_data.get("profit_before_tax")
            or financial_data.get("pat")
            or financial_data.get("pbt")
        )

        pat_dec = normalize_indian_currency(pat_val)
        if pat_dec is None:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=str(pat_val) if pat_val is not None else None,
                expected_value=expected_dec,
                operator=operator,
                reason="Profit after tax / net profit data is missing or could not be determined reliably.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        evidence_dict["actual_profit_after_tax"] = float(pat_dec)
        comp_ok, err_msg = compare_numbers(pat_dec, expected_dec, operator if operator != "EQUALS" else ComplianceOperator.GREATER_THAN)

        if err_msg:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=float(pat_dec),
                expected_value=float(expected_dec),
                operator=operator,
                reason=err_msg,
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"Verified Net Profit After Tax (₹{pat_dec:,.2f}) satisfies requirement ({operator} ₹{expected_dec:,.2f})."
            if comp_ok
            else f"Verified Net Profit After Tax (₹{pat_dec:,.2f}) fails condition ({operator} ₹{expected_dec:,.2f})."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=float(pat_dec),
            expected_value=float(expected_dec),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_average_turnover(
        self,
        requirement: TenderRequirement,
        financial_data: Dict[str, Any],
        expected_dec: Decimal,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Calculates and evaluates multi-year average annual turnover.
        Ensures all required financial years are present before evaluating.
        """
        fin_years_raw = financial_data.get("financial_years")
        avg_turnover_dec: Optional[Decimal] = None

        if isinstance(fin_years_raw, dict) and fin_years_raw:
            # Multi-year dictionary e.g. {"2022-23": 40000000, "2023-24": 50000000, "2024-25": 60000000}
            parsed_years: Dict[str, Decimal] = {}
            for y, val in fin_years_raw.items():
                val_dec = normalize_indian_currency(val)
                if val_dec is not None:
                    parsed_years[y] = val_dec

            evidence_dict["financial_years_evaluated"] = {k: float(v) for k, v in parsed_years.items()}

            # Default required years is 3 for average turnover rules
            required_years_count = 3
            if len(parsed_years) < required_years_count:
                available_str = ", ".join(parsed_years.keys()) if parsed_years else "None"
                return ComplianceRuleResult(
                    compliance_status=ComplianceStatus.REVIEW,
                    actual_value=None,
                    expected_value=float(expected_dec),
                    operator=operator,
                    reason=(
                        f"Only {len(parsed_years)} financial year(s) ({available_str}) provided, "
                        f"but average turnover mandates {required_years_count} complete financial years."
                    ),
                    evidence=evidence_dict,
                    source_verification_ids=source_ids,
                    is_mandatory=is_mandatory,
                    weight=weight,
                )

            # Calculate exact Decimal average
            total_sum = sum(parsed_years.values(), Decimal("0"))
            avg_turnover_dec = total_sum / Decimal(str(len(parsed_years)))
        else:
            # Fallback to direct average_turnover field or turnover field
            avg_val = financial_data.get("average_turnover") or financial_data.get("turnover") or financial_data.get("verified_value")
            avg_turnover_dec = normalize_indian_currency(avg_val)

        if avg_turnover_dec is None:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=None,
                expected_value=float(expected_dec),
                operator=operator,
                reason="Average annual turnover could not be determined from submitted financial records.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        evidence_dict["calculated_average_turnover"] = float(avg_turnover_dec)
        comp_ok, err_msg = compare_numbers(avg_turnover_dec, expected_dec, operator)

        if err_msg:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=float(avg_turnover_dec),
                expected_value=float(expected_dec),
                operator=operator,
                reason=err_msg,
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"Verified average annual turnover (₹{avg_turnover_dec:,.2f}) meets the required threshold ({operator} ₹{expected_dec:,.2f})."
            if comp_ok
            else f"Verified average annual turnover (₹{avg_turnover_dec:,.2f}) is below the required threshold ({operator} ₹{expected_dec:,.2f})."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=float(avg_turnover_dec),
            expected_value=float(expected_dec),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )

    def _evaluate_annual_turnover(
        self,
        requirement: TenderRequirement,
        financial_data: Dict[str, Any],
        expected_dec: Decimal,
        operator: str,
        source_ids: List[str],
        evidence_dict: Dict[str, Any],
        is_mandatory: bool,
        weight: Optional[Decimal],
    ) -> ComplianceRuleResult:
        """
        Evaluates single-year annual turnover or total revenue criteria.
        """
        turnover_val = (
            financial_data.get("turnover")
            or financial_data.get("annual_turnover")
            or financial_data.get("total_revenue")
            or financial_data.get("verified_value")
        )

        # If financial_years is present, pick the latest year
        fin_years_raw = financial_data.get("financial_years")
        if isinstance(fin_years_raw, dict) and fin_years_raw and not turnover_val:
            sorted_years = sorted(fin_years_raw.keys(), reverse=True)
            turnover_val = fin_years_raw[sorted_years[0]]
            evidence_dict["evaluated_financial_year"] = sorted_years[0]

        turnover_dec = normalize_indian_currency(turnover_val)
        if turnover_dec is None:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=str(turnover_val) if turnover_val is not None else None,
                expected_value=float(expected_dec),
                operator=operator,
                reason="Annual turnover / revenue data is missing or formatted invalidly in submitted documents.",
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        evidence_dict["actual_turnover_evaluated"] = float(turnover_dec)
        comp_ok, err_msg = compare_numbers(turnover_dec, expected_dec, operator)

        if err_msg:
            return ComplianceRuleResult(
                compliance_status=ComplianceStatus.REVIEW,
                actual_value=float(turnover_dec),
                expected_value=float(expected_dec),
                operator=operator,
                reason=err_msg,
                evidence=evidence_dict,
                source_verification_ids=source_ids,
                is_mandatory=is_mandatory,
                weight=weight,
            )

        status = ComplianceStatus.PASS if comp_ok else ComplianceStatus.FAIL
        reason = (
            f"Verified annual turnover (₹{turnover_dec:,.2f}) satisfies requirement condition ({operator} ₹{expected_dec:,.2f})."
            if comp_ok
            else f"Verified annual turnover (₹{turnover_dec:,.2f}) is below the required threshold ({operator} ₹{expected_dec:,.2f})."
        )

        return ComplianceRuleResult(
            compliance_status=status,
            actual_value=float(turnover_dec),
            expected_value=float(expected_dec),
            operator=operator,
            reason=reason,
            evidence=evidence_dict,
            source_verification_ids=source_ids,
            is_mandatory=is_mandatory,
            weight=weight,
        )
