"""
Bid Service for Part 3C: Bid Creation & Tender Participation
Handles bidder tender participation, draft bid lifecycle, statutory readiness checks,
and cross-tenant isolation.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models.bid import Bid
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.schemas.bid import (
    BidCreate,
    BidListItem,
    BidListResponse,
    BidResponse,
    BidTenderSummary,
    BidUpdate,
    BidderOrgSummary,
)
from app.services.bidder_profile_service import (
    _get_or_create_user_organization,
    calculate_profile_completion,
)


def generate_bid_number(db: Session) -> str:
    """
    Generates a deterministic, unique bid reference number.
    Format: BID-YYYY-XXXXXX (e.g. BID-2026-000001)
    """
    current_year = datetime.now(timezone.utc).year
    prefix = f"BID-{current_year}-"

    # Count existing bids in the current year to calculate next sequence
    count = db.scalar(
        select(func.count(Bid.id)).where(Bid.bid_number.like(f"{prefix}%"))
    ) or 0

    next_seq = count + 1
    bid_number = f"{prefix}{next_seq:06d}"

    # Ensure uniqueness in case of concurrency
    while db.scalar(select(Bid.id).where(Bid.bid_number == bid_number)):
        next_seq += 1
        bid_number = f"{prefix}{next_seq:06d}"

    return bid_number


def validate_tender_for_bid_creation(tender: Tender) -> None:
    """
    Validates that a tender is currently OPEN for participation and
    that the submission deadline has not passed.
    """
    if not tender.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested tender was not found or is inactive.",
        )

    # Tender status rule: Only OPEN tenders allow bid creation
    if tender.status != "OPEN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bid creation is only allowed for OPEN tenders. Current tender status is '{tender.status}'.",
        )

    # Server-side deadline check
    if tender.submission_end_date:
        now_utc = datetime.now(timezone.utc)
        deadline = tender.submission_end_date
        # Normalize naive/aware datetime
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if now_utc > deadline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The submission deadline for this tender has passed. Bid participation is closed.",
            )


def validate_bidder_profile_readiness(profile: Profile, org: Organization) -> None:
    """
    Validates that the bidder organization and contact profile satisfy all statutory
    mandatory fields (100% profile completeness) before allowing participation.
    """
    completion = calculate_profile_completion(profile, org)
    if not completion.is_complete:
        missing_str = ", ".join(completion.missing_required_fields)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Complete your bidder profile before participating in a tender. Missing required fields: {missing_str}",
        )


def _format_bid_tender_summary(tender: Tender) -> BidTenderSummary:
    """Formats a Tender model instance into a BidTenderSummary schema."""
    active_req_count = len([r for r in tender.requirements if r.is_active]) if tender.requirements else 0
    return BidTenderSummary(
        id=tender.id,
        tender_number=tender.tender_number,
        title=tender.title,
        description=tender.description,
        department=tender.department,
        category=tender.category,
        procurement_type=tender.procurement_type,
        estimated_value=tender.estimated_value,
        currency=tender.currency or "INR",
        status=tender.status,
        publish_date=tender.publish_date,
        submission_start_date=tender.submission_start_date,
        submission_end_date=tender.submission_end_date,
        organization_name=tender.organization.name if tender.organization else None,
        organization_city=tender.organization.city if tender.organization else None,
        organization_state=tender.organization.state if tender.organization else None,
        active_requirements_count=active_req_count,
    )


def _format_bid_response(bid: Bid) -> BidResponse:
    """Formats a Bid SQLAlchemy model instance into BidResponse schema."""
    tender_summary = _format_bid_tender_summary(bid.tender)
    bidder_org = None
    if bid.bidder_organization:
        bidder_org = BidderOrgSummary(
            id=bid.bidder_organization.id,
            name=bid.bidder_organization.name,
            trade_name=bid.bidder_organization.trade_name,
            pan_number=bid.bidder_organization.pan_number,
            gstin=bid.bidder_organization.gstin,
            city=bid.bidder_organization.city,
            state=bid.bidder_organization.state,
        )

    return BidResponse(
        id=bid.id,
        tender_id=bid.tender_id,
        bidder_organization_id=bid.bidder_organization_id,
        created_by_profile_id=bid.created_by_profile_id,
        bid_number=bid.bid_number,
        status=bid.status,
        quoted_amount=bid.quoted_amount,
        currency=bid.currency or "INR",
        technical_summary=bid.technical_summary,
        commercial_notes=bid.commercial_notes,
        remarks=bid.remarks,
        submitted_at=bid.submitted_at,
        is_active=bid.is_active,
        created_at=bid.created_at,
        updated_at=bid.updated_at,
        tender=tender_summary,
        bidder_organization=bidder_org,
    )


def create_bid(
    db: Session,
    current_user: User,
    tender_id: uuid.UUID,
    data: Optional[BidCreate] = None,
) -> BidResponse:
    """
    Creates a new DRAFT bid record for an authenticated BIDDER on an OPEN tender.
    Validates profile completeness, tender status, deadlines, and prevents duplicate participation.
    """
    # 1. Resolve and validate bidder organization
    profile, org = _get_or_create_user_organization(db, current_user)
    validate_bidder_profile_readiness(profile, org)

    # 2. Fetch tender with requirements and organization
    tender = db.scalars(
        select(Tender)
        .options(
            joinedload(Tender.organization),
            selectinload(Tender.requirements),
        )
        .where(Tender.id == tender_id)
    ).first()

    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found.",
        )

    # 3. Validate tender eligibility
    validate_tender_for_bid_creation(tender)

    # 4. Check for duplicate participation
    existing_bid = db.scalars(
        select(Bid).where(
            and_(
                Bid.tender_id == tender_id,
                Bid.bidder_organization_id == org.id,
                Bid.is_active == True,
            )
        )
    ).first()

    if existing_bid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A bid already exists for this tender.",
        )

    # 5. Generate deterministic unique bid number
    bid_number = generate_bid_number(db)

    # 6. Create draft bid
    new_bid = Bid(
        id=uuid.uuid4(),
        tender_id=tender.id,
        bidder_organization_id=org.id,
        created_by_profile_id=profile.id,
        bid_number=bid_number,
        status="DRAFT",
        quoted_amount=data.quoted_amount if data else None,
        currency=data.currency if data and data.currency else (tender.currency or "INR"),
        technical_summary=data.technical_summary if data else None,
        commercial_notes=data.commercial_notes if data else None,
        remarks=data.remarks if data else None,
        is_active=True,
    )

    db.add(new_bid)
    db.commit()
    db.refresh(new_bid)

    # Load relations for full response
    new_bid = db.scalars(
        select(Bid)
        .options(
            joinedload(Bid.tender).joinedload(Tender.organization),
            joinedload(Bid.tender).selectinload(Tender.requirements),
            joinedload(Bid.bidder_organization),
        )
        .where(Bid.id == new_bid.id)
    ).one()

    return _format_bid_response(new_bid)


def list_bidder_bids(
    db: Session,
    current_user: User,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> BidListResponse:
    """
    Returns paginated list of bids belonging exclusively to the authenticated bidder's organization.
    Cross-tenant access is strictly isolated at query level.
    """
    profile, org = _get_or_create_user_organization(db, current_user)

    # Base query joined with Tender for search and metadata
    base_query = (
        select(Bid)
        .join(Tender, Bid.tender_id == Tender.id)
        .options(
            joinedload(Bid.tender).joinedload(Tender.organization),
        )
        .where(
            and_(
                Bid.bidder_organization_id == org.id,
                Bid.is_active == True,
            )
        )
    )

    # Filter by status
    if status_filter:
        base_query = base_query.where(Bid.status == status_filter.strip().upper())

    # Search filter (bid number, tender number, tender title)
    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        base_query = base_query.where(
            or_(
                Bid.bid_number.ilike(search_pattern),
                Tender.tender_number.ilike(search_pattern),
                Tender.title.ilike(search_pattern),
            )
        )

    # Total count calculation
    count_query = select(func.count()).select_from(base_query.subquery())
    total = db.scalar(count_query) or 0

    # Pagination & ordering (newest updated first)
    offset = (page - 1) * page_size
    query = base_query.order_by(Bid.updated_at.desc()).offset(offset).limit(page_size)
    bids = db.scalars(query).all()

    total_pages = max(1, (total + page_size - 1) // page_size)

    items: List[BidListItem] = []
    for b in bids:
        items.append(
            BidListItem(
                id=b.id,
                bid_number=b.bid_number,
                status=b.status,
                quoted_amount=b.quoted_amount,
                currency=b.currency or "INR",
                tender_id=b.tender.id,
                tender_number=b.tender.tender_number,
                tender_title=b.tender.title,
                tender_status=b.tender.status,
                department=b.tender.department,
                category=b.tender.category,
                procurement_type=b.tender.procurement_type,
                submission_end_date=b.tender.submission_end_date,
                procuring_organization_name=b.tender.organization.name if b.tender.organization else None,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
        )

    return BidListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


def get_bid_detail(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> BidResponse:
    """
    Retrieves full details of a specific bid workspace.
    Enforces strict organization ownership: returns 404 if not found or belongs to another bidder.
    """
    profile, org = _get_or_create_user_organization(db, current_user)

    bid = db.scalars(
        select(Bid)
        .options(
            joinedload(Bid.tender).joinedload(Tender.organization),
            joinedload(Bid.tender).selectinload(Tender.requirements),
            joinedload(Bid.bidder_organization),
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

    return _format_bid_response(bid)


def update_draft_bid(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    data: BidUpdate,
) -> BidResponse:
    """
    Updates editable fields of a DRAFT bid.
    Immutable fields (id, bid_number, tender_id, bidder_organization_id, created_by_profile_id, status)
    cannot be altered through this endpoint.
    """
    profile, org = _get_or_create_user_organization(db, current_user)

    bid = db.scalars(
        select(Bid)
        .options(
            joinedload(Bid.tender).joinedload(Tender.organization),
            joinedload(Bid.tender).selectinload(Tender.requirements),
            joinedload(Bid.bidder_organization),
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

    # Status check: only DRAFT bids may be edited
    if bid.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only DRAFT bids can be modified. Current bid status is '{bid.status}'.",
        )

    # Apply editable fields
    update_data = data.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        if field_name in ["quoted_amount", "currency", "technical_summary", "commercial_notes", "remarks"]:
            setattr(bid, field_name, value)

    db.commit()
    db.refresh(bid)

    return _format_bid_response(bid)


def get_existing_bid_for_tender(
    db: Session,
    current_user: User,
    tender_id: uuid.UUID,
) -> Optional[BidListItem]:
    """
    Checks if the authenticated bidder organization already has an active bid for a given tender.
    Returns summary if exists, else None.
    """
    profile, org = _get_or_create_user_organization(db, current_user)

    bid = db.scalars(
        select(Bid)
        .join(Tender, Bid.tender_id == Tender.id)
        .options(joinedload(Bid.tender).joinedload(Tender.organization))
        .where(
            and_(
                Bid.tender_id == tender_id,
                Bid.bidder_organization_id == org.id,
                Bid.is_active == True,
            )
        )
    ).first()

    if not bid:
        return None

    return BidListItem(
        id=bid.id,
        bid_number=bid.bid_number,
        status=bid.status,
        quoted_amount=bid.quoted_amount,
        currency=bid.currency or "INR",
        tender_id=bid.tender.id,
        tender_number=bid.tender.tender_number,
        tender_title=bid.tender.title,
        tender_status=bid.tender.status,
        department=bid.tender.department,
        category=bid.tender.category,
        procurement_type=bid.tender.procurement_type,
        submission_end_date=bid.tender.submission_end_date,
        procuring_organization_name=bid.tender.organization.name if bid.tender.organization else None,
        created_at=bid.created_at,
        updated_at=bid.updated_at,
    )
