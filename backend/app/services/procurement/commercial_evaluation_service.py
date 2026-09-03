"""
Commercial Evaluation Service
Orchestrates deterministic commercial bid evaluation, L1 lowest compliant ranking,
QCBS (Quality and Cost Based Selection) technical + financial weighting,
mandatory eligibility gating, tie-handling, and safety review blockers.
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session, joinedload

from app.db.models.tender import Tender
from app.db.models.bid import Bid
from app.db.models.compliance_result import ComplianceResult
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.human_review import HumanReviewItem, ReviewStatus
from app.db.models.organization_identity import OrganizationIdentityAssessment
from app.db.models.commercial_evaluation import CommercialEvaluationResult
from app.db.models.audit_event import AuditActorSource, AuditEntityType, AuditEventType
from app.schemas.audit import RecordAuditEventDTO
from app.services.audit.audit_service import AuditService

logger = logging.getLogger(__name__)


class CommercialEvaluationService:
    """Service providing deterministic commercial evaluation and multi-method ranking for procurement tenders."""

    @staticmethod
    def evaluate_tender_commercial_bids(
        db: Session,
        tender_id: uuid.UUID,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> List[CommercialEvaluationResult]:
        """
        Executes deterministic commercial evaluation across all submitted bids for a tender.
        Adheres to configured evaluation method (L1, QCBS, CUSTOM_WEIGHTED).
        Applies Mandatory Eligibility Gate before pricing comparisons.
        """
        stmt = (
            select(Tender)
            .options(
                joinedload(Tender.organization),
                joinedload(Tender.bids),
            )
            .where(Tender.id == tender_id, Tender.is_active == True)
        )
        tender = db.execute(stmt).unique().scalar_one_or_none()
        if not tender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tender not found.",
            )

        # Audit evaluation initiation
        AuditService.record_event(
            db=db,
            event_dto=RecordAuditEventDTO(
                organization_id=tender.organization_id,
                tender_id=tender.id,
                actor_source=AuditActorSource.SYSTEM if not actor_user_id else AuditActorSource.HUMAN,
                actor_user_id=actor_user_id,
                event_type=AuditEventType.COMMERCIAL_EVALUATION_STARTED,
                entity_type=AuditEntityType.TENDER,
                entity_id=tender.id,
                action="COMMERCIAL_EVALUATION_STARTED",
                summary=f"Commercial evaluation started for tender {tender.tender_number} using {tender.evaluation_method}.",
                metadata={"evaluation_method": tender.evaluation_method},
            ),
        )

        submitted_bids = [b for b in tender.bids if b.status in ("SUBMITTED", "UNDER_EVALUATION", "EVALUATED") and b.is_active]

        if not submitted_bids:
            logger.info(f"No submitted bids found for tender {tender_id}.")
            return []

        # Mark prior evaluation snapshots as not current
        db.query(CommercialEvaluationResult).filter(
            CommercialEvaluationResult.tender_id == tender_id,
            CommercialEvaluationResult.is_current == True,
        ).update({"is_current": False})

        # Step 1: Evaluate Mandatory Compliance & Technical Score for each bid
        bid_eval_data: List[Dict[str, Any]] = []

        for bid in submitted_bids:
            # Check mandatory compliance failures
            comp_results = (
                db.query(ComplianceResult)
                .filter(ComplianceResult.bid_id == bid.id)
                .all()
            )
            mandatory_failures = [
                cr for cr in comp_results
                if cr.compliance_status in ("FAIL", "NON_COMPLIANT")
            ]
            open_mandatory_reviews = (
                db.query(HumanReviewItem)
                .filter(
                    HumanReviewItem.bid_id == bid.id,
                    HumanReviewItem.status == ReviewStatus.OPEN,
                )
                .all()
            )

            # Determine Technical Score (from BidScoreSnapshot or Compliance score ratio)
            score_snap = (
                db.query(BidScoreSnapshot)
                .filter(BidScoreSnapshot.bid_id == bid.id, BidScoreSnapshot.is_current == True)
                .order_by(BidScoreSnapshot.calculated_at.desc())
                .first()
            )
            technical_score = 0.0
            if score_snap and score_snap.overall_score is not None:
                technical_score = float(score_snap.overall_score)
            elif comp_results:
                passed_count = sum(1 for cr in comp_results if cr.compliance_status in ("PASS", "COMPLIANT"))
                technical_score = round((passed_count / max(len(comp_results), 1)) * 100.0, 2)

            # Check Risk Level
            risk_snap = (
                db.query(BidRiskSnapshot)
                .filter(BidRiskSnapshot.bid_id == bid.id, BidRiskSnapshot.is_current == True)
                .order_by(BidRiskSnapshot.calculated_at.desc())
                .first()
            )
            is_critical_risk = False
            if risk_snap:
                level = risk_snap.adjusted_risk_level or risk_snap.base_risk_level
                if level in ("CRITICAL", "HIGH"):
                    is_critical_risk = True

            # Determine Mandatory Eligibility
            eligibility_status = "ELIGIBLE"
            ineligible_reason = None
            if mandatory_failures:
                eligibility_status = "INELIGIBLE_MANDATORY_FAILED"
                ineligible_reason = f"Failed {len(mandatory_failures)} mandatory tender requirement(s)."
            elif open_mandatory_reviews:
                eligibility_status = "REVIEW_REQUIRED"
                ineligible_reason = f"{len(open_mandatory_reviews)} mandatory review item(s) pending resolution."

            quoted_amt = None
            if bid.quoted_amount is not None:
                try:
                    quoted_amt = Decimal(str(bid.quoted_amount))
                except Exception:
                    quoted_amt = None

            bid_eval_data.append({
                "bid": bid,
                "eligibility_status": eligibility_status,
                "ineligible_reason": ineligible_reason,
                "technical_score": technical_score,
                "quoted_amount": quoted_amt,
                "currency": bid.currency or "INR",
                "is_critical_risk": is_critical_risk,
                "open_reviews_count": len(open_mandatory_reviews),
            })

        # Step 2: Separate Eligible vs Ineligible bids
        eligible_bids = [
            b for b in bid_eval_data
            if b["eligibility_status"] == "ELIGIBLE" and b["quoted_amount"] is not None and b["quoted_amount"] > 0
        ]

        eval_results: List[CommercialEvaluationResult] = []
        method = tender.evaluation_method or "L1_LOWEST_COMPLIANT_BID"

        # Find lowest compliant price among eligible bidders
        lowest_eligible_price: Optional[Decimal] = None
        if eligible_bids:
            lowest_eligible_price = min(b["quoted_amount"] for b in eligible_bids)

        # Step 3: Evaluate by Method
        if method == "L1_LOWEST_COMPLIANT_BID":
            # Sort eligible bids ascending by quoted amount
            eligible_bids.sort(key=lambda x: x["quoted_amount"])

            # Check for Price Ties
            price_counts: Dict[Decimal, int] = {}
            for b in eligible_bids:
                price_counts[b["quoted_amount"]] = price_counts.get(b["quoted_amount"], 0) + 1

            for rank_idx, b in enumerate(eligible_bids, start=1):
                amt = b["quoted_amount"]
                is_tie = price_counts.get(amt, 0) > 1
                is_l1 = (rank_idx == 1) or (is_tie and amt == lowest_eligible_price)

                if is_tie:
                    rank_label = f"L{rank_idx} (COMMERCIAL TIE)" if not is_l1 else "L1 (COMMERCIAL TIE)"
                    explanation = (
                        f"Bidder passed all mandatory eligibility requirements with evaluated price of "
                        f"{b['currency']} {amt:,.2f}. Tied with another compliant bidder. "
                        f"Tie-breaking process required under procurement rules."
                    )
                else:
                    rank_label = f"L{rank_idx}"
                    if is_l1:
                        explanation = (
                            f"Bidder passed all mandatory eligibility requirements and submitted the "
                            f"lowest evaluated compliant price of {b['currency']} {amt:,.2f} ({rank_label})."
                        )
                    else:
                        diff_pct = (
                            round(float(((amt - lowest_eligible_price) / lowest_eligible_price) * 100), 2)
                            if lowest_eligible_price else 0.0
                        )
                        explanation = (
                            f"Bidder passed mandatory eligibility with evaluated price of "
                            f"{b['currency']} {amt:,.2f} ({diff_pct}% above L1)."
                        )

                # Financial Score for L1 method: 100 for L1, scaled inversely for higher
                fin_score = 100.0
                if lowest_eligible_price and amt > 0:
                    fin_score = round(float((lowest_eligible_price / amt) * Decimal("100.0")), 2)

                # Check safety blockers for top-ranked bidder
                has_blocker = False
                blocker_reason = None
                if is_l1 and (b["is_critical_risk"] or b["open_reviews_count"] > 0):
                    has_blocker = True
                    blocker_reason = (
                        "Commercially ranked L1, but final qualification and award consideration is "
                        "blocked pending resolution of critical review / risk alerts."
                    )

                res = CommercialEvaluationResult(
                    id=uuid.uuid4(),
                    tender_id=tender_id,
                    bid_id=b["bid"].id,
                    evaluation_method=method,
                    eligibility_status="ELIGIBLE",
                    quoted_amount=amt,
                    currency=b["currency"],
                    technical_score=b["technical_score"],
                    financial_score=fin_score,
                    final_score=fin_score,
                    commercial_rank=rank_idx,
                    rank_label=rank_label,
                    is_l1=is_l1,
                    is_tie=is_tie,
                    has_critical_blocker=has_blocker,
                    blocker_reason=blocker_reason,
                    explanation=explanation,
                    formula_snapshot={
                        "method": "L1_LOWEST_COMPLIANT_BID",
                        "lowest_eligible_price": str(lowest_eligible_price) if lowest_eligible_price else None,
                        "quoted_amount": str(amt),
                    },
                    is_current=True,
                    evaluated_at=datetime.now(timezone.utc),
                )
                eval_results.append(res)

        elif method == "QCBS_TECHNICAL_FINANCIAL":
            # QCBS Quality and Cost Based Selection
            tech_w = float(tender.technical_weight if tender.technical_weight is not None else 70.0)
            fin_w = float(tender.financial_weight if tender.financial_weight is not None else 30.0)
            if round(tech_w + fin_w, 1) != 100.0:
                tech_w, fin_w = 70.0, 30.0

            # Calculate Financial Score & QCBS Final Score for each eligible bidder
            for b in eligible_bids:
                amt = b["quoted_amount"]
                fin_score = 100.0
                if lowest_eligible_price and amt > 0:
                    fin_score = round(float((lowest_eligible_price / amt) * Decimal("100.0")), 2)
                
                tech_score = b["technical_score"]
                final_score = round((tech_score * (tech_w / 100.0)) + (fin_score * (fin_w / 100.0)), 2)
                b["financial_score"] = fin_score
                b["final_score"] = final_score

            # Sort eligible bids descending by Final Score
            eligible_bids.sort(key=lambda x: x["final_score"], reverse=True)

            score_counts: Dict[float, int] = {}
            for b in eligible_bids:
                score_counts[b["final_score"]] = score_counts.get(b["final_score"], 0) + 1

            for rank_idx, b in enumerate(eligible_bids, start=1):
                f_score = b["final_score"]
                is_tie = score_counts.get(f_score, 0) > 1
                rank_label = f"Rank #{rank_idx} (TIE)" if is_tie else f"Rank #{rank_idx}"

                explanation = (
                    f"Bidder achieved a combined QCBS score of {f_score} "
                    f"(Technical: {b['technical_score']} × {int(tech_w)}%, "
                    f"Financial: {b['financial_score']} × {int(fin_w)}%), ranking {rank_label}."
                )

                has_blocker = False
                blocker_reason = None
                if rank_idx == 1 and (b["is_critical_risk"] or b["open_reviews_count"] > 0):
                    has_blocker = True
                    blocker_reason = (
                        "Ranked #1 on QCBS combined score, but qualification determination is blocked "
                        "pending resolution of critical review / risk flags."
                    )

                res = CommercialEvaluationResult(
                    id=uuid.uuid4(),
                    tender_id=tender_id,
                    bid_id=b["bid"].id,
                    evaluation_method=method,
                    eligibility_status="ELIGIBLE",
                    quoted_amount=b["quoted_amount"],
                    currency=b["currency"],
                    technical_score=b["technical_score"],
                    financial_score=b["financial_score"],
                    final_score=f_score,
                    commercial_rank=rank_idx,
                    rank_label=rank_label,
                    is_l1=False,  # QCBS uses combined ranking
                    is_tie=is_tie,
                    has_critical_blocker=has_blocker,
                    blocker_reason=blocker_reason,
                    explanation=explanation,
                    formula_snapshot={
                        "method": "QCBS_TECHNICAL_FINANCIAL",
                        "technical_weight": tech_w,
                        "financial_weight": fin_w,
                        "formula": "Final = (Technical × TechWeight) + (Financial × FinWeight)",
                        "financial_formula": "Financial = (LowestPrice / QuotedPrice) × 100",
                        "lowest_eligible_price": str(lowest_eligible_price) if lowest_eligible_price else None,
                    },
                    is_current=True,
                    evaluated_at=datetime.now(timezone.utc),
                )
                eval_results.append(res)

        else:
            # CUSTOM_WEIGHTED Evaluation
            custom_weights = tender.custom_weights_json or {"technical": 70.0, "financial": 30.0}
            tech_w = float(custom_weights.get("technical", 70.0))
            fin_w = float(custom_weights.get("financial", 30.0))

            for b in eligible_bids:
                amt = b["quoted_amount"]
                fin_score = 100.0
                if lowest_eligible_price and amt > 0:
                    fin_score = round(float((lowest_eligible_price / amt) * Decimal("100.0")), 2)
                tech_score = b["technical_score"]
                final_score = round((tech_score * (tech_w / 100.0)) + (fin_score * (fin_w / 100.0)), 2)
                b["financial_score"] = fin_score
                b["final_score"] = final_score

            eligible_bids.sort(key=lambda x: x["final_score"], reverse=True)

            for rank_idx, b in enumerate(eligible_bids, start=1):
                f_score = b["final_score"]
                rank_label = f"Rank #{rank_idx}"
                explanation = f"Evaluated under custom weighted criteria with final score of {f_score}."

                res = CommercialEvaluationResult(
                    id=uuid.uuid4(),
                    tender_id=tender_id,
                    bid_id=b["bid"].id,
                    evaluation_method=method,
                    eligibility_status="ELIGIBLE",
                    quoted_amount=b["quoted_amount"],
                    currency=b["currency"],
                    technical_score=b["technical_score"],
                    financial_score=b["financial_score"],
                    final_score=f_score,
                    commercial_rank=rank_idx,
                    rank_label=rank_label,
                    is_l1=False,
                    is_tie=False,
                    has_critical_blocker=False,
                    blocker_reason=None,
                    explanation=explanation,
                    formula_snapshot={"custom_weights": custom_weights},
                    is_current=True,
                    evaluated_at=datetime.now(timezone.utc),
                )
                eval_results.append(res)

        # Step 4: Handle Ineligible & Excluded Bids (Never assign L1 or Winning Rank)
        ineligible_bids = [b for b in bid_eval_data if b not in eligible_bids]
        for inel in ineligible_bids:
            reason = inel["ineligible_reason"] or "Mandatory eligibility criteria not met or invalid quoted price."
            res = CommercialEvaluationResult(
                id=uuid.uuid4(),
                tender_id=tender_id,
                bid_id=inel["bid"].id,
                evaluation_method=method,
                eligibility_status=inel["eligibility_status"],
                quoted_amount=inel["quoted_amount"],
                currency=inel["currency"],
                technical_score=inel["technical_score"],
                financial_score=None,
                final_score=None,
                commercial_rank=None,
                rank_label="INELIGIBLE",
                is_l1=False,
                is_tie=False,
                has_critical_blocker=True,
                blocker_reason=reason,
                explanation=f"Bidder disqualified from commercial ranking: {reason}",
                formula_snapshot={"disqualified": True, "reason": reason},
                is_current=True,
                evaluated_at=datetime.now(timezone.utc),
            )
            eval_results.append(res)

        # Save results to DB
        db.add_all(eval_results)
        db.commit()

        # Emit audit event for generated rankings
        AuditService.record_event(
            db=db,
            event_dto=RecordAuditEventDTO(
                organization_id=tender.organization_id,
                tender_id=tender.id,
                actor_source=AuditActorSource.SYSTEM if not actor_user_id else AuditActorSource.HUMAN,
                actor_user_id=actor_user_id,
                event_type=AuditEventType.COMMERCIAL_RANKING_GENERATED,
                entity_type=AuditEntityType.TENDER,
                entity_id=tender.id,
                action="COMMERCIAL_RANKING_GENERATED",
                summary=f"Commercial ranking generated for {len(eval_results)} bid(s) under {method}.",
                metadata={
                    "total_evaluated": len(eval_results),
                    "eligible_count": len(eligible_bids),
                    "ineligible_count": len(ineligible_bids),
                    "evaluation_method": method,
                },
            ),
        )

        return eval_results

    @staticmethod
    def get_tender_commercial_evaluation(
        db: Session,
        tender_id: uuid.UUID,
    ) -> List[CommercialEvaluationResult]:
        """Retrieves current commercial evaluation results for a tender, calculating dynamically if missing."""
        results = (
            db.query(CommercialEvaluationResult)
            .filter(
                CommercialEvaluationResult.tender_id == tender_id,
                CommercialEvaluationResult.is_current == True,
            )
            .order_by(
                CommercialEvaluationResult.commercial_rank.asc().nullslast(),
                CommercialEvaluationResult.quoted_amount.asc().nullslast(),
            )
            .all()
        )
        if not results:
            results = CommercialEvaluationService.evaluate_tender_commercial_bids(db, tender_id)
        return results
