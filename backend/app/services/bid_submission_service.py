"""
Bid Submission Service for Part 3E: Bid Review & Final Submission Workflow
Centralizes submission readiness validation, mandatory document verification,
atomic DRAFT -> SUBMITTED transition, and tamper-evident locking.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Tuple
from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.schemas.bid_submission import (
    BidSubmissionReadinessChecks,
    BidSubmissionReadinessResponse,
    BidSubmitPayload,
    BidSubmitResponse,
)
from app.services.bidder_profile_service import (
    _get_or_create_user_organization,
    calculate_profile_completion,
)


def _get_bid_for_submission(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> Tuple[Profile, Organization, Bid]:
    """
    Resolves the authenticated bidder profile and verifies organization ownership of the bid.
    Returns 404 on missing or cross-tenant access to protect tenant boundaries.
    """
    profile, org = _get_or_create_user_organization(db, current_user)

    bid = db.scalars(
        select(Bid)
        .options(
            joinedload(Bid.tender).joinedload(Tender.organization),
            joinedload(Bid.tender).selectinload(Tender.requirements),
            joinedload(Bid.bidder_organization),
            joinedload(Bid.created_by_profile),
            joinedload(Bid.submitted_by_profile),
            selectinload(Bid.documents).joinedload(BidDocument.tender_requirement),
        )
        .where(
            and_(
                Bid.id == bid_id,
                Bid.bidder_organization_id == org.id,
                Bid.is_active == True,
            )
        )
    ).first()

    if not bid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid submission record not found.",
        )

    return profile, org, bid


def check_submission_readiness(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> BidSubmissionReadinessResponse:
    """
    Evaluates all mandatory pre-submission criteria for a bid proposal:
    1. Bidder Profile completeness (100% statutory fields)
    2. Required Proposal Fields (quoted_amount, technical_summary)
    3. Mandatory Compliance Documents (all mandatory tender requirements have active linked docs)
    4. Tender Status (must be OPEN)
    5. Submission Deadline (current server UTC time <= submission_end_date)
    """
    profile, org, bid = _get_bid_for_submission(db, current_user, bid_id)

    # 1. Profile Readiness
    profile_completion = calculate_profile_completion(profile, org)
    profile_complete = profile_completion.is_complete

    # 2. Bid Proposal Details Completeness
    missing_required_fields: List[str] = []
    if bid.quoted_amount is None or bid.quoted_amount <= 0:
        missing_required_fields.append("Quoted Amount (Commercial Proposal)")
    if not bid.technical_summary or not bid.technical_summary.strip():
        missing_required_fields.append("Technical & Scope Summary")

    bid_details_complete = len(missing_required_fields) == 0

    # 3. Mandatory Document Requirements
    active_docs = [d for d in bid.documents if d.is_active]
    uploaded_req_ids = {d.tender_requirement_id for d in active_docs if d.tender_requirement_id}

    mandatory_reqs = [
        r for r in bid.tender.requirements
        if r.is_active and (r.is_mandatory or r.requirement_type == "DOCUMENT") and r.is_mandatory
    ]

    missing_documents: List[str] = []
    for req in mandatory_reqs:
        if req.id not in uploaded_req_ids:
            missing_documents.append(req.name)

    mandatory_documents_complete = len(missing_documents) == 0

    # 4. Tender Status Check
    tender_open = bool(bid.tender.is_active and bid.tender.status == "OPEN")

    # 5. Server-Side Submission Deadline Check
    deadline_valid = True
    if bid.tender.submission_end_date:
        now_utc = datetime.now(timezone.utc)
        end_date = bid.tender.submission_end_date
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        if now_utc > end_date:
            deadline_valid = False

    ready_to_submit = bool(
        profile_complete
        and bid_details_complete
        and mandatory_documents_complete
        and tender_open
        and deadline_valid
        and bid.status == "DRAFT"
    )

    checks = BidSubmissionReadinessChecks(
        profile_complete=profile_complete,
        bid_details_complete=bid_details_complete,
        mandatory_documents_complete=mandatory_documents_complete,
        tender_open=tender_open,
        deadline_valid=deadline_valid,
    )

    return BidSubmissionReadinessResponse(
        bid_id=bid.id,
        bid_number=bid.bid_number,
        ready_to_submit=ready_to_submit,
        checks=checks,
        missing_required_fields=missing_required_fields,
        missing_documents=missing_documents,
        tender_title=bid.tender.title,
        tender_number=bid.tender.tender_number,
        tender_status=bid.tender.status,
        submission_end_date=bid.tender.submission_end_date,
    )


def submit_bid(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    payload: BidSubmitPayload,
) -> BidSubmitResponse:
    """
    Executes final atomic submission of a DRAFT bid proposal.
    Validates readiness, sets SUBMITTED status with timestamps and audit reference,
    and locks the proposal from subsequent mutation.
    """
    profile, org, bid = _get_bid_for_submission(db, current_user, bid_id)

    # 1. Declaration check
    if not payload.declaration_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must accept the submission declaration to submit your bid.",
        )

    # 2. Prevent duplicate submission
    if bid.status == "SUBMITTED":
        submitted_str = bid.submitted_at.isoformat() if bid.submitted_at else "previously"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bid '{bid.bid_number}' has already been submitted on {submitted_str}.",
        )

    if bid.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only DRAFT bids can be submitted. Current status is '{bid.status}'.",
        )

    # 3. Comprehensive readiness evaluation
    readiness = check_submission_readiness(db, current_user, bid_id)
    if not readiness.ready_to_submit:
        if not readiness.checks.profile_complete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bid is not ready for submission. Bidder organization profile is incomplete.",
            )
        if not readiness.checks.tender_open:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bid is not ready for submission. Tender is not OPEN (Status: '{bid.tender.status}').",
            )
        if not readiness.checks.deadline_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bid is not ready for submission. Tender submission deadline has passed.",
            )
        if not readiness.checks.bid_details_complete:
            missing_fields_str = ", ".join(readiness.missing_required_fields)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bid is not ready for submission. Required details missing: {missing_fields_str}.",
            )
        if not readiness.checks.mandatory_documents_complete:
            missing_docs_str = ", ".join(readiness.missing_documents)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bid is not ready for submission. Missing mandatory documents: {missing_docs_str}.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bid is not ready for final submission.",
        )

    # 4. Atomic submission state transition
    now_utc = datetime.now(timezone.utc)
    submission_ref = f"SUB-{now_utc.year}-{bid.bid_number.replace('BID-', '')}"

    bid.status = "SUBMITTED"
    bid.submitted_at = now_utc
    bid.submitted_by_profile_id = profile.id
    bid.declaration_accepted = True
    bid.declaration_accepted_at = now_utc
    bid.submission_reference = submission_ref

    try:
        db.commit()
        db.refresh(bid)
        # Emit Part 12 notifications for Bidder and Procurement Officer
        try:
            from app.services.notification_service import NotificationService
            NotificationService.notify_bid_submitted(db=db, bid=bid)
        except Exception as notif_err:
            pass
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the bid submission. Please try again.",
        )

    return BidSubmitResponse(
        id=bid.id,
        bid_number=bid.bid_number,
        submission_reference=submission_ref,
        status=bid.status,
        submitted_at=bid.submitted_at,
        submitted_by_email=profile.email,
        submitted_by_name=profile.full_name,
        tender_id=bid.tender_id,
        tender_number=bid.tender.tender_number,
        tender_title=bid.tender.title,
        bidder_organization_name=org.name,
        quoted_amount=bid.quoted_amount,
        currency=bid.currency or "INR",
        message="Bid proposal submitted successfully and locked for verification.",
    )
