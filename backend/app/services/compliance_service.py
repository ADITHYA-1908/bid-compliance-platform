"""
Compliance Evaluation Service for Part 6A
Orchestrates compliance evaluation lifecycle, RBAC & multi-tenant security,
database persistence, versioning, and summary aggregation.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from app.compliance.engine import build_compliance_context, evaluate_requirement
from app.compliance.types import ComplianceStatus
from app.db.models.bid import Bid
from app.db.models.compliance_result import ComplianceResult
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.schemas.compliance import (
    BidComplianceSummaryResponse,
    ComplianceResultItemResponse,
    ComplianceSummaryCounts,
)


def _get_bid_for_compliance_access(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> Tuple[Profile, Bid, Tender]:
    """
    Validates tenant ownership and role-based access for compliance operations.
    - BIDDER: must belong to the bidding organization.
    - PROCUREMENT_OFFICER: must belong to the organization owning the tender.
    - ADMIN: unrestricted access across all organizations.
    Raises HTTP 404 on unauthorized access or missing records.
    """
    profile = db.scalars(
        select(Profile).where(Profile.id == current_user.profile_id)
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )

    bid = db.scalars(
        select(Bid).where(
            and_(
                Bid.id == bid_id,
                Bid.is_active == True,
            )
        )
    ).first()
    if not bid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid submission record not found.",
        )

    tender = db.scalars(
        select(Tender).where(
            and_(
                Tender.id == bid.tender_id,
                Tender.is_active == True,
            )
        )
    ).first()
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated tender not found.",
        )

    role = db.scalars(select(Role).where(Role.id == profile.role_id)).first()
    role_name = role.name if role else ""

    if role_name == "BIDDER":
        if bid.bidder_organization_id != profile.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bid submission record not found.",
            )
    elif role_name == "PROCUREMENT_OFFICER":
        if tender.organization_id != profile.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bid submission record not found.",
            )
    elif role_name == "ADMIN":
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized role for compliance evaluation.",
        )

    return profile, bid, tender


def evaluate_bid_compliance(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> BidComplianceSummaryResponse:
    """
    Executes compliance evaluation for all active TenderRequirements of the bid's tender.
    - Preserves audit history by superseding previous evaluation records.
    - Idempotently creates current compliance results.
    - Links verified evidence and justification reasons.
    """
    profile, bid, tender = _get_bid_for_compliance_access(db, current_user, bid_id)

    # 1. Load active tender requirements
    requirements = db.scalars(
        select(TenderRequirement)
        .where(
            and_(
                TenderRequirement.tender_id == tender.id,
                TenderRequirement.is_active == True,
            )
        )
        .order_by(TenderRequirement.display_order.asc(), TenderRequirement.created_at.asc())
    ).all()

    if not requirements:
        return BidComplianceSummaryResponse(
            bid_id=bid.id,
            tender_id=tender.id,
            tender_number=tender.tender_number,
            bidder_name=bid.bidder_organization.name if bid.bidder_organization else None,
            compliance_evaluation_complete=True,
            counts=ComplianceSummaryCounts(),
            results=[],
            evaluated_at=datetime.now(timezone.utc),
        )

    # 2. Build evaluation context
    context = build_compliance_context(db, bid.id)

    # 3. Determine next evaluation version
    max_ver = db.scalar(
        select(func.max(ComplianceResult.evaluation_version)).where(
            ComplianceResult.bid_id == bid.id
        )
    )
    next_version = (max_ver or 0) + 1
    eval_now = datetime.now(timezone.utc)

    # 4. Supersede current results
    existing_current = db.scalars(
        select(ComplianceResult).where(
            and_(
                ComplianceResult.bid_id == bid.id,
                ComplianceResult.is_current == True,
            )
        )
    ).all()
    for prev in existing_current:
        prev.is_current = False

    # 5. Evaluate each requirement and persist new results
    from app.db.models.tender_requirement_version import TenderRequirementVersion

    created_results: List[ComplianceResult] = []
    for req in requirements:
        rule_res = evaluate_requirement(req, context)
        is_crit = getattr(req, "is_critical", False) or rule_res.is_critical
        is_crit_fail = is_crit and (rule_res.compliance_status == ComplianceStatus.FAIL)

        ev_data = dict(rule_res.evidence) if isinstance(rule_res.evidence, dict) else {}
        if rule_res.review_type and "review_type" not in ev_data:
            ev_data["review_type"] = rule_res.review_type

        # Resolve active rule version
        rule_ver = db.scalars(
            select(TenderRequirementVersion).where(
                TenderRequirementVersion.tender_requirement_id == req.id
            ).order_by(TenderRequirementVersion.version_number.desc())
        ).first()

        rule_ver_id = rule_ver.id if rule_ver else None
        rule_ver_num = rule_ver.version_number if rule_ver else getattr(req, "current_version_number", 1)

        comp_rec = ComplianceResult(
            id=uuid.uuid4(),
            bid_id=bid.id,
            tender_id=tender.id,
            tender_requirement_id=req.id,
            rule_version_id=rule_ver_id,
            rule_version_number=rule_ver_num,
            compliance_status=rule_res.compliance_status,
            actual_value=rule_res.actual_value,
            expected_value=rule_res.expected_value,
            operator=rule_res.operator,
            reason=rule_res.reason,
            evidence=ev_data,
            source_verification_ids=rule_res.source_verification_ids,
            is_mandatory=rule_res.is_mandatory,
            is_critical=is_crit,
            critical_failure=is_crit_fail,
            weight=rule_res.weight,
            evaluation_version=next_version,
            is_current=True,
            evaluated_at=eval_now,
        )
        db.add(comp_rec)
        created_results.append(comp_rec)

    db.commit()

    # 6. Build response
    return _build_compliance_summary_response(bid, tender, created_results, eval_now)


def get_bid_compliance(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> BidComplianceSummaryResponse:
    """
    Retrieves the current compliance evaluation results for a bid.
    """
    profile, bid, tender = _get_bid_for_compliance_access(db, current_user, bid_id)

    current_results = db.scalars(
        select(ComplianceResult)
        .options(selectinload(ComplianceResult.tender_requirement))
        .where(
            and_(
                ComplianceResult.bid_id == bid.id,
                ComplianceResult.is_current == True,
            )
        )
    ).all()

    evaluated_at = current_results[0].evaluated_at if current_results else None
    return _build_compliance_summary_response(bid, tender, list(current_results), evaluated_at)


def _build_compliance_summary_response(
    bid: Bid,
    tender: Tender,
    results: List[ComplianceResult],
    evaluated_at: Optional[datetime],
) -> BidComplianceSummaryResponse:
    """
    Synthesizes evaluated compliance rows into a unified response summary.
    """
    counts = ComplianceSummaryCounts(total=len(results))
    item_responses: List[ComplianceResultItemResponse] = []
    review_items = []

    for r in results:
        status_val = r.compliance_status
        if status_val == ComplianceStatus.PASS:
            counts.passed += 1
        elif status_val == ComplianceStatus.FAIL:
            counts.failed += 1
            if r.is_mandatory:
                counts.mandatory_failures += 1
            if r.is_critical or r.critical_failure:
                counts.critical_failures += 1
        elif status_val == ComplianceStatus.REVIEW:
            counts.review += 1
        elif status_val == ComplianceStatus.PENDING:
            counts.pending += 1
        elif status_val == ComplianceStatus.NOT_APPLICABLE:
            counts.not_applicable += 1
        elif status_val == ComplianceStatus.BLOCKED:
            counts.blocked += 1

        req = r.tender_requirement
        req_code = req.code if req else "UNKNOWN"
        req_name = req.name if req else "Unknown Requirement"
        category = req.category if req else "GENERAL"
        req_type = req.requirement_type if req else "TEXT"

        is_crit = r.is_critical if hasattr(r, "is_critical") else False
        is_crit_fail = r.critical_failure if hasattr(r, "critical_failure") else (is_crit and status_val == ComplianceStatus.FAIL)

        item_responses.append(
            ComplianceResultItemResponse(
                id=r.id,
                bid_id=r.bid_id,
                tender_id=r.tender_id,
                tender_requirement_id=r.tender_requirement_id,
                requirement_code=req_code,
                requirement_name=req_name,
                category=category,
                requirement_type=req_type,
                compliance_status=r.compliance_status,
                actual_value=r.actual_value,
                expected_value=r.expected_value,
                operator=r.operator,
                reason=r.reason,
                evidence=r.evidence,
                source_verification_ids=r.source_verification_ids,
                is_mandatory=r.is_mandatory,
                is_critical=is_crit,
                critical_failure=is_crit_fail,
                weight=r.weight,
                rule_version_id=getattr(r, "rule_version_id", None),
                rule_version_number=getattr(r, "rule_version_number", 1),
                evaluation_version=r.evaluation_version,
                is_current=r.is_current,
                evaluated_at=r.evaluated_at,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )

        # Collect review item if status is REVIEW
        if status_val == ComplianceStatus.REVIEW:
            ev_dict = r.evidence if isinstance(r.evidence, dict) else {}
            review_type = ev_dict.get("review_type") or "HUMAN_REVIEW_REQUIRED"
            source_name = ev_dict.get("source_name") or ev_dict.get("source")

            from app.schemas.compliance import ComplianceReviewItemResponse
            review_items.append(
                ComplianceReviewItemResponse(
                    requirement_id=r.tender_requirement_id,
                    requirement_code=req_code,
                    requirement_name=req_name,
                    category=category,
                    compliance_status=r.compliance_status,
                    review_type=review_type,
                    reason=r.reason,
                    evidence=r.evidence,
                    source_name=source_name,
                    is_mandatory=r.is_mandatory,
                    is_critical=is_crit,
                )
            )

    # Evaluation is complete when all items are in terminal statuses (none PENDING or BLOCKED)
    is_complete = len(results) > 0 and all(
        r.compliance_status in ComplianceStatus.TERMINAL for r in results
    )

    bidder_name = bid.bidder_organization.name if bid.bidder_organization else None

    return BidComplianceSummaryResponse(
        bid_id=bid.id,
        tender_id=tender.id,
        tender_number=tender.tender_number,
        bidder_name=bidder_name,
        compliance_evaluation_complete=is_complete,
        counts=counts,
        results=item_responses,
        review_items=review_items,
        evaluated_at=evaluated_at,
    )
