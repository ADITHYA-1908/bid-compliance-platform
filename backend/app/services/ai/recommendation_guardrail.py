"""
Recommendation Guardrail & Citation Validator for Part 7E: RAG + AI Recommendation & Evidence-Based Explanation
Enforces strict deterministic policy alignment, prevents contradictory LLM recommendations,
and validates that all citations correspond to actually retrieved evidence chunks.
"""

import logging
from typing import List, Optional, Set, Tuple

from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.score_snapshot import BidScoreSnapshot
from app.services.ai.ai_config import AIRecommendationEnum
from app.services.ai.ai_models import AIRecommendationOutput, EvidenceRef, RetrievedEvidence

logger = logging.getLogger(__name__)


class RecommendationGuardrail:
    """
    Validates LLM recommendation against deterministic ground truth and strips fake citations.
    """

    @classmethod
    def validate_and_adjust_recommendation(
        cls,
        llm_output: AIRecommendationOutput,
        risk_snapshot: Optional[BidRiskSnapshot],
        score_snapshot: Optional[BidScoreSnapshot],
        retrieved_chunks: List[RetrievedEvidence],
    ) -> Tuple[AIRecommendationOutput, bool, Optional[str]]:
        """
        Validates LLM recommendation against deterministic risk and score states.
        Returns: (adjusted_output, guardrail_applied, guardrail_reason)
        """
        guardrail_applied = False
        guardrail_reason: Optional[str] = None
        current_rec = llm_output.recommendation

        # 1. Validate Citations against actually retrieved evidence chunks
        valid_source_ids: Set[str] = {chunk.source_id for chunk in retrieved_chunks}
        valid_chunk_ids: Set[str] = {chunk.chunk_id for chunk in retrieved_chunks}
        all_valid_ids = valid_source_ids | valid_chunk_ids

        validated_citations: List[EvidenceRef] = []
        for ref in llm_output.evidence_refs:
            if ref.source_id in all_valid_ids or any(ref.source_id in str(c.metadata) for c in retrieved_chunks):
                validated_citations.append(ref)
            else:
                logger.warning(f"Stripping hallucinated / invalid evidence citation ID: {ref.source_id}")

        llm_output.evidence_refs = validated_citations

        # 2. Insufficient Evidence Rule
        if not retrieved_chunks:
            if current_rec != AIRecommendationEnum.INSUFFICIENT_EVIDENCE:
                llm_output.recommendation = AIRecommendationEnum.INSUFFICIENT_EVIDENCE
                guardrail_applied = True
                guardrail_reason = "Enforced INSUFFICIENT_EVIDENCE because no relevant evidence chunks were available."
                return llm_output, guardrail_applied, guardrail_reason

        # 3. Critical Risk Policy: If Adjusted Risk is CRITICAL -> Cannot PROCEED
        adjusted_level = risk_snapshot.adjusted_risk_level if risk_snapshot else None
        adjusted_score = float(risk_snapshot.adjusted_risk_score) if (risk_snapshot and risk_snapshot.adjusted_risk_score is not None) else None

        if adjusted_level == "CRITICAL" or (adjusted_score is not None and adjusted_score >= 75.0):
            if current_rec in (AIRecommendationEnum.PROCEED, AIRecommendationEnum.PROCEED_WITH_REVIEW):
                llm_output.recommendation = AIRecommendationEnum.DO_NOT_PROCEED_WITHOUT_REVIEW
                guardrail_applied = True
                guardrail_reason = (
                    f"Corrected recommendation from '{current_rec.value}' to "
                    f"'{AIRecommendationEnum.DO_NOT_PROCEED_WITHOUT_REVIEW.value}' "
                    f"because deterministic adjusted risk level is CRITICAL ({adjusted_score}/100)."
                )
                logger.info(f"Guardrail triggered: {guardrail_reason}")
                return llm_output, guardrail_applied, guardrail_reason

        # 4. Critical Failure Policy: If critical requirement failed -> Must require review
        crit_fails = getattr(score_snapshot, "critical_failures_count", getattr(score_snapshot, "critical_failure_count", 0)) if score_snapshot else 0
        if crit_fails > 0 and current_rec == AIRecommendationEnum.PROCEED:
            llm_output.recommendation = AIRecommendationEnum.DO_NOT_PROCEED_WITHOUT_REVIEW
            guardrail_applied = True
            guardrail_reason = (
                f"Corrected recommendation from '{current_rec.value}' to "
                f"'{AIRecommendationEnum.DO_NOT_PROCEED_WITHOUT_REVIEW.value}' "
                f"because {crit_fails} critical requirement failure(s) were confirmed."
            )
            logger.info(f"Guardrail triggered: {guardrail_reason}")
            return llm_output, guardrail_applied, guardrail_reason

        # 5. Mandatory Failure or High Risk Policy
        mand_fails = getattr(score_snapshot, "mandatory_failures_count", getattr(score_snapshot, "mandatory_failure_count", 0)) if score_snapshot else 0
        if (mand_fails > 0 or adjusted_level == "HIGH") and current_rec == AIRecommendationEnum.PROCEED:
            llm_output.recommendation = AIRecommendationEnum.REVIEW_REQUIRED
            guardrail_applied = True
            guardrail_reason = (
                f"Corrected recommendation from '{current_rec.value}' to "
                f"'{AIRecommendationEnum.REVIEW_REQUIRED.value}' "
                f"due to mandatory failure(s) ({mand_fails}) or HIGH risk posture."
            )
            logger.info(f"Guardrail triggered: {guardrail_reason}")
            return llm_output, guardrail_applied, guardrail_reason

        return llm_output, guardrail_applied, guardrail_reason
