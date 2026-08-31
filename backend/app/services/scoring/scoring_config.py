"""
Scoring Engine Centralized Configuration for Part 7A
Defines deterministic status-to-score factors, default weights, precision, rounding,
review policies, and formula versioning.
"""

from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict
from app.db.models.compliance_result import ComplianceStatus


class ReviewPolicy(str, Enum):
    """Policy for handling REVIEW compliance status in scoring."""
    UNRESOLVED = "UNRESOLVED"      # Factor 0.0, marked as requiring human review
    PARTIAL_CREDIT = "PARTIAL_CREDIT"  # Factor 0.5 (or configurable) with review flag


class ScoringConfig:
    """Centralized configuration container for the deterministic scoring engine."""

    # Default weight applied when requirement weight is None/unspecified
    DEFAULT_REQUIREMENT_WEIGHT: Decimal = Decimal("10.0")

    # Internal Decimal precision and rounding policy
    INTERNAL_DECIMAL_PRECISION: int = 4
    ROUNDING_MODE: str = ROUND_HALF_UP

    # Current Scoring Formula Version for auditing
    SCORING_FORMULA_VERSION: str = "v1.0"

    # Status-to-Score Factor baseline mappings
    STATUS_SCORE_FACTORS: Dict[str, Decimal] = {
        ComplianceStatus.PASS: Decimal("1.0000"),
        ComplianceStatus.FAIL: Decimal("0.0000"),
        ComplianceStatus.PENDING: Decimal("0.0000"),
        ComplianceStatus.BLOCKED: Decimal("0.0000"),
        ComplianceStatus.NOT_APPLICABLE: Decimal("0.0000"),
    }

    # Review policy configuration
    REVIEW_POLICY: ReviewPolicy = ReviewPolicy.UNRESOLVED
    REVIEW_PARTIAL_FACTOR: Decimal = Decimal("0.5000")

    # Category normalization mappings (maps legacy/synonym aliases to canonical categories)
    CATEGORY_NORMALIZATION: Dict[str, str] = {
        "STATUTORY_LEGAL": "STATUTORY",
        "LEGAL": "STATUTORY",
        "REGISTRATION": "STATUTORY",
        "FINANCIAL_CRITERIA": "FINANCIAL",
        "FINANCIAL_CAPACITY": "FINANCIAL",
        "PAST_EXPERIENCE": "EXPERIENCE",
        "PROJECT_EXPERIENCE": "EXPERIENCE",
        "TECHNICAL_SPECIFICATION": "TECHNICAL",
        "TECHNICAL_PARAMETERS": "TECHNICAL",
        "OEM_AUTHORIZATION": "OEM",
        "MAKE_IN_INDIA": "LOCAL_CONTENT",
        "BIS_CERTIFICATION": "BIS",
        "INTEGRITY_CHECK": "INTEGRITY",
        "BLACKLISTING_DEBARMENT": "INTEGRITY",
        "SUPPORTING_DOCUMENTS": "DOCUMENTS",
        "DOCUMENTATION": "DOCUMENTS",
    }

    # Human-readable display labels for procurement portal presentation
    CATEGORY_DISPLAY_NAMES: Dict[str, str] = {
        "STATUTORY": "Statutory & Registration",
        "FINANCIAL": "Financial Capacity",
        "EXPERIENCE": "Past Experience & Projects",
        "TECHNICAL": "Technical Specifications",
        "OEM": "OEM Authorization",
        "LOCAL_CONTENT": "Make in India / Local Content",
        "BIS": "BIS / Certifications",
        "DOCUMENTS": "Supporting Documents",
        "INTEGRITY": "Integrity & Non-Debarment",
        "GENERAL": "General Criteria",
        "OTHER": "Other Criteria",
    }

    @classmethod
    def get_score_factor(cls, status: str, review_policy: ReviewPolicy = None) -> Decimal:
        """
        Returns the deterministic score factor (0.0 - 1.0) for a given compliance status.
        """
        active_policy = review_policy or cls.REVIEW_POLICY
        if status == ComplianceStatus.REVIEW:
            if active_policy == ReviewPolicy.PARTIAL_CREDIT:
                return cls.REVIEW_PARTIAL_FACTOR
            return Decimal("0.0000")
        return cls.STATUS_SCORE_FACTORS.get(status, Decimal("0.0000"))

    @classmethod
    def normalize_category(cls, category: str) -> str:
        """Normalizes category aliases to standard canonical domain names."""
        if not category:
            return "GENERAL"
        cat_clean = category.strip().upper()
        return cls.CATEGORY_NORMALIZATION.get(cat_clean, cat_clean)

    @classmethod
    def get_category_display_name(cls, category: str) -> str:
        """Returns human-friendly display label for a category."""
        norm_cat = cls.normalize_category(category)
        return cls.CATEGORY_DISPLAY_NAMES.get(norm_cat, norm_cat.replace("_", " ").title())

