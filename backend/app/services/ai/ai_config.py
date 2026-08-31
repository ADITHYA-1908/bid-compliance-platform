"""
AI & RAG Domain Configuration for Part 7E: RAG + AI Recommendation & Evidence-Based Explanation
Defines enums, prompt versions, allowed recommendations, and source types.
"""

from enum import Enum
from typing import Dict


class AIRecommendationEnum(str, Enum):
    """
    Conservative, non-binding AI recommendation values.
    Note: 'QUALIFIED' / 'DISQUALIFIED' / 'ACCEPT' / 'REJECT' are strictly prohibited
    as final procurement decisions belong solely to the authorized Procurement Officer.
    """
    PROCEED = "PROCEED"
    PROCEED_WITH_REVIEW = "PROCEED_WITH_REVIEW"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    DO_NOT_PROCEED_WITHOUT_REVIEW = "DO_NOT_PROCEED_WITHOUT_REVIEW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ConfidenceLabelEnum(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RAGSourceType(str, Enum):
    TENDER_REQUIREMENT = "TENDER_REQUIREMENT"
    TENDER_CLAUSE = "TENDER_CLAUSE"
    BID_DOCUMENT = "BID_DOCUMENT"
    STRUCTURED_EXTRACTION = "STRUCTURED_EXTRACTION"
    VERIFICATION_RESULT = "VERIFICATION_RESULT"
    COMPLIANCE_RESULT = "COMPLIANCE_RESULT"
    SCORING_RESULT = "SCORING_RESULT"
    RISK_RESULT = "RISK_RESULT"


# Relative ranking priority multiplier for evidence types in hybrid search
SOURCE_PRIORITY_MULTIPLIERS: Dict[str, float] = {
    RAGSourceType.COMPLIANCE_RESULT.value: 1.25,
    RAGSourceType.VERIFICATION_RESULT.value: 1.20,
    RAGSourceType.RISK_RESULT.value: 1.15,
    RAGSourceType.SCORING_RESULT.value: 1.15,
    RAGSourceType.STRUCTURED_EXTRACTION.value: 1.10,
    RAGSourceType.TENDER_REQUIREMENT.value: 1.05,
    RAGSourceType.BID_DOCUMENT.value: 1.00,
    RAGSourceType.TENDER_CLAUSE.value: 1.00,
}

PROMPT_VERSION = "v1"
DISCLAIMER_TEXT = (
    "This AI-assisted recommendation and explanation is grounded in deterministic "
    "verification, compliance, and risk evidence. Final qualification and award "
    "decisions remain with the authorized Procurement Officer."
)
