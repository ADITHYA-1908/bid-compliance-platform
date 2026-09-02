"""
AI Recommendation & Q&A Service for Part 7E: RAG + AI Recommendation & Evidence-Based Explanation
Orchestrates knowledge indexing, scoped retrieval, prompt execution, guardrail enforcement,
database persistence, and stale recommendation tracking.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.bid import Bid
from app.db.models.compliance_result import ComplianceResult
from app.db.models.profile import Profile
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.tender import Tender
from app.db.models.user import User
from app.services.ai.ai_config import PROMPT_VERSION
from app.services.ai.ai_models import (
    AIQuestionAnswerOutput,
    AIRecommendationOutput,
    EvidenceRef,
)
from app.services.ai.llm_service import LLMService
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.rag_indexing_service import RAGIndexingService
from app.services.ai.rag_retrieval_service import RAGRetrievalService
from app.services.ai.recommendation_guardrail import RecommendationGuardrail

logger = logging.getLogger(__name__)


def _verify_ai_access(db: Session, user: User, bid_id: uuid.UUID) -> Tuple[Bid, Profile]:
    """
    Validates that user has authorized access to AI evaluation features for the target Bid.
    Only authorized Procurement Officers belonging to the Tender's organization and Admins are permitted.
    Bidders and cross-tenant users are denied.
    """
    stmt = (
        select(Bid)
        .options(
            joinedload(Bid.tender),
            joinedload(Bid.bidder_organization),
        )
        .where(Bid.id == bid_id)
    )
    bid = db.execute(stmt).scalar_one_or_none()
    if not bid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid not found or access denied.",
        )

    profile = db.scalars(select(Profile).where(Profile.id == user.profile_id)).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User profile not found.",
        )

    role = db.scalars(select(Role).where(Role.id == profile.role_id)).first()
    role_name = role.name if role else ""

    if role_name == "ADMIN":
        return bid, profile

    if role_name == "PROCUREMENT_OFFICER":
        if not bid.tender or bid.tender.organization_id != profile.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bid not found or access denied.",
            )
        return bid, profile

    # Bidder or other roles are forbidden from internal AI evaluation recommendations
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="AI evaluation recommendations are restricted to authorized Procurement Officers.",
    )


class AIRecommendationService:
    """
    Service layer for generating grounded AI recommendations and answering officer inquiries.
    """

    @classmethod
    def generate_bid_recommendation(
        cls,
        db: Session,
        user: User,
        bid_id: uuid.UUID,
        force_refresh: bool = False,
    ) -> AIRecommendationRecord:
        """
        Executes full RAG workflow to generate and persist a grounded AI evaluation recommendation.
        """
        bid, profile = _verify_ai_access(db, user, bid_id)

        # 1. Fetch current snapshots
        score_snap = db.scalars(
            select(BidScoreSnapshot).where(
                BidScoreSnapshot.bid_id == bid_id,
                BidScoreSnapshot.is_current == True,  # noqa: E712
            )
        ).first()

        risk_snap = db.scalars(
            select(BidRiskSnapshot).where(
                BidRiskSnapshot.bid_id == bid_id,
                BidRiskSnapshot.is_current == True,  # noqa: E712
            )
        ).first()

        # 2. Check if a non-stale recommendation already exists (unless force_refresh)
        if not force_refresh:
            existing = db.scalars(
                select(AIRecommendationRecord)
                .where(
                    AIRecommendationRecord.bid_id == bid_id,
                    AIRecommendationRecord.is_stale == False,  # noqa: E712
                )
                .order_by(AIRecommendationRecord.created_at.desc())
            ).first()

            if existing:
                # Check if upstream data has changed since creation
                if (
                    score_snap
                    and existing.score_snapshot_id == score_snap.id
                    and risk_snap
                    and existing.risk_snapshot_id == risk_snap.id
                ):
                    return existing

        # 3. Index/re-index knowledge chunks for this bid
        RAGIndexingService.index_full_bid_knowledge(db, bid_id)

        # 4. Scoped vector retrieval of top evidence chunks
        evidence_chunks = RAGRetrievalService.retrieve_evidence(
            db=db,
            tender_id=bid.tender_id,
            bid_id=bid.id,
            query="evaluation compliance requirements risk verification findings",
            top_k=settings.RAG_TOP_K,
        )

        # 5. Build structured prompt context
        tender_meta = {
            "tender_number": bid.tender.tender_number if bid.tender else "N/A",
            "title": bid.tender.title if bid.tender else "N/A",
        }
        bid_meta = {
            "bid_number": bid.bid_number,
            "bidder_name": bid.bidder_organization.name if bid.bidder_organization else "N/A",
        }
        score_data = {
            "overall_score": float(score_snap.overall_score) if score_snap and score_snap.overall_score is not None else None,
            "mandatory_failure_count": getattr(score_snap, "mandatory_failures_count", getattr(score_snap, "mandatory_failure_count", 0)) if score_snap else 0,
            "critical_failure_count": getattr(score_snap, "critical_failures_count", getattr(score_snap, "critical_failure_count", 0)) if score_snap else 0,
        } if score_snap else None

        risk_data = {
            "base_risk_score": float(risk_snap.base_risk_score) if risk_snap and risk_snap.base_risk_score is not None else None,
            "base_risk_level": risk_snap.base_risk_level if risk_snap else None,
            "adjusted_risk_score": float(risk_snap.adjusted_risk_score) if risk_snap and risk_snap.adjusted_risk_score is not None else None,
            "adjusted_risk_level": risk_snap.adjusted_risk_level if risk_snap else None,
            "override_applied": risk_snap.override_applied if risk_snap else False,
            "override_count": risk_snap.override_count if risk_snap else 0,
            "summary_reasons": risk_snap.summary_reasons if risk_snap else [],
        } if risk_snap else None

        user_prompt = PromptBuilder.build_recommendation_prompt(
            tender_meta=tender_meta,
            bid_meta=bid_meta,
            score_data=score_data,
            risk_data=risk_data,
            evidence_chunks=evidence_chunks,
        )

        # 6. Invoke LLM
        llm_output = LLMService.generate_structured_completion(
            system_prompt=PromptBuilder.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=AIRecommendationOutput,
        )

        # 7. Apply deterministic recommendation guardrail & citation validation
        adjusted_output, guardrail_applied, guardrail_reason = RecommendationGuardrail.validate_and_adjust_recommendation(
            llm_output=llm_output,
            risk_snapshot=risk_snap,
            score_snapshot=score_snap,
            retrieved_chunks=evidence_chunks,
        )

        # 8. Mark previous recommendations for this bid as stale
        db.execute(
            update(AIRecommendationRecord)
            .where(AIRecommendationRecord.bid_id == bid_id)
            .values(is_stale=True)
        )

        # 9. Persist new recommendation record
        rec_record = AIRecommendationRecord(
            bid_id=bid.id,
            score_snapshot_id=score_snap.id if score_snap else None,
            risk_snapshot_id=risk_snap.id if risk_snap else None,
            compliance_evaluation_version=1,
            recommendation=adjusted_output.recommendation.value,
            recommendation_reason=adjusted_output.recommendation_reason,
            summary=adjusted_output.summary,
            strengths=adjusted_output.strengths,
            concerns=adjusted_output.concerns,
            review_items=adjusted_output.review_items,
            evidence_refs=[ref.model_dump() for ref in adjusted_output.evidence_refs],
            limitations=adjusted_output.limitations,
            confidence_label=adjusted_output.confidence_label.value,
            model_provider=settings.LLM_PROVIDER,
            model_name=settings.LLM_MODEL,
            prompt_version=PROMPT_VERSION,
            guardrail_applied=guardrail_applied,
            guardrail_reason=guardrail_reason,
            is_stale=False,
        )
        db.add(rec_record)
        db.commit()
        db.refresh(rec_record)

        return rec_record

    @classmethod
    def get_bid_recommendation(
        cls,
        db: Session,
        user: User,
        bid_id: uuid.UUID,
    ) -> Tuple[Optional[AIRecommendationRecord], bool]:
        """
        Retrieves current AI recommendation record for a Bid, detecting if upstream changes caused staleness.
        """
        bid, profile = _verify_ai_access(db, user, bid_id)

        rec = db.scalars(
            select(AIRecommendationRecord)
            .where(AIRecommendationRecord.bid_id == bid_id)
            .order_by(AIRecommendationRecord.created_at.desc())
        ).first()

        if not rec:
            return None, False

        # Staleness check against active snapshots
        score_snap = db.scalars(
            select(BidScoreSnapshot).where(
                BidScoreSnapshot.bid_id == bid_id,
                BidScoreSnapshot.is_current == True,  # noqa: E712
            )
        ).first()

        risk_snap = db.scalars(
            select(BidRiskSnapshot).where(
                BidRiskSnapshot.bid_id == bid_id,
                BidRiskSnapshot.is_current == True,  # noqa: E712
            )
        ).first()

        is_stale = rec.is_stale
        if score_snap and rec.score_snapshot_id != score_snap.id:
            is_stale = True
        if risk_snap and rec.risk_snapshot_id != risk_snap.id:
            is_stale = True

        if is_stale and not rec.is_stale:
            rec.is_stale = True
            db.commit()

        return rec, is_stale

    @classmethod
    def ask_bid_question(
        cls,
        db: Session,
        user: User,
        bid_id: uuid.UUID,
        question: str,
    ) -> AIQuestionAnswerOutput:
        """
        Answers an interactive question from a Procurement Officer regarding a specific Bid proposal.
        """
        bid, profile = _verify_ai_access(db, user, bid_id)

        # 1. Scoped vector retrieval for the question
        evidence_chunks = RAGRetrievalService.retrieve_evidence(
            db=db,
            tender_id=bid.tender_id,
            bid_id=bid.id,
            query=question,
            top_k=6,
        )

        tender_meta = {
            "tender_number": bid.tender.tender_number if bid.tender else "N/A",
            "title": bid.tender.title if bid.tender else "N/A",
        }
        bid_meta = {
            "bid_number": bid.bid_number,
            "bidder_name": bid.bidder_organization.name if bid.bidder_organization else "N/A",
        }

        user_prompt = PromptBuilder.build_qa_prompt(
            question=question,
            tender_meta=tender_meta,
            bid_meta=bid_meta,
            evidence_chunks=evidence_chunks,
        )

        qa_output = LLMService.generate_structured_completion(
            system_prompt=PromptBuilder.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=AIQuestionAnswerOutput,
        )

        # Validate citation IDs
        valid_source_ids = {chunk.source_id for chunk in evidence_chunks}
        valid_citations = [
            ref for ref in qa_output.evidence_refs
            if ref.source_id in valid_source_ids or any(ref.source_id in str(c.metadata) for c in evidence_chunks)
        ]
        qa_output.evidence_refs = valid_citations

        return qa_output
