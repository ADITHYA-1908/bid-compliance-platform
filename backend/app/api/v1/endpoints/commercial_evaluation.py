import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.tender import Tender
from app.core.deps import get_current_user
from app.core.authorization import require_any_role
from app.schemas.commercial_evaluation import (
    CommercialEvaluationResultItem,
    TenderCommercialEvaluationResponse,
)
from app.services.procurement.commercial_evaluation_service import CommercialEvaluationService

router = APIRouter(prefix="/procurement/tenders", tags=["Commercial Evaluation"])


@router.get(
    "/{tender_id}/commercial-evaluation",
    response_model=TenderCommercialEvaluationResponse,
    summary="Get commercial evaluation results for a tender",
)
def get_tender_commercial_evaluation(
    tender_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_role("PROCUREMENT_OFFICER", "ADMIN")),
):
    """
    Retrieves deterministic commercial evaluation results for all submitted bids against a tender.
    Adheres to the tender's configured evaluation method (L1, QCBS, or Custom Weighted).
    """
    tender = db.query(Tender).filter(Tender.id == tender_id, Tender.is_active == True).first()
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found.",
        )

    # Cross-tenant isolation check
    user_role = user.profile.role.name if user.profile and user.profile.role else ""
    user_org_id = user.profile.organization_id if user.profile else None
    if user_role != "ADMIN" and tender.organization_id != user_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cross-organization tender access forbidden.",
        )

    results = CommercialEvaluationService.get_tender_commercial_evaluation(db, tender_id)

    items: List[CommercialEvaluationResultItem] = []
    lowest_price = None
    eligible_count = 0
    ineligible_count = 0

    for res in results:
        if res.eligibility_status == "ELIGIBLE" and res.quoted_amount is not None:
            eligible_count += 1
            if lowest_price is None or res.quoted_amount < lowest_price:
                lowest_price = res.quoted_amount
        else:
            ineligible_count += 1

        bid_number = res.bid.bid_number if res.bid else "Unknown Bid"
        bidder_name = res.bid.bidder_organization.name if res.bid and res.bid.bidder_organization else "Unknown Organization"

        items.append(
            CommercialEvaluationResultItem(
                id=res.id,
                tender_id=res.tender_id,
                bid_id=res.bid_id,
                bid_number=bid_number,
                bidder_name=bidder_name,
                evaluation_method=res.evaluation_method,
                eligibility_status=res.eligibility_status,
                quoted_amount=res.quoted_amount,
                currency=res.currency,
                technical_score=res.technical_score,
                financial_score=res.financial_score,
                final_score=res.final_score,
                commercial_rank=res.commercial_rank,
                rank_label=res.rank_label,
                is_l1=res.is_l1,
                is_tie=res.is_tie,
                has_critical_blocker=res.has_critical_blocker,
                blocker_reason=res.blocker_reason,
                explanation=res.explanation,
                formula_snapshot=res.formula_snapshot or {},
                evaluated_at=res.evaluated_at,
                is_current=res.is_current,
            )
        )

    return TenderCommercialEvaluationResponse(
        tender_id=tender.id,
        tender_number=tender.tender_number,
        tender_title=tender.title,
        evaluation_method=tender.evaluation_method,
        technical_weight=tender.technical_weight or 70.0,
        financial_weight=tender.financial_weight or 30.0,
        custom_weights=tender.custom_weights_json or {},
        total_evaluated_bids=len(items),
        eligible_bids_count=eligible_count,
        ineligible_bids_count=ineligible_count,
        lowest_compliant_price=lowest_price,
        results=items,
    )


@router.post(
    "/{tender_id}/commercial-evaluation/evaluate",
    response_model=TenderCommercialEvaluationResponse,
    summary="Re-evaluate commercial bids for a tender",
)
def evaluate_tender_commercials(
    tender_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_role("PROCUREMENT_OFFICER", "ADMIN")),
):
    """
    Forces recalculation of commercial evaluation results for a tender, refreshing L1/QCBS scores.
    """
    tender = db.query(Tender).filter(Tender.id == tender_id, Tender.is_active == True).first()
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found.",
        )

    user_role = user.profile.role.name if user.profile and user.profile.role else ""
    user_org_id = user.profile.organization_id if user.profile else None
    if user_role != "ADMIN" and tender.organization_id != user_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cross-organization tender access forbidden.",
        )

    results = CommercialEvaluationService.evaluate_tender_commercial_bids(
        db=db,
        tender_id=tender_id,
        actor_user_id=user.id,
    )

    items: List[CommercialEvaluationResultItem] = []
    lowest_price = None
    eligible_count = 0
    ineligible_count = 0

    for res in results:
        if res.eligibility_status == "ELIGIBLE" and res.quoted_amount is not None:
            eligible_count += 1
            if lowest_price is None or res.quoted_amount < lowest_price:
                lowest_price = res.quoted_amount
        else:
            ineligible_count += 1

        bid_number = res.bid.bid_number if res.bid else "Unknown Bid"
        bidder_name = res.bid.bidder_organization.name if res.bid and res.bid.bidder_organization else "Unknown Organization"

        items.append(
            CommercialEvaluationResultItem(
                id=res.id,
                tender_id=res.tender_id,
                bid_id=res.bid_id,
                bid_number=bid_number,
                bidder_name=bidder_name,
                evaluation_method=res.evaluation_method,
                eligibility_status=res.eligibility_status,
                quoted_amount=res.quoted_amount,
                currency=res.currency,
                technical_score=res.technical_score,
                financial_score=res.financial_score,
                final_score=res.final_score,
                commercial_rank=res.commercial_rank,
                rank_label=res.rank_label,
                is_l1=res.is_l1,
                is_tie=res.is_tie,
                has_critical_blocker=res.has_critical_blocker,
                blocker_reason=res.blocker_reason,
                explanation=res.explanation,
                formula_snapshot=res.formula_snapshot or {},
                evaluated_at=res.evaluated_at,
                is_current=res.is_current,
            )
        )

    return TenderCommercialEvaluationResponse(
        tender_id=tender.id,
        tender_number=tender.tender_number,
        tender_title=tender.title,
        evaluation_method=tender.evaluation_method,
        technical_weight=tender.technical_weight or 70.0,
        financial_weight=tender.financial_weight or 30.0,
        custom_weights=tender.custom_weights_json or {},
        total_evaluated_bids=len(items),
        eligible_bids_count=eligible_count,
        ineligible_bids_count=ineligible_count,
        lowest_compliant_price=lowest_price,
        results=items,
    )
