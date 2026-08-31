"""
Document Classification Service for Part 4D: Document Classification
Provides deterministic, explainable, rule-and-pattern-based classification of bid documents
using extracted text signals, regex patterns, headings, requirement context, and filename hints.
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
    ProcessingStage,
    ProcessingStatus,
)
from app.db.models.tender_requirement import TenderRequirement

logger = logging.getLogger(__name__)

# Regular expressions for statutory and procurement identifiers
RE_GSTIN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b")
RE_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]{1}\b")
RE_UDYAM = re.compile(r"\bUDYAM-[A-Z]{2}-\d{2}-\d{7}\b", re.IGNORECASE)
RE_UDIN = re.compile(r"\b(?:UDIN[:\s-]*)?\d{18}\b|\bUDIN\b", re.IGNORECASE)


@dataclass
class ClassificationEvidence:
    heading_matches: List[str] = field(default_factory=list)
    keyword_matches: List[str] = field(default_factory=list)
    identifier_matches: List[str] = field(default_factory=list)
    filename_matches: List[str] = field(default_factory=list)
    requirement_match: Optional[str] = None


@dataclass
class ClassificationResult:
    detected_document_type: str
    confidence: float
    confidence_level: str  # HIGH, MEDIUM, LOW
    method: str  # RULE_BASED
    reason: str
    expected_document_type: Optional[str] = None
    requires_review: bool = False
    evidence: Optional[ClassificationEvidence] = None


# Signal rulebook defining anchor headings, keywords, identifiers, and filename tokens
DOCUMENT_CLASS_RULES = {
    DocumentClass.GST_CERTIFICATE: {
        "headings": [
            "goods and services tax",
            "registration certificate",
            "form gst reg",
            "gst registration certificate",
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
        ],
        "keywords": [
            "father's name",
            "date of birth",
            "signature",
            "pan",
            "photo",
        ],
        "regex": [RE_PAN],
        "filename_tokens": ["pan", "pancard", "pan_card", "pan_document"],
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
    DocumentClass.OEM_AUTHORIZATION: {
        "headings": [
            "manufacturer authorization",
            "manufacturers authorization",
            "manufacturer's authorization",
            "authorization letter",
            "authorisation letter",
            "oem authorization",
            "maf",
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
    DocumentClass.FINANCIAL_STATEMENT: {
        "headings": [
            "balance sheet",
            "statement of profit and loss",
            "profit and loss account",
            "cash flow statement",
            "independent auditor's report",
            "audited financial statements",
            "auditors report",
        ],
        "keywords": [
            "equity and liabilities",
            "current assets",
            "non-current assets",
            "total revenue",
            "net profit",
            "notes forming part of the financial statements",
            "financial year",
            "as at 31st march",
        ],
        "regex": [],
        "filename_tokens": ["financial", "balance_sheet", "pnl", "audited", "pl", "annual_report"],
    },
    DocumentClass.TURNOVER_CERTIFICATE: {
        "headings": [
            "turnover certificate",
            "annual turnover certificate",
            "certificate of turnover",
            "chartered accountant certificate",
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
    DocumentClass.EXPERIENCE_CERTIFICATE: {
        "headings": [
            "experience certificate",
            "work completion certificate",
            "completion certificate",
            "performance certificate",
            "client certificate",
        ],
        "keywords": [
            "satisfactorily completed",
            "successfully completed",
            "satisfactory performance",
            "purchase order",
            "work order",
            "contract value",
            "scope of work",
            "execution of work",
            "date of commencement",
            "date of completion",
        ],
        "regex": [],
        "filename_tokens": ["experience", "completion", "work_order", "po", "past_experience"],
    },
    DocumentClass.LOCAL_CONTENT_DECLARATION: {
        "headings": [
            "make in india declaration",
            "local content declaration",
            "local content certificate",
            "preference to make in india",
            "mii declaration",
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
        "filename_tokens": ["local_content", "make_in_india", "mii", "mii_declaration"],
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
}


def format_class_name(class_str: str) -> str:
    """Formats document class name with statutory acronym capitalization."""
    if not class_str:
        return ""
    acronyms = {"GST": "GST", "PAN": "PAN", "OEM": "OEM", "MAF": "MAF", "MII": "MII", "CA": "CA", "UDYAM": "Udyam"}
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
    if any(k in combined_meta for k in ["oem", "authorization", "authorisation", "maf"]):
        return DocumentClass.OEM_AUTHORIZATION
    if any(k in combined_meta for k in ["turnover", "ca certificate", "udin"]):
        return DocumentClass.TURNOVER_CERTIFICATE
    if any(k in combined_meta for k in ["financial", "balance sheet", "pnl", "audited"]):
        return DocumentClass.FINANCIAL_STATEMENT
    if any(k in combined_meta for k in ["experience", "completion", "work order", "po"]):
        return DocumentClass.EXPERIENCE_CERTIFICATE
    if any(k in combined_meta for k in ["local content", "make in india", "mii"]):
        return DocumentClass.LOCAL_CONTENT_DECLARATION
    if any(k in combined_meta for k in ["blacklist", "debarment", "debar"]):
        return DocumentClass.BLACKLIST_DECLARATION

    return None


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

    # 1. Heading matches
    matched_headings = [h for h in rules["headings"] if h in text_lower]
    if matched_headings:
        evidence.heading_matches = matched_headings
        if has_regex_rules:
            heading_weight = min(0.40, 0.30 + (0.05 * (len(matched_headings) - 1)))
        else:
            heading_weight = min(0.50, 0.40 + (0.05 * (len(matched_headings) - 1)))
        score += heading_weight

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

    # 3. Supporting Keywords
    matched_keywords = [k for k in rules["keywords"] if k in text_lower]
    if matched_keywords:
        evidence.keyword_matches = matched_keywords
        kw_ratio = min(1.0, len(matched_keywords) / max(2, len(rules["keywords"]) / 3))
        if has_regex_rules:
            score += 0.20 * kw_ratio
        else:
            score += 0.35 * kw_ratio

    # 4. Filename Tokens (up to 0.05)
    matched_fn = [fn for fn in rules.get("filename_tokens", []) if fn in filename_lower]
    if matched_fn:
        evidence.filename_matches = matched_fn
        score += 0.05

    # 5. Expected Requirement Alignment (up to 0.10)
    if expected_type and expected_type == target_class:
        evidence.requirement_match = expected_type
        score += 0.10

    # Anti-collision dampening: PAN vs GST
    # A GST certificate often mentions the PAN inside the GSTIN or as PAN number.
    # If the document strongly matches GST headings, dampen PAN score so GST wins.
    if target_class == DocumentClass.PAN and "goods and services tax" in text_lower:
        score *= 0.4

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
    - Determines detected class, confidence score (0.00-1.00), and review requirement.
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
    second_class, (second_score, _) = sorted_candidates[1] if len(sorted_candidates) > 1 else (None, (0.0, None))

    # Threshold evaluation
    # If top score is below 0.35, or if ambiguous with negligible margin
    if top_score < 0.35:
        reason = "Document text does not match standard procurement document templates or statutory headings."
        return ClassificationResult(
            detected_document_type=DocumentClass.UNKNOWN,
            confidence=round(top_score, 2),
            confidence_level=ClassificationConfidenceLevel.LOW,
            method="RULE_BASED",
            reason=reason,
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

    # Mismatch checking (Expected vs. Detected)
    requires_review = False
    if conf_level == ClassificationConfidenceLevel.LOW:
        requires_review = True
        reason_parts.append("(Low confidence match)")

    if expected_type and expected_type != top_class and top_class != DocumentClass.UNKNOWN:
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
    Advances stage from CLASSIFICATION to STRUCTURED_EXTRACTION upon completion.
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
    document_processing.classification_requires_review = result.requires_review

    # Stage Progression
    if result.detected_document_type == DocumentClass.UNKNOWN and result.confidence == 0.0:
        # Document was unreadable / empty text
        document_processing.processing_stage = ProcessingStage.CLASSIFICATION
        document_processing.processing_status = ProcessingStatus.NEEDS_REVIEW
    else:
        # Successful classification -> Advance to STRUCTURED_EXTRACTION (ready for Part 4E)
        document_processing.processing_stage = ProcessingStage.STRUCTURED_EXTRACTION
        if result.requires_review:
            # Document has mismatch or low confidence, mark status as NEEDS_REVIEW without invalidating
            document_processing.processing_status = ProcessingStatus.NEEDS_REVIEW
        elif document_processing.processing_status == ProcessingStatus.PROCESSING:
            document_processing.processing_status = ProcessingStatus.PROCESSING

    logger.info(
        "Document %s classified as '%s' (conf=%.2f, review=%s, stage=%s)",
        bid_document.id,
        document_processing.detected_document_type,
        document_processing.classification_confidence or 0.0,
        document_processing.classification_requires_review,
        document_processing.processing_stage,
    )

    db.commit()
    db.refresh(document_processing)
    return document_processing
