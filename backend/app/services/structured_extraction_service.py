"""
Structured Entity / Field Extraction Service for Part 4E
Provides deterministic, regex- and label-based extraction of high-signal business,
statutory, financial, and compliance entities across all recognized document classes.

Tracks field-level confidence, page-level provenance, concise evidence snippets,
and conflict/discrepancy detection without external LLM dependencies.
"""

import re
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from app.db.models.document_processing import (
    ClassificationConfidenceLevel,
    DocumentClass,
    DocumentProcessing,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State Code to State Name Mapping (for GSTIN normalization)
# ---------------------------------------------------------------------------
GST_STATE_MAP: Dict[str, str] = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
    "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
    "24": "Gujarat", "25": "Daman and Diu", "26": "Dadra and Nagar Haveli",
    "27": "Maharashtra", "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
    "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman and Nicobar",
    "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh", "97": "Other Territory",
}


# ---------------------------------------------------------------------------
# Centralized Regex Catalog
# ---------------------------------------------------------------------------
GSTIN_REGEX = re.compile(r'\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b')
PAN_REGEX = re.compile(r'\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b')
UDYAM_REGEX = re.compile(r'\b(UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7})\b', re.IGNORECASE)
PERCENTAGE_REGEX = re.compile(r'(\d+(?:\.\d+)?)\s*(?:%|percent)', re.IGNORECASE)
FY_REGEX = re.compile(r'\b(?:FY\s*)?(20\d{2})\s*[-/]\s*(?:20)?(\d{2})\b', re.IGNORECASE)
UDIN_REGEX = re.compile(r'\b(\d{2}[A-Z0-9]{6}[A-Z0-9]{10})\b', re.IGNORECASE)

DATE_PATTERNS = [
    # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    (re.compile(r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b'), "%d/%m/%Y"),
    # YYYY-MM-DD, YYYY/MM/DD
    (re.compile(r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b'), "%Y-%m-%d"),
    # DD Month YYYY (e.g. 15 August 2025, 15th Aug 2024)
    (re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})\b'), "textual"),
]

MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12
}


# ---------------------------------------------------------------------------
# Data Transfer Object for Single Field Extraction
# ---------------------------------------------------------------------------
@dataclass
class ExtractedField:
    value: Any
    confidence: float
    evidence: str
    page: int = 1
    is_conflict: bool = False
    conflict_values: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "value": self.value,
            "confidence": round(self.confidence, 2),
            "evidence": self.evidence,
            "page": self.page,
        }
        if self.is_conflict:
            res["is_conflict"] = True
            res["conflict_values"] = self.conflict_values
        return res


@dataclass
class StructuredExtractionResult:
    document_type: str
    fields: Dict[str, ExtractedField] = field(default_factory=dict)
    overall_confidence: float = 1.0
    requires_review: bool = False
    review_reasons: List[str] = field(default_factory=list)
    extraction_method: str = "RULE_BASED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_type": self.document_type,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "overall_confidence": round(self.overall_confidence, 2),
            "requires_review": self.requires_review,
            "review_reasons": self.review_reasons,
            "extraction_method": self.extraction_method,
        }


# ---------------------------------------------------------------------------
# Helper Extraction & Normalization Utilities
# ---------------------------------------------------------------------------
def normalize_date_string(date_str: str) -> Optional[str]:
    """
    Normalizes a variety of date formats to ISO YYYY-MM-DD.
    Returns None if the string cannot be parsed unambiguously.
    """
    if not date_str:
        return None
    
    clean_str = date_str.strip()
    
    # Try DD/MM/YYYY or DD-MM-YYYY
    match_dmy = re.search(r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b', clean_str)
    if match_dmy:
        d, m, y = int(match_dmy.group(1)), int(match_dmy.group(2)), int(match_dmy.group(3))
        try:
            dt = datetime(y, m, d)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Try YYYY-MM-DD or YYYY/MM/DD
    match_ymd = re.search(r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b', clean_str)
    if match_ymd:
        y, m, d = int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3))
        try:
            dt = datetime(y, m, d)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Try DD Month YYYY (e.g. 15 August 2025)
    match_textual = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})\b', clean_str)
    if match_textual:
        d = int(match_textual.group(1))
        m_name = match_textual.group(2).lower()
        y = int(match_textual.group(3))
        m = MONTH_MAP.get(m_name)
        if m:
            try:
                dt = datetime(y, m, d)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

    return None


def parse_indian_currency_to_number(amount_text: str) -> Optional[float]:
    """
    Parses Indian currency phrases into numeric float values.
    Supports Crore, Crores, Lakh, Lakhs, Thousand, and standard comma notation.
    Examples:
      - 'Rs. 5,00,00,000' -> 50000000.0
      - '5 Crore' -> 50000000.0
      - '5.26 Crores' -> 52600000.0
      - '45 Lakhs' -> 4500000.0
      - 'Rs. 85,00,000' -> 8500000.0
    """
    if not amount_text:
        return None

    clean = amount_text.strip()
    
    # 1. Match 'X.XX Crore/Crores/Cr'
    match_cr = re.search(r'([\d,]+(?:\.\d+)?)\s*(?:Crores?|Cr)\b', clean, re.IGNORECASE)
    if match_cr:
        num_part = float(match_cr.group(1).replace(",", ""))
        return round(num_part * 10000000.0, 2)

    # 2. Match 'X.XX Lakh/Lakhs/Lac/Lacs'
    match_lakh = re.search(r'([\d,]+(?:\.\d+)?)\s*(?:Lakhs?|Lacs?|Lac)\b', clean, re.IGNORECASE)
    if match_lakh:
        num_part = float(match_lakh.group(1).replace(",", ""))
        return round(num_part * 100000.0, 2)

    # 3. Match 'X.XX Thousand/k'
    match_th = re.search(r'([\d,]+(?:\.\d+)?)\s*(?:Thousands?|k)\b', clean, re.IGNORECASE)
    if match_th:
        num_part = float(match_th.group(1).replace(",", ""))
        return round(num_part * 1000.0, 2)

    # 4. Explicit Currency Prefix Match: e.g. Rs. 4,50,00,000 or INR 5000000
    curr_match = re.search(r'(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)', clean, re.IGNORECASE)
    if curr_match:
        try:
            val_str = curr_match.group(1).replace(",", "")
            return float(val_str)
        except ValueError:
            pass

    # 5. Comma formatted numbers (at least one comma): '5,00,00,000' or '85,00,000'
    match_comma = re.search(r'\b([\d]{1,3}(?:,\d{2,3})+(?:\.\d+)?)\b', clean)
    if match_comma:
        try:
            val_str = match_comma.group(1).replace(",", "")
            return float(val_str)
        except ValueError:
            pass

    # 6. Raw standalone numbers
    match_std = re.search(r'\b([\d]+(?:\.\d+)?)\b', clean)
    if match_std:
        try:
            return float(match_std.group(1))
        except ValueError:
            pass

    return None


