"""
Compliance Engine Core Dispatcher for Part 6A
Orchestrates context preparation, evaluator resolution, rule evaluation, and result synthesis.
"""

import uuid
from typing import Dict, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import Session, selectinload

from app.compliance.registry import compliance_registry
from app.compliance.types import (
    ComplianceContext,
    ComplianceRuleResult,
    ComplianceStatus,
)
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.organization import Organization
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.verification_record import VerificationRecord


def build_compliance_context(db: Session, bid_id: uuid.UUID) -> ComplianceContext:
    """
    Constructs an immutable evaluation context for a bid by loading:
    - The Bid record
    - The associated Tender
    - The Bidder Organization
    - All currently active BidDocuments
    - All currently active VerificationRecords
    """
    bid = db.scalars(select(Bid).where(Bid.id == bid_id)).first()
    if not bid:
        raise ValueError(f"Bid with id {bid_id} not found")

    tender = db.scalars(select(Tender).where(Tender.id == bid.tender_id)).first()
    if not tender:
        raise ValueError(f"Tender with id {bid.tender_id} not found")

    org = None
    if bid.bidder_organization_id:
        org = db.scalars(select(Organization).where(Organization.id == bid.bidder_organization_id)).first()

    # Active documents for this bid with processing preloaded
    active_docs = db.scalars(
        select(BidDocument)
        .options(selectinload(BidDocument.processing))
        .where(
            and_(
                BidDocument.bid_id == bid_id,
                BidDocument.is_active == True,
            )
        )
    ).all()

    # Active verification records for this bid
    active_verifications = db.scalars(
        select(VerificationRecord)
        .outerjoin(BidDocument, VerificationRecord.bid_document_id == BidDocument.id)
        .where(
            and_(
                VerificationRecord.bid_id == bid_id,
                VerificationRecord.is_active == True,
                (VerificationRecord.bid_document_id == None) | (BidDocument.is_active == True),
            )
        )
        .order_by(VerificationRecord.created_at.asc())
    ).all()

    # Index verifications by type and claim source
    v_by_type: Dict[str, List[VerificationRecord]] = {}
    v_by_claim: Dict[str, VerificationRecord] = {}

    for v in active_verifications:
        v_by_type.setdefault(v.verification_type, []).append(v)
        if v.claim_source:
            v_by_claim[v.claim_source] = v

    # Active validity records for this bid's documents
    from app.db.models.document_validity import DocumentValidityRecord
    doc_ids = [d.id for d in active_docs]
    validity_records = []
    if doc_ids:
        validity_records = list(db.scalars(
            select(DocumentValidityRecord).where(
                DocumentValidityRecord.document_id.in_(doc_ids),
                DocumentValidityRecord.is_current == True,
                DocumentValidityRecord.is_active == True,
            )
        ).all())

    validity_by_doc_id = {v.document_id: v for v in validity_records}
    validity_by_type = {}
    for v in validity_records:
        validity_by_type.setdefault(v.document_type, []).append(v)

    return ComplianceContext(
        bid=bid,
        tender=tender,
        bidder_organization=org,
        bid_documents=list(active_docs),
        verifications=list(active_verifications),
        verifications_by_type=v_by_type,
        verifications_by_claim=v_by_claim,
        metadata={
            "validity_records": validity_records,
            "validity_by_doc_id": validity_by_doc_id,
            "validity_by_type": validity_by_type,
        },
    )


def evaluate_requirement(
    requirement: TenderRequirement,
    context: ComplianceContext,
) -> ComplianceRuleResult:
    """
    Resolves the registered evaluator for a requirement and executes evaluation.
    """
    evaluator = compliance_registry.resolve_evaluator(requirement)
    return evaluator.evaluate(requirement, context)
