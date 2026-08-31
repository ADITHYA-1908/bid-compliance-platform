"""
Shared Normalization and Field Comparison Utilities for Part 5B, 5C, 5D & 5E
Provides deterministic identifier formatting, corporate name normalization,
date parsing, similarity scoring, percentage parsing, supplier class normalization,
PAN from GSTIN extraction, address token comparison, organization type normalization,
and PAN/CIN entity-type inference.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from app.verification.types import VerificationMatchStatus


# ---------------------------------------------------------------------------
# Identifier Normalizers
# ---------------------------------------------------------------------------

def normalize_identifier(val: Optional[str]) -> str:
    """
    Cleans an alphanumeric identifier by stripping whitespace and converting to uppercase.
    """
    if not val:
        return ""
    return str(val).strip().upper()


def normalize_udyam_number(val: Optional[str]) -> str:
    """
    Cleans and standardizes a Udyam Registration Number into uppercase with consistent hyphens.
    Example: 'udyam - tn - 01 - 0012345' -> 'UDYAM-TN-01-0012345'
    """
    if not val:
        return ""
    cleaned = str(val).strip().upper()
    cleaned = re.sub(r'\s*-\s*', '-', cleaned)
    cleaned = re.sub(r'\s+', '', cleaned)
    return cleaned


def normalize_cin(val: Optional[str]) -> str:
    """
    Cleans and standardizes a Corporate Identification Number (CIN).
    Example: ' u72900tn2018ptc123456 ' -> 'U72900TN2018PTC123456'
    """
    if not val:
        return ""
    cleaned = str(val).strip().upper()
    cleaned = re.sub(r'\s+', '', cleaned)
    return cleaned


def normalize_llpin(val: Optional[str]) -> str:
    """
    Cleans and standardizes an LLP Identification Number (LLPIN).
    Example: ' aaa - 1234 ' -> 'AAA-1234'
    """
    if not val:
        return ""
    cleaned = str(val).strip().upper()
    cleaned = re.sub(r'\s*-\s*', '-', cleaned)
    cleaned = re.sub(r'\s+', '', cleaned)
    return cleaned


def normalize_epfo_code(val: Optional[str]) -> str:
    """
    Cleans and standardizes a 15-character EPFO establishment code.
    Example: ' tnmas 1234567 000 ' -> 'TNMAS1234567000'
    """
    if not val:
        return ""
    cleaned = str(val).strip().upper()
    cleaned = re.sub(r'[\s\-_]+', '', cleaned)
    return cleaned


def normalize_esic_code(val: Optional[str]) -> str:
    """
    Cleans and standardizes a 17-digit numeric ESIC employer code.
    Example: '51-00-123456-000-1001' -> '51001234560001001'
    """
    if not val:
        return ""
    cleaned = str(val).strip()
    cleaned = re.sub(r'[\s\-_]+', '', cleaned)
    return cleaned


def normalize_startup_number(val: Optional[str]) -> str:
    """
    Cleans and standardizes a Startup India / DPIIT recognition number.
    Example: ' dipp 123456 ' -> 'DIPP123456'
    """
    if not val:
        return ""
    cleaned = str(val).strip().upper()
    cleaned = re.sub(r'\s+', '', cleaned)
    return cleaned


def normalize_nsic_number(val: Optional[str]) -> str:
    """
    Cleans and standardizes an NSIC registration number.
    Example: ' nsic - tn - 2025 - 001234 ' -> 'NSIC-TN-2025-001234'
    """
    if not val:
        return ""
    cleaned = str(val).strip().upper()
    cleaned = re.sub(r'\s*-\s*', '-', cleaned)
    cleaned = re.sub(r'\s*/\s*', '/', cleaned)
    cleaned = re.sub(r'\s+', '', cleaned)
    return cleaned


def normalize_bis_number(val: Optional[str]) -> str:
    """
    Cleans and standardizes a BIS registration or license number.
    Example: ' r - 12345678 ' -> 'R-12345678'
    """
    if not val:
        return ""
    cleaned = str(val).strip().upper()
    cleaned = re.sub(r'\s*-\s*', '-', cleaned)
    cleaned = re.sub(r'\s*/\s*', '/', cleaned)
    cleaned = re.sub(r'\s+', '', cleaned)
    return cleaned


# ---------------------------------------------------------------------------
# PAN from GSTIN Extractor (Part 5E)
# ---------------------------------------------------------------------------

def extract_pan_from_gstin(gstin: Optional[str]) -> Optional[str]:
    """
    Extracts the embedded 10-character Permanent Account Number (PAN) from a 15-character Indian GSTIN.
    Format: State Code (2 digits) + PAN (10 chars) + Entity Code (1 digit) + 'Z' + Check Digit (1 char).
    Example: '33ABCDE1234F1Z5' -> 'ABCDE1234F'
    """
    if not gstin:
        return None
    cleaned = normalize_identifier(gstin)
    if len(cleaned) == 15:
        embedded_pan = cleaned[2:12]
        # Basic validation: 5 letters, 4 digits, 1 letter
        if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', embedded_pan):
            return embedded_pan
    return None


# ---------------------------------------------------------------------------
# Organization Type Normalizer (Part 5E)
# ---------------------------------------------------------------------------

_ORG_TYPE_CANONICAL_MAP: List[Tuple[re.Pattern, str]] = [
    (re.compile(r'\b(PRIVATE\s*LIMITED|PVT\.?\s*LTD\.?|PTC|PRIVATE\s*COMPANY)\b', re.IGNORECASE), "PRIVATE_LIMITED"),
    (re.compile(r'\b(LIMITED\s*LIABILITY\s*PARTNERSHIP|L\.?L\.?P\.?)\b', re.IGNORECASE), "LLP"),
    (re.compile(r'\b(PUBLIC\s*LIMITED(\s*COMPANY)?|PUB\.?\s*LTD\.?|PLC|PUBLIC\s*COMPANY|LISTED|\bLIMITED\b|\bLTD\.?\b)\b', re.IGNORECASE), "PUBLIC_LIMITED"),
    (re.compile(r'\b(PARTNERSHIP\s*FIRM|PARTNERSHIP)\b', re.IGNORECASE), "PARTNERSHIP"),
    (re.compile(r'\b(PROPRIETORSHIP|SOLE\s*PROPRIETORSHIP|PROPRIETOR|INDIVIDUAL)\b', re.IGNORECASE), "PROPRIETORSHIP"),
    (re.compile(r'\b(TRUST|PUBLIC\s*TRUST)\b', re.IGNORECASE), "TRUST"),
    (re.compile(r'\b(SOCIETY|COOPERATIVE\s*SOCIETY)\b', re.IGNORECASE), "SOCIETY"),
    (re.compile(r'\b(GOVERNMENT|STATE\s*GOVT|CENTRAL\s*GOVT|PSU)\b', re.IGNORECASE), "GOVERNMENT_PSU"),
]


def normalize_organization_type(val: Optional[str]) -> str:
    """
    Normalizes organizational legal entity types into canonical tokens:
    - 'PRIVATE_LIMITED', 'PUBLIC_LIMITED', 'LLP', 'PARTNERSHIP',
      'PROPRIETORSHIP', 'TRUST', 'SOCIETY', 'GOVERNMENT_PSU', 'OTHER', 'UNKNOWN'
    """
    if not val:
        return "UNKNOWN"

    s = str(val).strip().upper()
    for pattern, canonical in _ORG_TYPE_CANONICAL_MAP:
        if pattern.search(s):
            return canonical

    return "OTHER"


# ---------------------------------------------------------------------------
# Address Comparison (Part 5E)
# ---------------------------------------------------------------------------

def compare_addresses(addr_a: Optional[str], addr_b: Optional[str]) -> Tuple[str, float]:
    """
    Compares two address strings conservatively using token intersection and PIN code checks.
    Returns (VerificationMatchStatus, confidence_score).
    """
    if not addr_a and not addr_b:
        return VerificationMatchStatus.NOT_APPLICABLE, 1.0
    if not addr_a or not addr_b:
        return VerificationMatchStatus.UNKNOWN, 0.50

    def _extract_pin(s: str) -> Optional[str]:
        m = re.search(r'\b([1-9][0-9]{5})\b', s)
        return m.group(1) if m else None

    def _clean_tokens(s: str) -> set:
        cleaned = re.sub(r'[,.\'"\-_/\\()\[\]{}]', ' ', str(s).upper())
        noise = {"INDIA", "ROAD", "STREET", "NAGAR", "FLOOR", "BUILDING", "NO", "PLOT", "PHASE"}
        tokens = set(cleaned.split()) - noise
        return tokens

    pin_a = _extract_pin(addr_a)
    pin_b = _extract_pin(addr_b)

    tokens_a = _clean_tokens(addr_a)
    tokens_b = _clean_tokens(addr_b)

    if not tokens_a or not tokens_b:
        return VerificationMatchStatus.UNKNOWN, 0.50

    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    jaccard = len(intersection) / len(union) if union else 0.0

    # If both have PIN codes and PIN codes differ -> MISMATCH
    if pin_a and pin_b and pin_a != pin_b:
        return VerificationMatchStatus.MISMATCH, 0.0

    if jaccard >= 0.60 or tokens_a == tokens_b:
        return VerificationMatchStatus.MATCH, 1.0
    elif jaccard >= 0.30 or (pin_a and pin_b and pin_a == pin_b):
        return VerificationMatchStatus.PARTIAL_MATCH, 0.85
    else:
        return VerificationMatchStatus.MISMATCH, 0.0


# ---------------------------------------------------------------------------
# Local Content & Supplier Class Normalizers
# ---------------------------------------------------------------------------

def normalize_percentage(val: Any) -> Optional[float]:
    """
    Extracts a clean float percentage from various formats:
    '55%', '55.5 %', 55, 55.0 -> 55.0
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    match = re.search(r'([0-9]+(?:\.[0-9]+)?)', s)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def normalize_supplier_class(val: Optional[str]) -> str:
    """
    Normalizes local content supplier classification:
    - 'Class-I Local Supplier' / 'Class 1' / 'CLASS_I' -> 'CLASS_I'
    - 'Class-II Local Supplier' / 'Class 2' / 'CLASS_II' -> 'CLASS_II'
    - 'Non-Local Supplier' / 'NON_LOCAL' -> 'NON_LOCAL'
    """
    if not val:
        return "UNKNOWN"

    s = str(val).strip().upper()
    if "CLASS-I" in s or "CLASS I" in s or "CLASS_I" in s or "CLASS 1" in s or "CLASS-1" in s:
        return "CLASS_I"
    if "CLASS-II" in s or "CLASS II" in s or "CLASS_II" in s or "CLASS 2" in s or "CLASS-2" in s:
        return "CLASS_II"
    if "NON-LOCAL" in s or "NON LOCAL" in s or "NON_LOCAL" in s:
        return "NON_LOCAL"

    return "UNKNOWN"