def get_pages_from_text(text: str) -> List[Tuple[int, str]]:
    """
    Splits text into pages based on standard '--- Page X ---' delimiters.
    Returns list of (page_number, page_text).
    """
    if not text:
        return []

    page_splits = re.split(r'--- Page (\d+) ---', text)
    if len(page_splits) > 1:
        pages: List[Tuple[int, str]] = []
        # page_splits[0] is pre-page 1 (usually empty), then (page_num, content), ...
        idx = 1
        while idx < len(page_splits):
            try:
                p_num = int(page_splits[idx])
                p_content = page_splits[idx + 1] if idx + 1 < len(page_splits) else ""
                pages.append((p_num, p_content))
            except ValueError:
                pass
            idx += 2
        if pages:
            return pages

    return [(1, text)]


def find_page_for_snippet(pages: List[Tuple[int, str]], snippet: str) -> int:
    """Finds the 1-indexed page number containing the snippet."""
    if not snippet:
        return 1
    for p_num, p_text in pages:
        if snippet in p_text or snippet[:20] in p_text:
            return p_num
    return 1


def extract_labeled_value(
    text: str,
    labels: List[str],
    max_chars: int = 150,
) -> Optional[Tuple[str, str]]:
    """
    Extracts the value following a label in text.
    Returns (cleaned_value, evidence_snippet) if found.
    """
    for lbl in labels:
        # Match label followed by optional colon, dash, equals, whitespace
        pattern = re.compile(
            rf'(?:^|\n|[;•\-])\s*{re.escape(lbl)}\s*[:\-=\t]\s*([^\n\r]+)',
            re.IGNORECASE,
        )
        m = pattern.search(text)
        if m:
            val = m.group(1).strip()
            # Trim trailing punctuation / metadata
            val = re.sub(r'[\t;]+.*$', '', val).strip()
            if val and len(val) <= max_chars:
                evidence = m.group(0).strip()
                return val, evidence
    return None


# ---------------------------------------------------------------------------
# Document-Specific Extractors
# ---------------------------------------------------------------------------

