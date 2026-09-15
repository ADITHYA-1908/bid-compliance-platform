"""
Document Classification Service for Part 4D: Document Classification
Provides deterministic, explainable, rule-and-pattern-based classification of bid documents
using extracted text signals, regex patterns, headings, page-level provenance, requirement context,
and filename hints.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import (
    DocumentClass,
    ClassificationConfidenceLevel,
    DocumentProcessing,
    ExtractionMethod,
    ProcessingStage,
    ProcessingStatus,
)
from app.db.models.tender_requirement import TenderRequirement

logger = logging.getLogger(__name__)

# Regular expressions for statutory and procurement identifiers
RE_GSTIN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b")
RE_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]{1}\b")
RE_UDYAM = re.compile(r"\bUDYAM-[A-Z]{2}-\d{2}-\d{7}\b", re.IGNORECASE)
RE_CIN = re.compile(r"\b[LUu]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")
RE_UDIN = re.compile(r"\b(?:UDIN[:\s-]*)?\d{18}\b|\bUDIN\b", re.IGNORECASE)
RE_DPIIT = re.compile(r"\b(?:DIPP|DPIIT)[/\s-]*\d+\b", re.IGNORECASE)
RE_EPFO = re.compile(r"\b[A-Z]{2}[/\s-]?[A-Z]{3}[/\s-]?\d{7}[/\s-]?\d{3}\b|\bESTABLISHMENT\s+CODE\b", re.IGNORECASE)
RE_ESIC = re.compile(r"\b\d{17}\b|\bESIC\s+CODE\b", re.IGNORECASE)
RE_BIS = re.compile(r"\bCM/L[/\s-]*\d{7,10}\b|\bIS\s*\d{3,5}\b", re.IGNORECASE)
RE_ISO = re.compile(r"\bISO\s*(?:9001|14001|27001|45001|13485|50001)(?::\d{4})?\b", re.IGNORECASE)


@dataclass
class ClassificationEvidence:
    heading_matches: List[str] = field(default_factory=list)
    keyword_matches: List[str] = field(default_factory=list)
    identifier_matches: List[str] = field(default_factory=list)
    filename_matches: List[str] = field(default_factory=list)
    requirement_match: Optional[str] = None
    page_number: int = 1
    snippet: Optional[str] = None


@dataclass
class ClassificationResult:
    detected_document_type: str
    confidence: float
    confidence_level: str  # HIGH, MEDIUM, LOW
    method: str  # RULE_BASED
    reason: str
    evidence_snippet: Optional[str] = None
    page_number: int = 1
    expected_document_type: Optional[str] = None
    requires_review: bool = False
    evidence: Optional[ClassificationEvidence] = None


# Comprehensive Signal Rulebook defining anchor headings, keywords, identifiers, and filename tokens
DOCUMENT_CLASS_RULES = {
    DocumentClass.GST_CERTIFICATE: {
        "headings": [
            "goods and services tax",
            "registration certificate",
            "form gst reg",
            "form gst reg-06",
            "gst registration certificate",
            "government of india",
            "taxpayer type",
            "jurisdiction",
        ],
        "keywords": [
            "gstin",
            "legal name",
            "trade name",
            "constitution of business",
            "date of liability",
            "period of validity",
            "principal place of business",
            "taxpayer type",
        ],
        "regex": [RE_GSTIN],
        "filename_tokens": ["gst", "gstin", "gst_cert", "gst_certificate", "tax_reg"],
    },
    DocumentClass.PAN: {
        "headings": [
            "permanent account number",
            "income tax department",
            "govt of india",
            "government of india",
            "income tax",
            "pan card",
        ],
        "keywords": [
            "father's name",
            "date of birth",
            "signature",
            "pan",
            "photo",
            "permanent account number card",
        ],
        "regex": [RE_PAN],
        "filename_tokens": ["pan", "pancard", "pan_card", "pan_document", "pan_certificate"],
    },
    DocumentClass.UDYAM_CERTIFICATE: {
        "headings": [
            "udyam registration certificate",
            "ministry of micro, small and medium enterprises",
            "ministry of msme",
            "udyam registration",
            "msme registration certificate",
        ],
        "keywords": [
            "udyam registration number",
            "enterprise type",
            "major activity",
            "social category",
            "date of incorporation",
            "national industry classification",
            "micro",
            "small",
            "medium",
            "dic",
        ],
        "regex": [RE_UDYAM],
        "filename_tokens": ["udyam", "msme", "udyam_certificate", "msme_cert"],
    },
    DocumentClass.INCORPORATION_CERTIFICATE: {
        "headings": [
            "certificate of incorporation",
            "ministry of corporate affairs",
            "registrar of companies",
            "form 1",
            "form inc-11",
            "companies act",
        ],
        "keywords": [
            "corporate identity number",
            "cin",
            "incorporated under the companies act",
            "company limited by shares",
            "company is limited",
            "date of incorporation",
            "roc",
        ],
        "regex": [RE_CIN],
        "filename_tokens": ["incorporation", "coi", "cin", "mca", "company_reg", "inc_cert"],
    },
    DocumentClass.DPIIT_STARTUP_CERTIFICATE: {
        "headings": [
            "department for promotion of industry and internal trade",
            "startup india",
            "certificate of recognition",
            "dipp",
            "dpiit",
        ],
        "keywords": [
            "recognized as a startup",
            "startup recognition",
            "dipp recognition number",
            "dpiit recognition number",
            "working towards innovation",
            "ministry of commerce and industry",
        ],
        "regex": [RE_DPIIT],
        "filename_tokens": ["dpiit", "startup", "startup_india", "dipp_cert", "startup_recognition"],
    },
    DocumentClass.NSIC_CERTIFICATE: {
        "headings": [
            "national small industries corporation",
            "nsic",
            "government purchases enlistment certificate",
            "single point registration scheme",
            "sprs",
        ],
        "keywords": [
            "enlistment certificate",
            "monetary limit",
            "store details",
            "qualitative capacity",
            "sprs registration",
            "nsic certificate",
        ],
        "regex": [],
        "filename_tokens": ["nsic", "sprs", "nsic_cert", "single_point"],
    },
    DocumentClass.EPFO_CERTIFICATE: {
        "headings": [
            "employees' provident fund organisation",
            "employees provident fund",
            "epfo",
            "electronic challan cum return",
            "ecr",
        ],
        "keywords": [
            "establishment code",
            "establishment id",
            "epfo registration",
            "provident fund",
            "uan",
            "wage month",
        ],
        "regex": [RE_EPFO],
        "filename_tokens": ["epfo", "pf", "pf_cert", "epfo_ecr", "provident_fund"],
    },
    DocumentClass.ESIC_CERTIFICATE: {
        "headings": [
            "employees' state insurance corporation",
            "employees state insurance",
            "esic",
            "form c-11",
        ],
        "keywords": [
            "employer's code no",
            "employer code",
            "esic registration",
            "esi corporation",
            "insurance number",
        ],
        "regex": [RE_ESIC],
        "filename_tokens": ["esic", "esi", "esic_cert", "esi_code"],
    },
    DocumentClass.BALANCE_SHEET: {
        "headings": [
            "balance sheet",
            "statement of financial position",
            "as at 31st march",
            "as on 31st march",
        ],
        "keywords": [
            "equity and liabilities",
            "current assets",
            "non-current assets",
            "shareholder's funds",
            "total assets",
            "total equity",
            "liabilities",
        ],
        "regex": [],
        "filename_tokens": ["balance_sheet", "bs", "balancesheet"],
    },
    DocumentClass.PROFIT_LOSS_STATEMENT: {
        "headings": [
            "statement of profit and loss",
            "profit and loss account",
            "income statement",
            "statement of income and expenditure",
        ],
        "keywords": [
            "revenue from operations",
            "total revenue",
            "total expenses",
            "net profit",
            "profit before tax",
            "profit for the year",
            "cost of materials consumed",
        ],
        "regex": [],
        "filename_tokens": ["pnl", "profit_loss", "pl", "income_statement"],
    },
    DocumentClass.FINANCIAL_STATEMENT: {
        "headings": [
            "independent auditor's report",
            "audited financial statements",
            "auditors report",
            "annual report",
            "financial statements",
        ],
        "keywords": [
            "notes forming part of the financial statements",
            "accounting policies",
            "true and fair view",
            "statutory auditor",
            "chartered accountants",
            "financial year",
        ],
        "regex": [],
        "filename_tokens": ["financial", "financial_statement", "annual_report", "audited_financials"],
    },
    DocumentClass.TURNOVER_CERTIFICATE: {
        "headings": [
            "turnover certificate",
            "annual turnover certificate",
            "certificate of turnover",
            "chartered accountant certificate",
            "ca certificate",
        ],
        "keywords": [
            "annual turnover",
            "gross turnover",
            "average annual turnover",
            "turnover from operations",
            "chartered accountant",
            "membership number",
            "firm registration",
            "financial year",
            "udin",
        ],
        "regex": [RE_UDIN],
        "filename_tokens": ["turnover", "ca_cert", "turnover_certificate", "ca_turnover"],
    },
    DocumentClass.ITR_DOCUMENT: {
        "headings": [
            "indian income tax return acknowledgement",
            "income tax return",
            "itr-v",
            "itr acknowledgment",
            "centralized processing center",
        ],
        "keywords": [
            "assessment year",
            "acknowledgement number",
            "gross total income",
            "total tax payable",
            "verification code",
            "e-filing",
        ],
        "regex": [],
        "filename_tokens": ["itr", "itrv", "income_tax_return", "itr_ack"],
    },
    DocumentClass.OEM_AUTHORIZATION: {
        "headings": [
            "manufacturer authorization",
            "manufacturers authorization",
            "manufacturer's authorization",
            "authorization letter",
            "authorisation letter",
            "oem authorization",
            "maf",
            "oem declaration",
        ],
        "keywords": [
            "authorized partner",
            "authorised partner",
            "authorized reseller",
            "authorised reseller",
            "original equipment manufacturer",
            "we hereby authorize",
            "we hereby authorise",
            "bid response for",
            "warranty support",
            "guarantee support",
        ],
        "regex": [],
        "filename_tokens": ["oem", "maf", "auth", "authorization", "oem_auth"],
    },
    DocumentClass.COMPLETION_CERTIFICATE: {
        "headings": [
            "work completion certificate",
            "completion certificate",
            "project completion certificate",
            "satisfactory completion certificate",
        ],
        "keywords": [
            "satisfactorily completed",
            "successfully completed",
            "date of completion",
            "final completion",
            "executed value",
            "completed the work",
        ],
        "regex": [],
        "filename_tokens": ["completion", "completion_cert", "work_completion"],
    },
    DocumentClass.WORK_ORDER: {
        "headings": [
            "work order",
            "purchase order",
            "letter of award",
            "loa",
            "contract agreement",
            "award of contract",
        ],
        "keywords": [
            "order no",
            "po no",
            "contract value",
            "scope of work",
            "date of commencement",
            "delivery period",
            "terms and conditions",
        ],
        "regex": [],
        "filename_tokens": ["work_order", "purchase_order", "po", "loa", "order"],
    },
    DocumentClass.EXPERIENCE_CERTIFICATE: {
        "headings": [
            "experience certificate",
            "past experience certificate",
            "performance certificate",
            "client certificate",
        ],
        "keywords": [
            "satisfactory performance",
            "service performance",
            "client certificate",
            "past credentials",
            "experience in supplying",
        ],
        "regex": [],
        "filename_tokens": ["experience", "past_experience", "experience_cert"],
    },
    DocumentClass.LOCAL_CONTENT_DECLARATION: {
        "headings": [
            "make in india declaration",
            "local content declaration",
            "local content certificate",
            "preference to make in india",
            "mii declaration",
            "mii certificate",
        ],
        "keywords": [
            "make in india",
            "local content",
            "class-i local supplier",
            "class-ii local supplier",
            "percentage of local content",
            "local value addition",
            "location of value addition",
            "public procurement (preference to make in india)",
        ],
        "regex": [],
        "filename_tokens": ["local_content", "make_in_india", "mii", "mii_declaration", "mii_cert"],
    },
    DocumentClass.BIS_CERTIFICATE: {
        "headings": [
            "bureau of indian standards",
            "bis licence",
            "bis certificate",
            "conformity assessment",
            "grant of licence",
        ],
        "keywords": [
            "isi mark",
            "standard mark",
            "is/iso",
            "licence no",
            "cml no",
            "valid up to",
        ],
        "regex": [RE_BIS],
        "filename_tokens": ["bis", "bis_cert", "isi_cert"],
    },
    DocumentClass.QUALITY_CERTIFICATE: {
        "headings": [
            "certificate of registration",
            "quality management system",
            "iso 9001",
            "iso 14001",
            "iso 27001",
            "iso 45001",
            "accreditation certificate",
        ],
        "keywords": [
            "quality management system",
            "iso 9001:2015",
            "has been assessed and found to conform",
            "certification scope",
            "validity period",
            "surveillance audit",
        ],
        "regex": [RE_ISO],
        "filename_tokens": ["iso", "iso9001", "quality_cert", "iso_certificate"],
    },
    DocumentClass.BLACKLIST_DECLARATION: {
        "headings": [
            "non-blacklisting declaration",
            "blacklisting declaration",
            "non-debarment declaration",
            "self declaration for non-blacklisting",
            "declaration regarding non-blacklisting",
        ],
        "keywords": [
            "not blacklisted",
            "not debarred",
            "debarment",
            "never been blacklisted",
            "not banned",
            "any government agency",
            "public sector undertaking",
            "gem",
            "self declaration",
        ],
        "regex": [],
        "filename_tokens": ["blacklisting", "non_blacklisting", "debarment", "declaration"],
    },
    DocumentClass.TENDER_UNDERTAKING: {
        "headings": [
            "tender undertaking",
            "tender acceptance letter",
            "bid undertaking",
            "integrity pact",
            "undertaking by bidder",
        ],
        "keywords": [
            "unconditionally accept",
            "terms and conditions of tender",
            "bid security declaration",
            "integrity pact",
            "duly signed and accepted",
        ],
        "regex": [],
        "filename_tokens": ["undertaking", "tender_undertaking", "integrity_pact", "acceptance_letter"],
    },
    DocumentClass.TECHNICAL_DOCUMENT: {
        "headings": [
            "technical datasheet",
            "technical specifications",
            "product specification",
            "technical compliance sheet",
            "product brochure",
        ],
        "keywords": [
            "specifications",
            "operating temperature",
            "technical parameters",
            "dimensions",
            "model number",
            "features and benefits",
        ],
        "regex": [],
        "filename_tokens": ["datasheet", "technical_spec", "spec_sheet", "brochure"],
    },
}


def format_class_name(class_str: str) -> str:
    """Formats document class name with statutory acronym capitalization."""
    if not class_str:
        return ""
    acronyms = {
        "GST": "GST",
        "PAN": "PAN",
        "OEM": "OEM",
        "MAF": "MAF",
        "MII": "MII",
        "CA": "CA",
        "UDYAM": "Udyam",
        "DPIIT": "DPIIT",
        "NSIC": "NSIC",
        "EPFO": "EPFO",
        "ESIC": "ESIC",
        "ITR": "ITR",
        "BIS": "BIS",
        "ISO": "ISO",
        "CIN": "CIN",
        "PO": "PO",
        "LOA": "LOA",
    }
    words = class_str.replace("_", " ").split()
    return " ".join(acronyms.get(w.upper(), w.capitalize()) for w in words)


def derive_expected_document_type(
    requirement: Optional[TenderRequirement],
    document_type_hint: Optional[str] = None,
) -> Optional[str]:
    """
    Infers the expected document class from TenderRequirement code, name, category, or upload hint.
    """
    if not requirement and not document_type_hint:
        return None

    combined_meta = ""
    if requirement:
        combined_meta += f" {requirement.code or ''} {requirement.name or ''} {requirement.category or ''} {requirement.description or ''}"
    if document_type_hint:
        combined_meta += f" {document_type_hint}"

    combined_meta = combined_meta.lower()

    if any(k in combined_meta for k in ["gst", "gstin"]):
        return DocumentClass.GST_CERTIFICATE
    if any(k in combined_meta for k in ["pan", "permanent account"]):
        return DocumentClass.PAN
    if any(k in combined_meta for k in ["udyam", "msme"]):
        return DocumentClass.UDYAM_CERTIFICATE
    if any(k in combined_meta for k in ["incorporation", "cin", "mca", "coi"]):
        return DocumentClass.INCORPORATION_CERTIFICATE
    if any(k in combined_meta for k in ["dpiit", "startup", "dipp"]):
        return DocumentClass.DPIIT_STARTUP_CERTIFICATE
    if any(k in combined_meta for k in ["nsic", "sprs"]):
        return DocumentClass.NSIC_CERTIFICATE
    if any(k in combined_meta for k in ["epfo", "provident fund", "pf"]):
        return DocumentClass.EPFO_CERTIFICATE
    if any(k in combined_meta for k in ["esic", "state insurance", "esi"]):
        return DocumentClass.ESIC_CERTIFICATE
    if any(k in combined_meta for k in ["turnover", "ca certificate", "ca turnover", "udin"]):
        return DocumentClass.TURNOVER_CERTIFICATE
    if any(k in combined_meta for k in ["balance sheet"]):
        return DocumentClass.BALANCE_SHEET
    if any(k in combined_meta for k in ["profit and loss", "pnl", "income statement"]):
        return DocumentClass.PROFIT_LOSS_STATEMENT
    if any(k in combined_meta for k in ["financial", "audited", "annual report"]):
        return DocumentClass.FINANCIAL_STATEMENT
    if any(k in combined_meta for k in ["itr", "income tax return", "itrv"]):
        return DocumentClass.ITR_DOCUMENT
    if any(k in combined_meta for k in ["oem", "authorization", "authorisation", "maf"]):
        return DocumentClass.OEM_AUTHORIZATION
    if any(k in combined_meta for k in ["work order", "purchase order", "po"]):
        return DocumentClass.WORK_ORDER
    if any(k in combined_meta for k in ["completion certificate", "project completion"]):
        return DocumentClass.COMPLETION_CERTIFICATE
    if any(k in combined_meta for k in ["experience", "past performance"]):
        return DocumentClass.EXPERIENCE_CERTIFICATE
    if any(k in combined_meta for k in ["local content", "make in india", "mii"]):
        return DocumentClass.LOCAL_CONTENT_DECLARATION
    if any(k in combined_meta for k in ["bis", "isi mark"]):
        return DocumentClass.BIS_CERTIFICATE
    if any(k in combined_meta for k in ["iso", "quality management"]):
        return DocumentClass.QUALITY_CERTIFICATE
    if any(k in combined_meta for k in ["blacklist", "debarment", "debar"]):
        return DocumentClass.BLACKLIST_DECLARATION
    if any(k in combined_meta for k in ["undertaking", "integrity pact"]):
        return DocumentClass.TENDER_UNDERTAKING
    if any(k in combined_meta for k in ["datasheet", "specification", "technical compliance"]):
        return DocumentClass.TECHNICAL_DOCUMENT

    return None


def split_pages_with_numbers(text: str) -> List[Tuple[int, str]]:
    """
    Parses [PAGE 1], [PAGE 2], etc. headers from extracted text.
    Returns a list of (1-indexed page_number, page_text).
    If no [PAGE N] headers are found, returns [(1, text)].
    """
    page_splits = re.split(r"\[PAGE\s+(\d+)\]", text, flags=re.IGNORECASE)
    if len(page_splits) <= 1:
        return [(1, text)]

    pages: List[Tuple[int, str]] = []
    if page_splits[0].strip():
        pages.append((1, page_splits[0]))

    for i in range(1, len(page_splits), 2):
        try:
            p_num = int(page_splits[i])
        except ValueError:
            p_num = (i // 2) + 1
        p_text = page_splits[i + 1] if i + 1 < len(page_splits) else ""
        pages.append((p_num, p_text))

    return pages if pages else [(1, text)]


def extract_evidence_snippet(
    raw_text: str,
    matched_term: str,
    max_len: int = 120,
) -> str:
    """
    Extracts an authentic snippet of text around the matched term from the actual document text.
    """
    idx = raw_text.lower().find(matched_term.lower())
    if idx == -1:
        return matched_term

    start = max(0, idx - 20)
    end = min(len(raw_text), idx + len(matched_term) + 60)
    snippet = raw_text[start:end].replace("\n", " ").strip()
    clean_snippet = " ".join(snippet.split())
    if start > 0:
        clean_snippet = "..." + clean_snippet
    if end < len(raw_text):
        clean_snippet = clean_snippet + "..."
    return clean_snippet[:max_len]


def calculate_class_score(
    text_lower: str,
    raw_text: str,
    filename_lower: str,
    rules: dict,
    expected_type: Optional[str],
    target_class: str,
) -> Tuple[float, ClassificationEvidence]:
    """
    Calculates a deterministic composite score [0.0 - 1.0] for a specific document class.
    Weights:
      - Has Regex: Heading (0.40) + Regex (0.25) + Keywords (0.20) + Filename (0.05) + Requirement (0.10)
      - No Regex: Heading (0.50) + Keywords (0.35) + Filename (0.05) + Requirement (0.10)
    """
    evidence = ClassificationEvidence()
    score = 0.0
    has_regex_rules = bool(rules.get("regex"))

    # Parse pages for provenance
    pages = split_pages_with_numbers(raw_text)
    best_page = 1
    best_snippet = None

    # 1. Heading matches
    matched_headings = [h for h in rules["headings"] if h in text_lower]
    if matched_headings:
        evidence.heading_matches = matched_headings
        if has_regex_rules:
            heading_weight = min(0.40, 0.30 + (0.05 * (len(matched_headings) - 1)))
        else:
            heading_weight = min(0.50, 0.40 + (0.05 * (len(matched_headings) - 1)))
        score += heading_weight

        # Identify which page contains the heading
        for p_num, p_text in pages:
            if matched_headings[0] in p_text.lower():
                best_page = p_num
                best_snippet = extract_evidence_snippet(p_text, matched_headings[0])
                break

    # 2. Identifier Regex (if applicable)
    if has_regex_rules:
        matched_regex_vals = []
        for rgx in rules.get("regex", []):
            matches = rgx.findall(raw_text)
            if matches:
                matched_regex_vals.extend(matches[:2])
        if matched_regex_vals:
            evidence.identifier_matches = [str(m) for m in matched_regex_vals]
            score += 0.25
            if not best_snippet:
                for p_num, p_text in pages:
                    if str(matched_regex_vals[0]) in p_text:
                        best_page = p_num
                        best_snippet = extract_evidence_snippet(p_text, str(matched_regex_vals[0]))
                        break

    # 3. Supporting Keywords
    matched_keywords = [k for k in rules["keywords"] if k in text_lower]
    if matched_keywords:
        evidence.keyword_matches = matched_keywords
        kw_ratio = min(1.0, len(matched_keywords) / max(2, len(rules["keywords"]) / 3))
        if has_regex_rules:
            score += 0.20 * kw_ratio
        else:
            score += 0.35 * kw_ratio
        if not best_snippet and matched_keywords:
            for p_num, p_text in pages:
                if matched_keywords[0] in p_text.lower():
                    best_page = p_num
                    best_snippet = extract_evidence_snippet(p_text, matched_keywords[0])
                    break

    # 4. Filename Tokens (up to 0.05)
    matched_fn = [fn for fn in rules.get("filename_tokens", []) if fn in filename_lower]
    if matched_fn:
        evidence.filename_matches = matched_fn
        score += 0.05

    # 5. Expected Requirement Alignment (up to 0.10)
    if expected_type and (expected_type == target_class or (target_class == DocumentClass.PAN and expected_type == DocumentClass.PAN_CERTIFICATE)):
        evidence.requirement_match = expected_type
        score += 0.10

    # Specificity & Collision Adjustments:
    # Anti-collision: PAN vs GST (GSTIN contains PAN, GST cert has PAN)
    if target_class == DocumentClass.PAN and ("goods and services tax" in text_lower or "gst registration" in text_lower):
        score *= 0.35

    # Specificity: Balance Sheet vs general Financial Statement
    if target_class == DocumentClass.FINANCIAL_STATEMENT and ("balance sheet" in text_lower and "statement of profit and loss" not in text_lower):
        score *= 0.70

    # Specificity: Work Order / Completion vs general Experience
    if target_class == DocumentClass.EXPERIENCE_CERTIFICATE and ("work order" in text_lower or "purchase order" in text_lower):
        score *= 0.70

    evidence.page_number = best_page
    evidence.snippet = best_snippet or (matched_headings[0] if matched_headings else (matched_keywords[0] if matched_keywords else None))

    return min(1.0, score), evidence


def classify_extracted_text(
    normalized_text: Optional[str],
    raw_text: Optional[str] = None,
    original_filename: Optional[str] = None,
    requirement: Optional[TenderRequirement] = None,
    document_type_hint: Optional[str] = None,
) -> ClassificationResult:
    """
    Main Classification Algorithm:
    - Analyzes normalized & raw text for structural headings, keywords, and statutory identifiers.
    - Evaluates filename and requirement context.
    - Determines detected class, confidence score (0.00-1.00), provenance page, and review requirement.
    - Accurately handles UNKNOWN for ambiguous / low-evidence text without forced guessing.
    """
    text = (normalized_text or "").strip()
    rtext = raw_text or text
    fname = (original_filename or "").lower()
    expected_type = derive_expected_document_type(requirement, document_type_hint)

    # If text is empty or insufficient (< 15 characters without whitespace)
    non_ws_count = len(re.sub(r"\s+", "", text))
    if non_ws_count < 15:
        reason = "Extracted text is empty or contains insufficient legible content for classification."
        return ClassificationResult(
            detected_document_type=DocumentClass.UNKNOWN,
            confidence=0.0,
            confidence_level=ClassificationConfidenceLevel.LOW,
            method="RULE_BASED",
            reason=reason,
            evidence_snippet=None,
            page_number=1,
            expected_document_type=expected_type,
            requires_review=True,
        )

    text_lower = text.lower()
    class_scores: Dict[str, Tuple[float, ClassificationEvidence]] = {}

    for doc_class, rules in DOCUMENT_CLASS_RULES.items():
        score, evidence = calculate_class_score(
            text_lower=text_lower,
            raw_text=rtext,
            filename_lower=fname,
            rules=rules,
            expected_type=expected_type,
            target_class=doc_class,
        )
        class_scores[doc_class] = (score, evidence)

    # Find top scoring candidate
    sorted_candidates = sorted(class_scores.items(), key=lambda item: item[1][0], reverse=True)
    top_class, (top_score, top_evidence) = sorted_candidates[0]

    # Threshold evaluation: If top score is below 0.35, classify as UNKNOWN
    if top_score < 0.35:
        reason = "Document text does not match standard procurement document templates or statutory headings."
        return ClassificationResult(
            detected_document_type=DocumentClass.UNKNOWN,
            confidence=round(top_score, 2),
            confidence_level=ClassificationConfidenceLevel.LOW,
            method="RULE_BASED",
            reason=reason,
            evidence_snippet=top_evidence.snippet,
            page_number=top_evidence.page_number,
            expected_document_type=expected_type,
            requires_review=True,
            evidence=top_evidence,
        )

    # Determine confidence level
    if top_score >= 0.80:
        conf_level = ClassificationConfidenceLevel.HIGH
    elif top_score >= 0.55:
        conf_level = ClassificationConfidenceLevel.MEDIUM
    else:
        conf_level = ClassificationConfidenceLevel.LOW

    # Build human-readable explainability reason
    reason_parts = [f"Detected {format_class_name(top_class)}"]
    if top_evidence.heading_matches:
        reason_parts.append(f"from heading '{top_evidence.heading_matches[0]}'")
    if top_evidence.identifier_matches:
        reason_parts.append(f"with identifier '{top_evidence.identifier_matches[0]}'")
    elif top_evidence.keyword_matches:
        reason_parts.append(f"matching keywords ({', '.join(top_evidence.keyword_matches[:2])})")
    if top_evidence.page_number > 1:
        reason_parts.append(f"on page {top_evidence.page_number}")

    # Mismatch checking (Expected vs. Detected)
    requires_review = False
    if conf_level == ClassificationConfidenceLevel.LOW:
        requires_review = True
        reason_parts.append("(Low confidence match)")

    if expected_type and expected_type != top_class and top_class != DocumentClass.UNKNOWN:
        # Check alias equivalence
        is_alias = (
            (expected_type in [DocumentClass.PAN, DocumentClass.PAN_CERTIFICATE] and top_class in [DocumentClass.PAN, DocumentClass.PAN_CERTIFICATE])
            or (expected_type in [DocumentClass.LOCAL_CONTENT_DECLARATION, DocumentClass.LOCAL_CONTENT_CERTIFICATE] and top_class in [DocumentClass.LOCAL_CONTENT_DECLARATION, DocumentClass.LOCAL_CONTENT_CERTIFICATE])
            or (expected_type in [DocumentClass.BLACKLIST_DECLARATION, DocumentClass.NON_BLACKLISTING_DECLARATION] and top_class in [DocumentClass.BLACKLIST_DECLARATION, DocumentClass.NON_BLACKLISTING_DECLARATION])
            or (expected_type in [DocumentClass.TECHNICAL_DOCUMENT, DocumentClass.TECHNICAL_DATASHEET] and top_class in [DocumentClass.TECHNICAL_DOCUMENT, DocumentClass.TECHNICAL_DATASHEET])
        )
        if not is_alias:
            requires_review = True
            reason_parts.append(
                f"(Note: Requirement expected '{format_class_name(expected_type)}' but uploaded document matches '{format_class_name(top_class)}')"
            )

    full_reason = " ".join(reason_parts).strip()

    return ClassificationResult(
        detected_document_type=top_class,
        confidence=round(top_score, 2),
        confidence_level=conf_level,
        method="RULE_BASED",
        reason=full_reason,
        evidence_snippet=top_evidence.snippet,
        page_number=top_evidence.page_number,
        expected_document_type=expected_type,
        requires_review=requires_review,
        evidence=top_evidence,
    )


def execute_document_classification(
    db: Session,
    document_processing: DocumentProcessing,
    bid_document: BidDocument,
) -> DocumentProcessing:
    """
    Executes Part 4D deterministic document classification on an existing DocumentProcessing record.
    Persists detected_document_type, confidence, provenance snippet, page number, and source.
    """
    result = classify_extracted_text(
        normalized_text=document_processing.normalized_text,
        raw_text=document_processing.raw_text,
        original_filename=bid_document.original_filename,
        requirement=bid_document.tender_requirement,
        document_type_hint=bid_document.document_type,
    )

    document_processing.detected_document_type = result.detected_document_type
    document_processing.classification_confidence = result.confidence
    document_processing.classification_method = result.method
    document_processing.classification_reason = result.reason
    document_processing.classification_evidence = result.evidence_snippet
    document_processing.classification_page_number = result.page_number
    document_processing.classification_source = document_processing.extraction_method or ExtractionMethod.NONE
    document_processing.classification_requires_review = result.requires_review

    # Stage Progression
    if result.detected_document_type == DocumentClass.UNKNOWN and result.confidence == 0.0:
        # Document was unreadable / empty text
        document_processing.processing_stage = ProcessingStage.CLASSIFICATION
        document_processing.processing_status = ProcessingStatus.NEEDS_REVIEW
    else:
        document_processing.processing_stage = ProcessingStage.STRUCTURED_EXTRACTION
        if result.requires_review:
            document_processing.processing_status = ProcessingStatus.NEEDS_REVIEW
        elif document_processing.processing_status == ProcessingStatus.PROCESSING:
            document_processing.processing_status = ProcessingStatus.PROCESSING

    logger.info(
        "Document %s classified as '%s' (conf=%.2f, page=%d, review=%s, stage=%s)",
        bid_document.id,
        document_processing.detected_document_type,
        document_processing.classification_confidence or 0.0,
        document_processing.classification_page_number or 1,
        document_processing.classification_requires_review,
        document_processing.processing_stage,
    )

    db.commit()
    db.refresh(document_processing)
    return document_processing