def compare_percentages(
    claimed: Optional[float],
    registry: Optional[float],
    tolerance: float = 0.01,
) -> Tuple[str, float]:
    """
    Compares two percentage values.
    Returns (VerificationMatchStatus, confidence).
    """
    if claimed is None or registry is None:
        return VerificationMatchStatus.NOT_APPLICABLE, 1.0

    diff = abs(claimed - registry)
    if diff <= tolerance:
        return VerificationMatchStatus.MATCH, 1.0
    elif diff <= 2.0:  # within 2% margin
        return VerificationMatchStatus.PARTIAL_MATCH, 0.85
    else:
        return VerificationMatchStatus.MISMATCH, 0.0


# ---------------------------------------------------------------------------
# Scope and Product Comparison
# ---------------------------------------------------------------------------

def compare_scope(claimed: Any, registry: Any) -> Tuple[str, float]:
    """
    Compares product name or authorized scope of supply:
    Handles strings, lists, or dictionaries of products.
    """
    if not claimed and not registry:
        return VerificationMatchStatus.NOT_APPLICABLE, 1.0
    if not claimed or not registry:
        return VerificationMatchStatus.NOT_APPLICABLE, 1.0

    def _to_token_set(item: Any) -> set:
        if isinstance(item, list):
            raw = " ".join(str(x) for x in item)
        elif isinstance(item, dict):
            raw = " ".join(f"{k} {v}" for k, v in item.items())
        else:
            raw = str(item)
        cleaned = re.sub(r'[,.\'"\-_/\\()\[\]{}]', ' ', raw.upper())
        return set(cleaned.split())

    tokens_c = _to_token_set(claimed)
    tokens_r = _to_token_set(registry)

    if not tokens_c or not tokens_r:
        return VerificationMatchStatus.NOT_APPLICABLE, 1.0

    intersection = tokens_c.intersection(tokens_r)
    union = tokens_c.union(tokens_r)

    if tokens_c == tokens_r:
        return VerificationMatchStatus.MATCH, 1.0

    is_subset = (tokens_c.issubset(tokens_r) or tokens_r.issubset(tokens_c)) and len(intersection) >= 1
    jaccard = len(intersection) / len(union) if union else 0.0

    if is_subset or jaccard >= 0.50:
        return VerificationMatchStatus.MATCH, 1.0
    elif jaccard >= 0.25 or len(intersection) >= 1:
        return VerificationMatchStatus.PARTIAL_MATCH, 0.85
    else:
        return VerificationMatchStatus.MISMATCH, 0.0


