import math
import uuid
from typing import Any, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.organization import Organization
from app.schemas.bidder_tender import (
    BidderOrganizationPublicSummary,
    BidderTenderDetail,
    BidderTenderListResponse,
    BidderTenderRequirementSummary,
    BidderTenderSummary,
)


def format_condition_text(operator: str, expected_value: Any, req_type: str, code: str = "") -> str:
    """Translates raw rule operators and JSON expected values into clear, human-readable statements for bidders."""
    op = (operator or "").upper()
    val = expected_value

    # Specific common statutory / compliance heuristics
    if "BLACKLIST" in (code or "").upper() or "DEBAR" in (code or "").upper():
        if val is False or val == "false" or val == "FALSE":
            return "Bidder must not be blacklisted or debarred by GeM / Government"

    if op == "EXISTS":
        return "Mandatory Document / Proof Submission Required"
    elif op == "NOT_EXISTS":
        return "Prohibited / Must not exist"
    elif op == "EQUALS":
        if val is True or val == "true":
            return "Required / Applicable"
        elif val is False or val == "false":
            return "Must be False / Not Applicable"
        elif str(val).upper() == "ACTIVE":
            return "Must be Active & Verified"
        return f"Must equal '{val}'"
    elif op == "NOT_EQUALS":
        return f"Must not equal '{val}'"
    elif op == "GREATER_THAN_OR_EQUAL":
        if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace(".", "", 1).isdigit()):
            return f"Minimum required: {val}"
        return f"At least {val}"
    elif op == "GREATER_THAN":
        return f"Strictly greater than {val}"
    elif op == "LESS_THAN_OR_EQUAL":
        return f"Maximum allowed: {val}"
    elif op == "LESS_THAN":
        return f"Strictly less than {val}"
    elif op == "CONTAINS":
        return f"Must contain '{val}'"
    
    return f"{op} {val}" if val is not None else op


def get_available_tenders(
    db: Session,
    search: Optional[str] = None,
    category: Optional[str] = None,
    procurement_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    sort_by: Optional[str] = "newest",
    page: int = 1,
    page_size: int = 12,
) -> BidderTenderListResponse:
    """
    Retrieves searchable, paginated list of tenders available for bidder discovery.
    Enforces visibility security: Bidders can NEVER see DRAFT or ARCHIVED tenders.
    """
    # 1. Base query: Active tenders in OPEN or PUBLISHED (Upcoming) status
    allowed_statuses = ["OPEN", "PUBLISHED"]
    
    if status_filter and status_filter.upper() in allowed_statuses:
        status_clause = Tender.status == status_filter.upper()
    else:
        status_clause = Tender.status.in_(allowed_statuses)

    filters = [
        Tender.is_active == True,
        status_clause,
    ]

    # 2. Keyword Search
    if search and search.strip():
        words = search.strip().split()
        for word in words:
            term = f"%{word}%"
            filters.append(
                or_(
                    Tender.title.ilike(term),
                    Tender.tender_number.ilike(term),
                    Tender.department.ilike(term),
                    Tender.category.ilike(term),
                    Tender.description.ilike(term),
                )
            )

    # 3. Category Filter
    if category and category.strip():
        filters.append(Tender.category.ilike(category.strip()))

    # 4. Procurement Type Filter
    if procurement_type and procurement_type.strip():
        filters.append(Tender.procurement_type.ilike(procurement_type.strip()))

    # 5. Total count
    count_stmt = select(func.count(Tender.id)).where(and_(*filters))
    total_items = db.scalar(count_stmt) or 0

    # 6. Sorting
    if sort_by == "deadline":
        order_clause = Tender.submission_end_date.asc().nulls_last()
    elif sort_by == "value_high":
        order_clause = Tender.estimated_value.desc().nulls_last()
    elif sort_by == "value_low":
        order_clause = Tender.estimated_value.asc().nulls_last()
    else:  # newest
        order_clause = Tender.created_at.desc()

    # 7. Pagination
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))
    offset_val = (safe_page - 1) * safe_page_size
    total_pages = math.ceil(total_items / safe_page_size) if safe_page_size > 0 else 1

    # 8. Query items with eager-loaded organization
    stmt = (
        select(Tender)
        .where(and_(*filters))
        .options(
            selectinload(Tender.organization),
            selectinload(Tender.requirements),
        )
        .order_by(order_clause)
        .offset(offset_val)
        .limit(safe_page_size)
    )

    tenders = db.scalars(stmt).all()

    items: List[BidderTenderSummary] = []
    for t in tenders:
        active_reqs = [r for r in t.requirements if r.is_active]
        items.append(
            BidderTenderSummary(
                id=t.id,
                tender_number=t.tender_number,
                title=t.title,
                description=t.description,
                department=t.department,
                category=t.category,
                procurement_type=t.procurement_type,
                estimated_value=t.estimated_value,
                currency=t.currency or "INR",
                status=t.status,
                publish_date=t.publish_date,
                submission_start_date=t.submission_start_date,
                submission_end_date=t.submission_end_date,
                organization_name=t.organization.name if t.organization else None,
                organization_city=t.organization.city if t.organization else None,
                organization_state=t.organization.state if t.organization else None,
                active_requirements_count=len(active_reqs),
                updated_at=t.updated_at,
            )
        )

    return BidderTenderListResponse(
        items=items,
        page=safe_page,
        page_size=safe_page_size,
        total=total_items,
        total_pages=total_pages,
    )


def get_bidder_tender_detail(
    db: Session,
    tender_id: uuid.UUID,
) -> BidderTenderDetail:
    """
    Retrieves sanitized, bidder-safe detailed view of a tender and its eligibility requirements.
    Strictly blocks access to DRAFT or ARCHIVED tenders (returns 404).
    """
    stmt = (
        select(Tender)
        .where(
            and_(
                Tender.id == tender_id,
                Tender.is_active == True,
                Tender.status.notin_(["DRAFT", "ARCHIVED"]),
            )
        )
        .options(
            selectinload(Tender.organization),
            selectinload(Tender.requirements),
        )
    )

    tender = db.scalars(stmt).first()
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found or not currently available for bidding.",
        )

    # Format active requirements
    active_reqs = [r for r in tender.requirements if r.is_active]
    active_reqs.sort(key=lambda r: (r.display_order, r.created_at))

    req_summaries: List[BidderTenderRequirementSummary] = []
    for r in active_reqs:
        condition_str = format_condition_text(
            operator=r.operator,
            expected_value=r.expected_value,
            req_type=r.requirement_type,
            code=r.code,
        )
        req_summaries.append(
            BidderTenderRequirementSummary(
                id=r.id,
                code=r.code,
                name=r.name,
                description=r.description,
                category=r.category,
                requirement_type=r.requirement_type,
                operator=r.operator,
                expected_value=r.expected_value,
                condition_text=condition_str,
                is_mandatory=r.is_mandatory,
                display_order=r.display_order,
            )
        )

    org_summary = BidderOrganizationPublicSummary(
        id=tender.organization.id,
        name=tender.organization.name,
        organization_type=tender.organization.organization_type,
        city=tender.organization.city,
        state=tender.organization.state,
    )

    return BidderTenderDetail(
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
        evaluation_start_date=tender.evaluation_start_date,
        published_at=tender.published_at,
        opened_at=tender.opened_at,
        organization=org_summary,
        requirements=req_summaries,
        updated_at=tender.updated_at,
    )
