"""
AI & RAG Services Module for Part 7E: RAG + AI Recommendation & Evidence-Based Explanation
"""

from app.services.ai.ai_config import (
    AIRecommendationEnum,
    ConfidenceLabelEnum,
    DISCLAIMER_TEXT,
    PROMPT_VERSION,
    RAGSourceType,
    SOURCE_PRIORITY_MULTIPLIERS,
)
from app.services.ai.ai_models import (
    AIQuestionAnswerOutput,
    AIRecommendationOutput,
    EvidenceRef,
    RAGIndexResult,
    RetrievedEvidence,
)
from app.services.ai.embedding_service import EmbeddingService
from app.services.ai.llm_service import LLMService
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.rag_indexing_service import RAGIndexingService
from app.services.ai.rag_retrieval_service import RAGRetrievalService
from app.services.ai.recommendation_guardrail import RecommendationGuardrail
from app.services.ai.ai_recommendation_service import AIRecommendationService

__all__ = [
    "AIRecommendationEnum",
    "ConfidenceLabelEnum",
    "RAGSourceType",
    "SOURCE_PRIORITY_MULTIPLIERS",
    "PROMPT_VERSION",
    "DISCLAIMER_TEXT",
    "EvidenceRef",
    "RetrievedEvidence",
    "AIRecommendationOutput",
    "AIQuestionAnswerOutput",
    "RAGIndexResult",
    "EmbeddingService",
    "LLMService",
    "PromptBuilder",
    "RAGIndexingService",
    "RAGRetrievalService",
    "RecommendationGuardrail",
    "AIRecommendationService",
]