# ---------------------------------------------------------------------------
# Organization Name Normalizer
# ---------------------------------------------------------------------------

_CORPORATE_SUFFIX_REPLACEMENTS = [
    (re.compile(r'\bPVT\.?\s*LTD\.?\b', re.IGNORECASE), "PRIVATE LIMITED"),
    (re.compile(r'\bPRIVATE\s*LTD\.?\b', re.IGNORECASE), "PRIVATE LIMITED"),
    (re.compile(r'\bPVT\s*LIMITED\b', re.IGNORECASE), "PRIVATE LIMITED"),
    (re.compile(r'\bLTD\.?\b', re.IGNORECASE), "LIMITED"),
    (re.compile(r'\bL\.L\.P\.?\b', re.IGNORECASE), "LLP"),
    (re.compile(r'\bLIMITED\s+LIABILITY\s+PARTNERSHIP\b', re.IGNORECASE), "LLP"),
    (re.compile(r'\bINC\.?\b', re.IGNORECASE), "INCORPORATED"),
    (re.compile(r'\bCORP\.?\b', re.IGNORECASE), "CORPORATION"),
    (re.compile(r'\bCO\.?\b', re.IGNORECASE), "COMPANY"),
]

_PUNCTUATION_STRIP_REGEX = re.compile(r'[,.\'"\-_/\\()\[\]{}]')