def extract_gst_certificate(
    text: str,
    pages: List[Tuple[int, str]],
) -> StructuredExtractionResult:
    """
    Extracts structured fields from a GST Certificate:
    - gstin, legal_name, trade_name, constitution_of_business,
      registration_date, principal_place_of_business, state, status_text
    """
    result = StructuredExtractionResult(document_type=DocumentClass.GST_CERTIFICATE)
    
    # 1. GSTIN Extraction & Validation
    gstin_matches = GSTIN_REGEX.findall(text.upper())
    if gstin_matches:
        unique_gstins = list(dict.fromkeys(gstin_matches))
        primary_gstin = unique_gstins[0]
        page = find_page_for_snippet(pages, primary_gstin)
        
        is_conflict = len(unique_gstins) > 1
        conf = 0.98 if not is_conflict else 0.65
        evidence = f"GSTIN: {primary_gstin}"
        
        result.fields["gstin"] = ExtractedField(
            value=primary_gstin,
            confidence=conf,
            evidence=evidence,
            page=page,
            is_conflict=is_conflict,
            conflict_values=unique_gstins[1:] if is_conflict else [],
        )

        if is_conflict:
            result.requires_review = True
            result.review_reasons.append(f"Multiple conflicting GSTIN numbers detected: {', '.join(unique_gstins)}")

        # State derivation from GSTIN prefix
        state_code = primary_gstin[:2]
        if state_code in GST_STATE_MAP:
            result.fields["state"] = ExtractedField(
                value=GST_STATE_MAP[state_code],
                confidence=0.95,
                evidence=f"Derived from GSTIN prefix {state_code}",
                page=page,
            )
    else:
        result.requires_review = True
        result.review_reasons.append("Mandatory GSTIN not found in document text.")

    # 2. Legal Business Name
    legal_match = extract_labeled_value(
        text,
        ["Legal Name", "Legal Name of Business", "Name of Business", "Legal Name of Taxable Person"],
    )
    if legal_match:
        val, ev = legal_match
        result.fields["legal_name"] = ExtractedField(
            value=val,
            confidence=0.90,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )
    else:
        # Fallback heuristic: look for Private Limited / Ltd enterprise line
        comp_match = re.search(r'\b([A-Z][A-Za-z0-9\s,\.&]{3,50}(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Limited|LLP|Corporation))\b', text)
        if comp_match:
            val = comp_match.group(1).strip()
            result.fields["legal_name"] = ExtractedField(
                value=val,
                confidence=0.70,
                evidence=f"Entity match: {val}",
                page=find_page_for_snippet(pages, val),
            )
        else:
            result.requires_review = True
            result.review_reasons.append("Legal business name could not be reliably extracted.")

    # 3. Trade Name
    trade_match = extract_labeled_value(text, ["Trade Name", "Trade Name, if any"])
    if trade_match:
        val, ev = trade_match
        result.fields["trade_name"] = ExtractedField(
            value=val,
            confidence=0.88,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    # 4. Constitution of Business
    const_match = extract_labeled_value(
        text,
        ["Constitution of Business", "Constitution", "Type of Business"],
    )
    if const_match:
        val, ev = const_match
        result.fields["constitution_of_business"] = ExtractedField(
            value=val,
            confidence=0.90,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )
    else:
        # Common standard constitutions
        for const in ["Private Limited Company", "Public Limited Company", "Partnership", "Proprietorship", "Limited Liability Partnership"]:
            if re.search(rf'\b{re.escape(const)}\b', text, re.IGNORECASE):
                result.fields["constitution_of_business"] = ExtractedField(
                    value=const,
                    confidence=0.80,
                    evidence=f"Matched constitution term '{const}'",
                    page=find_page_for_snippet(pages, const),
                )
                break

    # 5. Registration Date
    reg_match = extract_labeled_value(
        text,
        ["Date of Registration", "Registration Date", "Date of Liability", "Date of Issue"],
    )
    if reg_match:
        val, ev = reg_match
        norm_date = normalize_date_string(val) or val
        result.fields["registration_date"] = ExtractedField(
            value=norm_date,
            confidence=0.90 if norm_date != val else 0.75,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    # 6. Principal Place of Business / Address
    addr_match = extract_labeled_value(
        text,
        ["Principal Place of Business", "Address of Principal Place", "Principal Address"],
        max_chars=250,
    )
    if addr_match:
        val, ev = addr_match
        result.fields["principal_place_of_business"] = ExtractedField(
            value=val,
            confidence=0.85,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    # Calculate overall confidence
    confidences = [f.confidence for f in result.fields.values()]
    result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.30
    return result


def extract_pan_card(
    text: str,
    pages: List[Tuple[int, str]],
) -> StructuredExtractionResult:
    """
    Extracts structured fields from a PAN card:
    - pan_number, name, father_name, date_of_birth
    """
    result = StructuredExtractionResult(document_type=DocumentClass.PAN)

    # 1. PAN Number
    pan_matches = PAN_REGEX.findall(text.upper())
    # Exclude matches that are obviously part of a longer GSTIN (e.g. middle 10 chars of 15-char GSTIN)
    standalone_pans: List[str] = []
    for p in pan_matches:
        # Check if this PAN is contained in a 15-char GSTIN nearby
        is_gstin_part = False
        for g in GSTIN_REGEX.findall(text.upper()):
            if p in g and len(g) == 15:
                is_gstin_part = True
                break
        if not is_gstin_part:
            standalone_pans.append(p)

    candidate_pans = standalone_pans if standalone_pans else pan_matches
    if candidate_pans:
        unique_pans = list(dict.fromkeys(candidate_pans))
        primary_pan = unique_pans[0]
        page = find_page_for_snippet(pages, primary_pan)
        
        is_conflict = len(unique_pans) > 1
        conf = 0.98 if not is_conflict else 0.65
        
        result.fields["pan_number"] = ExtractedField(
            value=primary_pan,
            confidence=conf,
            evidence=f"PAN: {primary_pan}",
            page=page,
            is_conflict=is_conflict,
            conflict_values=unique_pans[1:] if is_conflict else [],
        )

        if is_conflict:
            result.requires_review = True
            result.review_reasons.append(f"Multiple conflicting PAN numbers detected: {', '.join(unique_pans)}")
    else:
        result.requires_review = True
        result.review_reasons.append("Mandatory PAN number pattern not found in document text.")

    # 2. Name
    name_match = extract_labeled_value(text, ["Name", "Cardholder Name", "Full Name"])
    if name_match:
        val, ev = name_match
        result.fields["name"] = ExtractedField(
            value=val,
            confidence=0.88,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )
    else:
        # Look for uppercase name line heuristic in PAN format
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if any(marker in line.upper() for marker in ["INCOME TAX DEPARTMENT", "GOVT. OF INDIA", "PERMANENT ACCOUNT NUMBER"]):
                # Next non-empty lines might be Name
                for next_line in lines[idx+1:idx+4]:
                    clean_l = next_line.strip()
                    if re.match(r'^[A-Z\s\.]{3,40}$', clean_l) and not any(k in clean_l for k in ["INCOME", "TAX", "GOVT", "INDIA", "PAN", "FATHER"]):
                        result.fields["name"] = ExtractedField(
                            value=clean_l,
                            confidence=0.75,
                            evidence=f"Name line: {clean_l}",
                            page=find_page_for_snippet(pages, clean_l),
                        )
                        break
                if "name" in result.fields:
                    break

    # 3. Father's Name
    father_match = extract_labeled_value(text, ["Father's Name", "Father Name"])
    if father_match:
        val, ev = father_match
        result.fields["father_name"] = ExtractedField(
            value=val,
            confidence=0.85,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    # 4. Date of Birth / Incorporation
    dob_match = extract_labeled_value(text, ["Date of Birth", "DOB", "Date of Incorporation"])
    if dob_match:
        val, ev = dob_match
        norm_date = normalize_date_string(val) or val
        result.fields["date_of_birth"] = ExtractedField(
            value=norm_date,
            confidence=0.90 if norm_date != val else 0.70,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )
    else:
        # General date search on PAN
        date_candidates = re.findall(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})\b', text)
        if date_candidates:
            raw_d = date_candidates[0]
            norm_d = normalize_date_string(raw_d) or raw_d
            result.fields["date_of_birth"] = ExtractedField(
                value=norm_d,
                confidence=0.75,
                evidence=f"Date match: {raw_d}",
                page=find_page_for_snippet(pages, raw_d),
            )

    confidences = [f.confidence for f in result.fields.values()]
    result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.30
    return result


def extract_udyam_certificate(
    text: str,
    pages: List[Tuple[int, str]],
) -> StructuredExtractionResult:
    """
    Extracts structured fields from an Udyam MSME Registration Certificate:
    - udyam_registration_number, enterprise_name, organization_type,
      major_activity, enterprise_classification, registration_date, official_address
    """
    result = StructuredExtractionResult(document_type=DocumentClass.UDYAM_CERTIFICATE)

    # 1. Udyam Registration Number
    udyam_matches = UDYAM_REGEX.findall(text.upper())
    if udyam_matches:
        unique_udyams = list(dict.fromkeys(udyam_matches))
        primary_udyam = unique_udyams[0]
        page = find_page_for_snippet(pages, primary_udyam)

        is_conflict = len(unique_udyams) > 1
        conf = 0.98 if not is_conflict else 0.65
        
        result.fields["udyam_registration_number"] = ExtractedField(
            value=primary_udyam,
            confidence=conf,
            evidence=f"UDYAM: {primary_udyam}",
            page=page,
            is_conflict=is_conflict,
            conflict_values=unique_udyams[1:] if is_conflict else [],
        )

        if is_conflict:
            result.requires_review = True
            result.review_reasons.append(f"Multiple conflicting Udyam numbers detected: {', '.join(unique_udyams)}")
    else:
        result.requires_review = True
        result.review_reasons.append("Mandatory Udyam registration number not found in document text.")

    # 2. Enterprise Name
    ent_match = extract_labeled_value(
        text,
        ["NAME OF ENTERPRISE", "Name of Enterprise", "Enterprise Name"],
    )
    if ent_match:
        val, ev = ent_match
        result.fields["enterprise_name"] = ExtractedField(
            value=val,
            confidence=0.92,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )
    else:
        # Heuristic search
        comp_match = re.search(r'\b([A-Z][A-Za-z0-9\s,\.&]{3,50}(?:Solutions|Systems|Technologies|Enterprises|Infra|Industries))\b', text)
        if comp_match:
            val = comp_match.group(1).strip()
            result.fields["enterprise_name"] = ExtractedField(
                value=val,
                confidence=0.70,
                evidence=f"Enterprise name heuristic: {val}",
                page=find_page_for_snippet(pages, val),
            )

    # 3. Enterprise Classification (Micro / Small / Medium)
    class_match = extract_labeled_value(
        text,
        ["ENTERPRISE TYPE", "Enterprise Type", "Classification", "Type of Enterprise"],
    )
    if class_match:
        val, ev = class_match
        norm_class = val.upper()
        result.fields["enterprise_classification"] = ExtractedField(
            value=norm_class,
            confidence=0.95,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )
    else:
        for cl in ["MICRO", "SMALL", "MEDIUM"]:
            if re.search(rf'\b{cl}\b', text, re.IGNORECASE):
                result.fields["enterprise_classification"] = ExtractedField(
                    value=cl,
                    confidence=0.85,
                    evidence=f"Matched enterprise class '{cl}'",
                    page=find_page_for_snippet(pages, cl),
                )
                break

    # 4. Major Activity (Manufacturing / Services / Trading)
    act_match = extract_labeled_value(
        text,
        ["MAJOR ACTIVITY", "Major Activity", "Activity"],
    )
    if act_match:
        val, ev = act_match
        result.fields["major_activity"] = ExtractedField(
            value=val.upper(),
            confidence=0.92,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )
    else:
        for act in ["MANUFACTURING", "SERVICES", "TRADING"]:
            if re.search(rf'\b{act}\b', text, re.IGNORECASE):
                result.fields["major_activity"] = ExtractedField(
                    value=act,
                    confidence=0.82,
                    evidence=f"Matched activity '{act}'",
                    page=find_page_for_snippet(pages, act),
                )
                break

    # 5. Registration Date
    date_match = extract_labeled_value(
        text,
        ["DATE OF UDYAM REGISTRATION", "Date of Registration", "DATE OF INCORPORATION", "Registration Date"],
    )
    if date_match:
        val, ev = date_match
        norm_d = normalize_date_string(val) or val
        result.fields["registration_date"] = ExtractedField(
            value=norm_d,
            confidence=0.90 if norm_d != val else 0.75,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    # 6. Official Address
    addr_match = extract_labeled_value(
        text,
        ["OFFICIAL ADDRESS OF ENTERPRISE", "Official Address", "Address of Enterprise"],
        max_chars=250,
    )
    if addr_match:
        val, ev = addr_match
        result.fields["official_address"] = ExtractedField(
            value=val,
            confidence=0.85,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    confidences = [f.confidence for f in result.fields.values()]
    result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.30
    return result


def extract_oem_authorization(
    text: str,
    pages: List[Tuple[int, str]],
) -> StructuredExtractionResult:
    """
    Extracts structured fields from an OEM Authorization Letter (MAF):
    - oem_name, authorized_entity, authorization_date, valid_from, valid_until,
      product_or_scope, reference_number, signatory_name
    """
    result = StructuredExtractionResult(document_type=DocumentClass.OEM_AUTHORIZATION)

    # 1. Reference Number
    ref_match = extract_labeled_value(
        text,
        ["Ref", "Ref No", "Reference Number", "Authorization Ref", "Letter Ref"],
    )
    if ref_match:
        val, ev = ref_match
        result.fields["reference_number"] = ExtractedField(
            value=val,
            confidence=0.90,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    # 2. OEM Name
    oem_match = re.search(
        r'(?:We|From)\s*,\s*([A-Za-z0-9\s,\.&]{3,60}?)(?:,|\s+)(?:Original Equipment Manufacturer|OEM|hereby authorize)',
        text,
        re.IGNORECASE,
    )
    if oem_match:
        val = oem_match.group(1).strip()
        result.fields["oem_name"] = ExtractedField(
            value=val,
            confidence=0.88,
            evidence=oem_match.group(0).strip(),
            page=find_page_for_snippet(pages, val),
        )
    else:
        oem_lbl = extract_labeled_value(text, ["OEM Name", "Manufacturer", "Principal Company"])
        if oem_lbl:
            val, ev = oem_lbl
            result.fields["oem_name"] = ExtractedField(
                value=val,
                confidence=0.85,
                evidence=ev,
                page=find_page_for_snippet(pages, ev),
            )

    # 3. Authorized Entity (Bidder/Partner)
    auth_match = re.search(
        r'(?:authorize|authorized partner|certify that)\s+(?:M/s\s+|Messrs\s+)?([A-Za-z0-9\s,\.&]{3,60}?)(?:\s+as our|\s+to submit|\s+to quote|\s+to bid)',
        text,
        re.IGNORECASE,
    )
    if auth_match:
        val = auth_match.group(1).strip()
        result.fields["authorized_entity"] = ExtractedField(
            value=val,
            confidence=0.86,
            evidence=auth_match.group(0).strip(),
            page=find_page_for_snippet(pages, val),
        )
    else:
        partner_lbl = extract_labeled_value(text, ["Authorized Partner", "Authorized Entity", "Reseller", "Bidder Name"])
        if partner_lbl:
            val, ev = partner_lbl
            result.fields["authorized_entity"] = ExtractedField(
                value=val,
                confidence=0.82,
                evidence=ev,
                page=find_page_for_snippet(pages, ev),
            )

    # 4. Tender / Scope Reference
    scope_match = re.search(r'(?:Tender|GeM Tender|Bid ID|Tender ID|Ref No)\s*[:\-]?\s*([A-Za-z0-9\/\-_]{5,40})', text, re.IGNORECASE)
    if scope_match:
        val = scope_match.group(1).strip()
        result.fields["product_or_scope"] = ExtractedField(
            value=val,
            confidence=0.85,
            evidence=scope_match.group(0).strip(),
            page=find_page_for_snippet(pages, val),
        )

    # 5. Authorization / Issue Date
    date_match = extract_labeled_value(text, ["Date", "Dated", "Issue Date", "Authorization Date"])
    if date_match:
        val, ev = date_match
        norm_d = normalize_date_string(val) or val
        result.fields["authorization_date"] = ExtractedField(
            value=norm_d,
            confidence=0.90 if norm_d != val else 0.70,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    # 6. Validity Period
    val_match = re.search(r'valid\s+(?:until|up to|till)\s+([A-Za-z0-9\/\-\s]{5,25})', text, re.IGNORECASE)
    if val_match:
        val_raw = val_match.group(1).strip()
        norm_v = normalize_date_string(val_raw) or val_raw
        result.fields["valid_until"] = ExtractedField(
            value=norm_v,
            confidence=0.82,
            evidence=val_match.group(0).strip(),
            page=find_page_for_snippet(pages, val_raw),
        )

    # 7. Signatory
    sig_match = extract_labeled_value(text, ["Authorized Signatory", "Signatory", "Signature"])
    if sig_match:
        val, ev = sig_match
        result.fields["signatory_name"] = ExtractedField(
            value=val,
            confidence=0.80,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    confidences = [f.confidence for f in result.fields.values()]
    result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.40
    return result


def extract_turnover_certificate(
    text: str,
    pages: List[Tuple[int, str]],
) -> StructuredExtractionResult:
    """
    Extracts structured fields from a Turnover Certificate (CA certified):
    - organization_name, financial_years, annual_turnover_values,
      average_annual_turnover, certificate_date, chartered_accountant_name, membership_number, udin
    """
    result = StructuredExtractionResult(document_type=DocumentClass.TURNOVER_CERTIFICATE)

    # 1. Organization Name
    org_match = re.search(r'(?:certify that|turnover of)\s+(?:M/s\s+|Messrs\s+)?([A-Za-z0-9\s,\.&]{3,60}?)(?:\s+has achieved|\s+is as follows|\s+having PAN)', text, re.IGNORECASE)
    if org_match:
        val = org_match.group(1).strip()
        result.fields["organization_name"] = ExtractedField(
            value=val,
            confidence=0.88,
            evidence=org_match.group(0).strip(),
            page=find_page_for_snippet(pages, val),
        )
    else:
        lbl = extract_labeled_value(text, ["Name of Firm", "Company Name", "Client Name"])
        if lbl:
            val, ev = lbl
            result.fields["organization_name"] = ExtractedField(
                value=val,
                confidence=0.82,
                evidence=ev,
                page=find_page_for_snippet(pages, ev),
            )

    # 2. Extract FY-specific turnover values (e.g. FY 2022-23: Rs. 4,50,00,000)
    annual_values: Dict[str, float] = {}
    lines = text.splitlines()
    for line in lines:
        fy_m = FY_REGEX.search(line)
        if fy_m:
            fy_label = f"{fy_m.group(1)}-{fy_m.group(2)}"
            # Strip out the matched FY substring before parsing the currency amount!
            line_without_fy = line[:fy_m.start()] + line[fy_m.end():]
            parsed_amt = parse_indian_currency_to_number(line_without_fy)
            if parsed_amt is not None and parsed_amt > 0:
                annual_values[fy_label] = parsed_amt

    if annual_values:
        result.fields["annual_turnover_values"] = ExtractedField(
            value=annual_values,
            confidence=0.92,
            evidence=f"Extracted {len(annual_values)} annual turnover records ({', '.join(annual_values.keys())})",
            page=1,
        )
        result.fields["financial_years"] = ExtractedField(
            value=list(annual_values.keys()),
            confidence=0.95,
            evidence=f"Financial Years: {', '.join(annual_values.keys())}",
            page=1,
        )

    # 3. Average Annual Turnover
    avg_match = re.search(r'(?:Average|Avg\.?)\s*(?:Annual\s*)?Turnover\s*[:\-]?\s*([^\n\r]+)', text, re.IGNORECASE)
    if avg_match:
        raw_avg_str = avg_match.group(1).strip()
        parsed_avg = parse_indian_currency_to_number(raw_avg_str)
        if parsed_avg is not None:
            result.fields["average_annual_turnover"] = ExtractedField(
                value=parsed_avg,
                confidence=0.92,
                evidence=avg_match.group(0).strip(),
                page=find_page_for_snippet(pages, raw_avg_str),
            )

    # 4. UDIN Extraction & Validation
    udin_match = UDIN_REGEX.search(text.upper())
    if udin_match:
        udin_val = udin_match.group(1).strip()
        result.fields["udin"] = ExtractedField(
            value=udin_val,
            confidence=0.95,
            evidence=f"UDIN: {udin_val}",
            page=find_page_for_snippet(pages, udin_val),
        )

    # 5. CA Membership Number
    mem_match = re.search(r'(?:Membership\s*(?:No\.?|Number)|M\.?\s*No\.?)\s*[:\-]?\s*([0-9]{4,8})\b', text, re.IGNORECASE)
    if mem_match:
        mem_val = mem_match.group(1).strip()
        result.fields["membership_number"] = ExtractedField(
            value=mem_val,
            confidence=0.90,
            evidence=mem_match.group(0).strip(),
            page=find_page_for_snippet(pages, mem_val),
        )

    # 6. CA Name
    ca_match = re.search(r'(?:Chartered Accountant|For\s+[A-Za-z\s]+Chartered Accountants)\s*[:\-]?\s*([A-Za-z\s\.]+)', text, re.IGNORECASE)
    if ca_match:
        ca_val = ca_match.group(1).strip()
        if len(ca_val) < 50:
            result.fields["chartered_accountant_name"] = ExtractedField(
                value=ca_val,
                confidence=0.82,
                evidence=ca_match.group(0).strip(),
                page=find_page_for_snippet(pages, ca_val),
            )

    # 7. Certificate Date
    date_match = extract_labeled_value(text, ["Date", "Dated", "Place & Date"])
    if date_match:
        val, ev = date_match
        norm_d = normalize_date_string(val) or val
        result.fields["certificate_date"] = ExtractedField(
            value=norm_d,
            confidence=0.88 if norm_d != val else 0.70,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    confidences = [f.confidence for f in result.fields.values()]
    result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.35
    return result


def extract_financial_statement(
    text: str,
    pages: List[Tuple[int, str]],
) -> StructuredExtractionResult:
    """
    Extracts high-level figures from Financial Statements (Balance Sheet / P&L):
    - financial_year, total_revenue, turnover, profit_before_tax, profit_after_tax,
      total_assets, auditor_name
    """
    result = StructuredExtractionResult(document_type=DocumentClass.FINANCIAL_STATEMENT)

    # 1. Financial Year / Period
    fy_match = re.search(r'(?:Balance Sheet as at|Year ended|FY|Financial Year)\s*[:\-]?\s*([0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+[0-9]{4}|20\d{2}[-\/](?:20)?\d{2})', text, re.IGNORECASE)
    if fy_match:
        val = fy_match.group(1).strip()
        result.fields["financial_year"] = ExtractedField(
            value=val,
            confidence=0.88,
            evidence=fy_match.group(0).strip(),
            page=find_page_for_snippet(pages, val),
        )

    # 2. Total Revenue / Revenue from Operations
    rev_match = re.search(r'(?:Total Revenue|Revenue from Operations|Total Income)\s*[:\-]?\s*([^\n\r]+)', text, re.IGNORECASE)
    if rev_match:
        raw_str = rev_match.group(1).strip()
        num_val = parse_indian_currency_to_number(raw_str)
        if num_val is not None:
            result.fields["total_revenue"] = ExtractedField(
                value=num_val,
                confidence=0.88,
                evidence=rev_match.group(0).strip(),
                page=find_page_for_snippet(pages, raw_str),
            )

    # 3. Profit Before Tax (PBT)
    pbt_match = re.search(r'(?:Profit before tax|PBT)\s*[:\-]?\s*([^\n\r]+)', text, re.IGNORECASE)
    if pbt_match:
        raw_str = pbt_match.group(1).strip()
        num_val = parse_indian_currency_to_number(raw_str)
        if num_val is not None:
            result.fields["profit_before_tax"] = ExtractedField(
                value=num_val,
                confidence=0.85,
                evidence=pbt_match.group(0).strip(),
                page=find_page_for_snippet(pages, raw_str),
            )

    # 4. Profit After Tax (PAT) / Net Profit
    pat_match = re.search(r'(?:Profit for the year|Profit after tax|PAT|Net Profit)\s*[:\-]?\s*([^\n\r]+)', text, re.IGNORECASE)
    if pat_match:
        raw_str = pat_match.group(1).strip()
        num_val = parse_indian_currency_to_number(raw_str)
        if num_val is not None:
            result.fields["profit_after_tax"] = ExtractedField(
                value=num_val,
                confidence=0.85,
                evidence=pat_match.group(0).strip(),
                page=find_page_for_snippet(pages, raw_str),
            )

    # 5. Total Assets
    assets_match = re.search(r'(?:Total Assets)\s*[:\-]?\s*([^\n\r]+)', text, re.IGNORECASE)
    if assets_match:
        raw_str = assets_match.group(1).strip()
        num_val = parse_indian_currency_to_number(raw_str)
        if num_val is not None:
            result.fields["total_assets"] = ExtractedField(
                value=num_val,
                confidence=0.85,
                evidence=assets_match.group(0).strip(),
                page=find_page_for_snippet(pages, raw_str),
            )

    # 6. Auditor Name
    aud_match = re.search(r'(?:Independent Auditor\'s Report|Auditor\'s Report|Chartered Accountants)\s*(?:by|for)?\s*([A-Za-z\s,\.&]{3,50})', text, re.IGNORECASE)
    if aud_match:
        val = aud_match.group(1).strip()
        result.fields["auditor_name"] = ExtractedField(
            value=val,
            confidence=0.80,
            evidence=aud_match.group(0).strip(),
            page=find_page_for_snippet(pages, val),
        )

    confidences = [f.confidence for f in result.fields.values()]
    result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.35
    return result


def extract_experience_certificate(
    text: str,
    pages: List[Tuple[int, str]],
) -> StructuredExtractionResult:
    """
    Extracts structured fields from Work Experience / Completion Certificates:
    - organization_name, client_name, project_name, work_order_number,
      start_date, completion_date, contract_value, experience_duration
    """
    result = StructuredExtractionResult(document_type=DocumentClass.EXPERIENCE_CERTIFICATE)

    # 1. Organization / Vendor Name
    org_match = re.search(r'(?:certify that|awarded to)\s+(?:M/s\s+|Messrs\s+)?([A-Za-z0-9\s,\.&]{3,60}?)(?:\s+has successfully|\s+completed the|\s+executed)', text, re.IGNORECASE)
    if org_match:
        val = org_match.group(1).strip()
        result.fields["organization_name"] = ExtractedField(
            value=val,
            confidence=0.88,
            evidence=org_match.group(0).strip(),
            page=find_page_for_snippet(pages, val),
        )

    # 2. Work Order / PO Number
    wo_match = re.search(r'(?:Purchase Order|Work Order|PO|WO|Contract|Agreement)\s*(?:No\.?|Number|Ref)?\s*[:\-]?\s*([A-Za-z0-9\/\-_]{4,35})', text, re.IGNORECASE)
    if wo_match:
        val = wo_match.group(1).strip()
        result.fields["work_order_number"] = ExtractedField(
            value=val,
            confidence=0.90,
            evidence=wo_match.group(0).strip(),
            page=find_page_for_snippet(pages, val),
        )

    # 3. Contract Value
    val_match = re.search(r'(?:Contract Value|Order Value|Total Value|Value of Work|Total Cost)\s*[:\-]?\s*([^\n\r]+)', text, re.IGNORECASE)
    if val_match:
        raw_str = val_match.group(1).strip()
        num_val = parse_indian_currency_to_number(raw_str)
        if num_val is not None:
            result.fields["contract_value"] = ExtractedField(
                value=num_val,
                confidence=0.90,
                evidence=val_match.group(0).strip(),
                page=find_page_for_snippet(pages, raw_str),
            )

    # 4. Completion / Execution Timeline Dates
    comp_match = extract_labeled_value(text, ["Completion Date", "Date of Completion", "Completed On", "Date of Commissioning"])
    if comp_match:
        val, ev = comp_match
        norm_d = normalize_date_string(val) or val
        result.fields["completion_date"] = ExtractedField(
            value=norm_d,
            confidence=0.90 if norm_d != val else 0.75,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    start_match = extract_labeled_value(text, ["Start Date", "Date of Commencement", "Award Date", "Order Date"])
    if start_match:
        val, ev = start_match
        norm_d = normalize_date_string(val) or val
        result.fields["start_date"] = ExtractedField(
            value=norm_d,
            confidence=0.88 if norm_d != val else 0.70,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    # 5. Client / Issuing Authority Name
    client_match = extract_labeled_value(text, ["Client Name", "Issued by", "Department", "Organization"])
    if client_match:
        val, ev = client_match
        result.fields["client_name"] = ExtractedField(
            value=val,
            confidence=0.82,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    confidences = [f.confidence for f in result.fields.values()]
    result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.35
    return result


def extract_local_content_declaration(
    text: str,
    pages: List[Tuple[int, str]],
) -> StructuredExtractionResult:
    """
    Extracts structured fields from a Local Content / Make in India Declaration:
    - local_content_percentage, supplier_class, product_name, declaration_date, certifying_authority
    """
    result = StructuredExtractionResult(document_type=DocumentClass.LOCAL_CONTENT_DECLARATION)

    # 1. Local Content Percentage
    pct_match = re.search(r'(?:Percentage of Local Content|Local Content\s*(?:is|percentage)?)\s*[:\-]?\s*([0-9]{1,3}(?:\.[0-9]+)?)\s*(?:%|percent)', text, re.IGNORECASE)
    if pct_match:
        val_float = float(pct_match.group(1))
        result.fields["local_content_percentage"] = ExtractedField(
            value=val_float,
            confidence=0.95,
            evidence=pct_match.group(0).strip(),
            page=find_page_for_snippet(pages, pct_match.group(0)),
        )
    else:
        # Fallback percentage check
        all_pcts = PERCENTAGE_REGEX.findall(text)
        if all_pcts:
            val_float = float(all_pcts[0][0])
            result.fields["local_content_percentage"] = ExtractedField(
                value=val_float,
                confidence=0.80,
                evidence=f"Percentage match: {val_float}%",
                page=1,
            )
        else:
            result.requires_review = True
            result.review_reasons.append("Local content percentage value not identified in text.")

    # 2. Supplier Class (Class-I / Class-II / Non-Local)
    if re.search(r'Class[\-\s]*I\b', text, re.IGNORECASE):
        result.fields["supplier_class"] = ExtractedField(
            value="Class-I Local Supplier",
            confidence=0.95,
            evidence="Matched 'Class-I Local Supplier'",
            page=1,
        )
    elif re.search(r'Class[\-\s]*II\b', text, re.IGNORECASE):
        result.fields["supplier_class"] = ExtractedField(
            value="Class-II Local Supplier",
            confidence=0.95,
            evidence="Matched 'Class-II Local Supplier'",
            page=1,
        )

    # 3. Declaration Date
    date_match = extract_labeled_value(text, ["Date", "Dated", "Declaration Date"])
    if date_match:
        val, ev = date_match
        norm_d = normalize_date_string(val) or val
        result.fields["declaration_date"] = ExtractedField(
            value=norm_d,
            confidence=0.90 if norm_d != val else 0.70,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    # 4. Signatory / Certifying Authority
    sig_match = extract_labeled_value(text, ["Authorized Signatory", "Signatory", "Name of Signatory"])
    if sig_match:
        val, ev = sig_match
        result.fields["certifying_authority"] = ExtractedField(
            value=val,
            confidence=0.85,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    confidences = [f.confidence for f in result.fields.values()]
    result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.40
    return result


def extract_blacklisting_declaration(
    text: str,
    pages: List[Tuple[int, str]],
) -> StructuredExtractionResult:
    """
    Extracts structured fields from a Non-Blacklisting / Debarment Undertaking:
    - organization_name, blacklisted_status_claim, debarred_status_claim,
      declaration_date, authorized_signatory
    """
    result = StructuredExtractionResult(document_type=DocumentClass.BLACKLIST_DECLARATION)

    # 1. Blacklisted Status Claim
    # In undertaking context: "not been blacklisted" -> claim is False (not blacklisted)
    is_not_blacklisted = bool(re.search(r'(?:not\s+(?:been\s+)?blacklisted|never\s+(?:been\s+)?blacklisted|not\s+debarred|non[\-\s]blacklisting)', text, re.IGNORECASE))
    result.fields["blacklisted_status_claim"] = ExtractedField(
        value=False if is_not_blacklisted else True,
        confidence=0.95 if is_not_blacklisted else 0.70,
        evidence="Self-declaration claim: Firm declares not blacklisted" if is_not_blacklisted else "Potential blacklisting mention found",
        page=1,
    )
    result.fields["debarred_status_claim"] = ExtractedField(
        value=False if is_not_blacklisted else True,
        confidence=0.95 if is_not_blacklisted else 0.70,
        evidence="Self-declaration claim: Firm declares not debarred",
        page=1,
    )

    # 2. Organization Name
    org_match = re.search(r'(?:affirm that|undertake that)\s+(?:M/s\s+|Messrs\s+)?([A-Za-z0-9\s,\.&]{3,60}?)(?:\s+has not|\s+is not|\s+hereby)', text, re.IGNORECASE)
    if org_match:
        val = org_match.group(1).strip()
        result.fields["organization_name"] = ExtractedField(
            value=val,
            confidence=0.88,
            evidence=org_match.group(0).strip(),
            page=find_page_for_snippet(pages, val),
        )

    # 3. Declaration Date
    date_match = extract_labeled_value(text, ["Date", "Dated", "Date of Declaration"])
    if date_match:
        val, ev = date_match
        norm_d = normalize_date_string(val) or val
        result.fields["declaration_date"] = ExtractedField(
            value=norm_d,
            confidence=0.90 if norm_d != val else 0.70,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    # 4. Signatory
    sig_match = extract_labeled_value(text, ["Authorized Signatory", "Signatory", "Name"])
    if sig_match:
        val, ev = sig_match
        result.fields["authorized_signatory"] = ExtractedField(
            value=val,
            confidence=0.85,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    confidences = [f.confidence for f in result.fields.values()]
    result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.40
    return result


def extract_technical_document(
    text: str,
    pages: List[Tuple[int, str]],
) -> StructuredExtractionResult:
    """
    Extracts high-level metadata from Technical Specifications / Brochures:
    - document_title, product_name, model_number, manufacturer, specifications_summary
    """
    result = StructuredExtractionResult(document_type=DocumentClass.TECHNICAL_DOCUMENT)

    # 1. Product / Model Name
    model_match = extract_labeled_value(text, ["Model Number", "Model", "Product Code", "Part Number"])
    if model_match:
        val, ev = model_match
        result.fields["model_number"] = ExtractedField(
            value=val,
            confidence=0.85,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    # 2. Manufacturer
    mfg_match = extract_labeled_value(text, ["Manufacturer", "Make", "Brand", "OEM"])
    if mfg_match:
        val, ev = mfg_match
        result.fields["manufacturer"] = ExtractedField(
            value=val,
            confidence=0.85,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    # 3. Product Name / Title
    title_match = extract_labeled_value(text, ["Product Name", "Item Description", "Technical Specification for"])
    if title_match:
        val, ev = title_match
        result.fields["product_name"] = ExtractedField(
            value=val,
            confidence=0.80,
            evidence=ev,
            page=find_page_for_snippet(pages, ev),
        )

    confidences = [f.confidence for f in result.fields.values()]
    result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.40
    return result


def extract_commercial_document(
    text: str,
    pages: List[Tuple[int, str]],
) -> StructuredExtractionResult:
    """
    Extracts commercial terms / price proposal metadata:
    - quoted_amount, currency, tax_percentage, total_amount, validity_period
    """
    result = StructuredExtractionResult(document_type=DocumentClass.COMMERCIAL_DOCUMENT)

    # 1. Quoted / Total Amount
    amt_match = re.search(r'(?:Total Quoted Bid Price|Total Quoted Amount|Total Bid Amount|Grand Total|Total Quoted Price)\s*[:\-]?\s*([^\n\r]+)', text, re.IGNORECASE)
    if amt_match:
        raw_str = amt_match.group(1).strip()
        num_val = parse_indian_currency_to_number(raw_str)
        if num_val is not None:
            result.fields["quoted_amount"] = ExtractedField(
                value=num_val,
                confidence=0.92,
                evidence=amt_match.group(0).strip(),
                page=find_page_for_snippet(pages, raw_str),
            )
            result.fields["total_amount"] = ExtractedField(
                value=num_val,
                confidence=0.92,
                evidence=amt_match.group(0).strip(),
                page=find_page_for_snippet(pages, raw_str),
            )

    # 2. Currency
    if any(c in text for c in ["INR", "Rs.", "Rs", "₹", "Rupees"]):
        result.fields["currency"] = ExtractedField(
            value="INR",
            confidence=0.98,
            evidence="Detected INR currency token",
            page=1,
        )

    # 3. Tax Percentage (e.g. GST 18%)
    tax_match = re.search(r'(?:GST|Tax)\s*(?:@|Rate|Percentage)?\s*([0-9]{1,2}(?:\.[0-9]+)?)\s*%', text, re.IGNORECASE)
    if tax_match:
        result.fields["tax_percentage"] = ExtractedField(
            value=float(tax_match.group(1)),
            confidence=0.88,
            evidence=tax_match.group(0).strip(),
            page=find_page_for_snippet(pages, tax_match.group(0)),
        )

    # 4. Bid Validity
    val_match = re.search(r'(?:Bid Validity|Validity Period)\s*[:\-]?\s*([^\n\r]+)', text, re.IGNORECASE)
    if val_match:
        val_str = val_match.group(1).strip()
        result.fields["validity_period"] = ExtractedField(
            value=val_str,
            confidence=0.85,
            evidence=val_match.group(0).strip(),
            page=find_page_for_snippet(pages, val_str),
        )

    confidences = [f.confidence for f in result.fields.values()]
    result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.40
    return result


def extract_generic_or_unknown(
    text: str,
    pages: List[Tuple[int, str]],
    document_type: str = DocumentClass.UNKNOWN,
) -> StructuredExtractionResult:
    """
    Generic fallback extractor for OTHER / UNKNOWN document types.
    Flags requires_review = True.
    """
    result = StructuredExtractionResult(
        document_type=document_type,
        requires_review=True,
        review_reasons=[f"Document classified as '{document_type}'. Generic fallback extraction applied."],
    )

    # Generic date search
    date_candidates = re.findall(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})\b', text)
    if date_candidates:
        norm_d = normalize_date_string(date_candidates[0]) or date_candidates[0]
        result.fields["document_date"] = ExtractedField(
            value=norm_d,
            confidence=0.60,
            evidence=f"Date match: {date_candidates[0]}",
            page=find_page_for_snippet(pages, date_candidates[0]),
        )

    result.overall_confidence = 0.40
    return result


# ---------------------------------------------------------------------------
# Master Dispatcher
# ---------------------------------------------------------------------------
EXTRACTOR_ROUTER = {
    DocumentClass.GST_CERTIFICATE: extract_gst_certificate,
    DocumentClass.PAN: extract_pan_card,
    DocumentClass.UDYAM_CERTIFICATE: extract_udyam_certificate,
    DocumentClass.OEM_AUTHORIZATION: extract_oem_authorization,
    DocumentClass.TURNOVER_CERTIFICATE: extract_turnover_certificate,
    DocumentClass.FINANCIAL_STATEMENT: extract_financial_statement,
    DocumentClass.EXPERIENCE_CERTIFICATE: extract_experience_certificate,
    DocumentClass.LOCAL_CONTENT_DECLARATION: extract_local_content_declaration,
    DocumentClass.BLACKLIST_DECLARATION: extract_blacklisting_declaration,
    DocumentClass.TECHNICAL_DOCUMENT: extract_technical_document,
    DocumentClass.COMMERCIAL_DOCUMENT: extract_commercial_document,
}


def extract_structured_entities_from_text(
    text: str,
    document_type: str,
    original_filename: Optional[str] = None,
) -> StructuredExtractionResult:
    """
    Master entry point for deterministic structured entity extraction:
    Routes to the document-specific parser based on detected document type.
    """
    if not text or not text.strip():
        return StructuredExtractionResult(
            document_type=document_type or DocumentClass.UNKNOWN,
            overall_confidence=0.0,
            requires_review=True,
            review_reasons=["Document text is empty or blank. No entities could be extracted."],
        )

    clean_text = text.strip()
    pages = get_pages_from_text(clean_text)

    extractor_func = EXTRACTOR_ROUTER.get(document_type)
    if extractor_func:
        return extractor_func(clean_text, pages)
    else:
        return extract_generic_or_unknown(clean_text, pages, document_type or DocumentClass.UNKNOWN)
