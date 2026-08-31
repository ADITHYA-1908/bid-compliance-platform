"""
Compliance Engine Domain Types and DTOs for Part 6A
Defines centralized compliance status constants, operator definitions, evaluation contexts,
and structured rule evaluation results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.organization import Organization
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.verification_record import VerificationRecord


class ComplianceStatus:
    """Centralized compliance determination outcomes."""
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"

    ALL = [PASS, FAIL, REVIEW, NOT_APPLICABLE, PENDING, BLOCKED]
    TERMINAL = [PASS, FAIL, REVIEW, NOT_APPLICABLE]


class ComplianceOperator:
    """Supported rule evaluation operators."""
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    CONTAINS = "CONTAINS"
    EXISTS = "EXISTS"
    NOT_EXISTS = "NOT_EXISTS"
    IN = "IN"
    NOT_IN = "NOT_IN"

    ALL = [
        EQUALS,
        NOT_EQUALS,
        GREATER_THAN,
        GREATER_THAN_OR_EQUAL,
        LESS_THAN,
        LESS_THAN_OR_EQUAL,
        CONTAINS,
        EXISTS,
        NOT_EXISTS,
        IN,
        NOT_IN,
    ]


@dataclass
class ComplianceContext:
    """
    Immutable structured evaluation context passed to rule evaluators.
    Contains all bid-level entity records, active documents, and active verification results
    to eliminate redundant database queries across evaluators.
    """
    bid: Bid
    tender: Tender
    bidder_organization: Optional[Organization] = None
    bid_documents: List[BidDocument] = field(default_factory=list)
    verifications: List[VerificationRecord] = field(default_factory=list)
    verifications_by_type: Dict[str, List[VerificationRecord]] = field(default_factory=dict)
    verifications_by_claim: Dict[str, VerificationRecord] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceRuleResult:
    """
    Structured outcome of a single TenderRequirement evaluation.
    """
    compliance_status: str
    actual_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    operator: Optional[str] = None
    reason: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = field(default_factory=dict)
    source_verification_ids: List[str] = field(default_factory=list)
    is_mandatory: bool = True
    is_critical: bool = False
    critical_failure: bool = False
    review_required: bool = False
    review_reason: Optional[str] = None
    review_type: Optional[str] = None
    weight: Optional[Decimal] = Decimal("10.0")