def normalize_org_name(name: Optional[str]) -> str:
    """
    Cleans and standardizes an organization or individual business name:
    - Converts to uppercase
    - Standardizes legal entity suffixes (e.g. PVT LTD -> PRIVATE LIMITED)
    - Strips non-essential punctuation
    - Normalizes multi-spaces
    """
    if not name:
        return ""

    text = str(name).strip().upper()

    # Normalize legal suffixes
    for pattern, replacement in _CORPORATE_SUFFIX_REPLACEMENTS:
        text = pattern.sub(replacement, text)

    # Strip punctuation
    text = _PUNCTUATION_STRIP_REGEX.sub(' ', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def compare_names(claimed: Optional[str], registry: Optional[str]) -> Tuple[str, float]:
    """
    Compares a claimed organization or individual name against a canonical registry name.
    Returns (VerificationMatchStatus, confidence_score).

    Match criteria:
    - If claimed is empty or not provided -> (NOT_APPLICABLE, 1.0)
    - Exact match after normalization -> (MATCH, 1.0)
    - Token subset / high token overlap -> (PARTIAL_MATCH, 0.90)
    - Distinct names -> (MISMATCH, 0.0)
    """
    if not claimed or not str(claimed).strip():
        return VerificationMatchStatus.NOT_APPLICABLE, 1.0

    if not registry or not str(registry).strip():
        return VerificationMatchStatus.NOT_APPLICABLE, 1.0

    norm_claimed = normalize_org_name(claimed)
    norm_registry = normalize_org_name(registry)

    if not norm_claimed or not norm_registry:
        return VerificationMatchStatus.NOT_APPLICABLE, 1.0

    # 1. Exact Normalized Match
    if norm_claimed == norm_registry:
        return VerificationMatchStatus.MATCH, 1.0

    # 2. Token Set Jaccard Comparison
    tokens_c = set(norm_claimed.split())
    tokens_r = set(norm_registry.split())

    intersection = tokens_c.intersection(tokens_r)
    union = tokens_c.union(tokens_r)

    if not union:
        return VerificationMatchStatus.MISMATCH, 0.0

    jaccard = len(intersection) / len(union)

    # Check if one is a complete subset of the other with at least 2 tokens
    is_subset = (tokens_c.issubset(tokens_r) or tokens_r.issubset(tokens_c)) and len(intersection) >= 2

    if is_subset or jaccard >= 0.70:
        return VerificationMatchStatus.PARTIAL_MATCH, 0.90
    elif jaccard >= 0.50 and len(intersection) >= 2:
        return VerificationMatchStatus.PARTIAL_MATCH, 0.75
    else:
        return VerificationMatchStatus.MISMATCH, 0.0


def compare_strings(claimed: Optional[str], registry: Optional[str]) -> Tuple[str, float]:
    """
    Case-insensitive string comparison for states, classifications, or statuses.
    """
    if not claimed and not registry:
        return VerificationMatchStatus.NOT_APPLICABLE, 1.0
    if not claimed or not registry:
        return VerificationMatchStatus.MISMATCH, 0.0

    c = str(claimed).strip().upper()
    r = str(registry).strip().upper()

    if c == r:
        return VerificationMatchStatus.MATCH, 1.0
    elif c in r or r in c:
        return VerificationMatchStatus.PARTIAL_MATCH, 0.80
    else:
        return VerificationMatchStatus.MISMATCH, 0.0


# ---------------------------------------------------------------------------
# Date Normalizer
# ---------------------------------------------------------------------------

def normalize_date(date_val: Any) -> Optional[str]:
    """
    Parses various date formats into standardized ISO 'YYYY-MM-DD' string.
    """
    if not date_val:
        return None

    if isinstance(date_val, datetime):
        return date_val.strftime("%Y-%m-%d")

    s = str(date_val).strip()
    if not s:
        return None

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return s


# ---------------------------------------------------------------------------
# PAN Entity-Type Signal Extractor
# ---------------------------------------------------------------------------

PAN_HOLDER_TYPE_MAP: Dict[str, str] = {
    "C": "Company / Private Limited / Limited",
    "P": "Individual / Person",
    "H": "Hindu Undivided Family (HUF)",
    "F": "Partnership Firm / LLP",
    "A": "Association of Persons (AOP)",
    "T": "Trust",
    "B": "Body of Individuals (BOI)",
    "L": "Local Authority",
    "J": "Artificial Juridical Person",
    "G": "Government Agency",
}


def extract_pan_entity_type(pan: str) -> Dict[str, str]:
    """
    Infers the taxpayer/entity category from the 4th character of an Indian PAN.
    """
    cleaned = normalize_identifier(pan)
    if len(cleaned) >= 4:
        code = cleaned[3]
        desc = PAN_HOLDER_TYPE_MAP.get(code, "Other / Unspecified")
        return {
            "entity_type_code": code,
            "entity_type_description": desc,
        }
    return {
        "entity_type_code": "",
        "entity_type_description": "Unknown",
    }


# ---------------------------------------------------------------------------
# CIN Metadata Signal Extractor
# ---------------------------------------------------------------------------

CIN_COMPANY_TYPE_MAP: Dict[str, str] = {
    "PTC": "Private Limited Company",
    "PLC": "Public Limited Company",
    "FTC": "Foreign Company",
    "OPC": "One Person Company",
    "GOI": "Union Government Company",
    "SGC": "State Government Company",
    "GAP": "General Association Public",
    "NPL": "Section 8 Non-Profit License",
    "ULL": "Unlisted Limited Liability",
}


def extract_cin_metadata(cin: str) -> Dict[str, Any]:
    """
    Extracts structural metadata from a standard 21-character Indian CIN:
    Example: 'U72900TN2018PTC123456'
    - Listing status: 'U' -> Unlisted, 'L' -> Listed
    - Industry code: '72900'
    - State code: 'TN'
    - Incorporation year: '2018'
    - Ownership type code: 'PTC' -> Private Limited Company
    - Registration number: '123456'
    """
    cleaned = normalize_cin(cin)
    if len(cleaned) == 21:
        listing = "Listed" if cleaned[0] == "L" else "Unlisted"
        industry_code = cleaned[1:6]
        state_code = cleaned[6:8]
        incorporation_year = cleaned[8:12]
        ownership_code = cleaned[12:15]
        reg_number = cleaned[15:21]
        company_type = CIN_COMPANY_TYPE_MAP.get(ownership_code, "Company")

        return {
            "listing_status": listing,
            "industry_code": industry_code,
            "state_code": state_code,
            "incorporation_year": incorporation_year,
            "ownership_code": ownership_code,
            "company_type": company_type,
            "registration_number": reg_number,
        }

    return {
        "listing_status": "Unknown",
        "industry_code": "",
        "state_code": "",
        "incorporation_year": "",
        "ownership_code": "",
        "company_type": "Company",
        "registration_number": "",
    }
