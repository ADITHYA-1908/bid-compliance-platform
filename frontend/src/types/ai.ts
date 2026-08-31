/**
 * AI & RAG Domain Types for Part 7E: RAG + AI Recommendation & Evidence-Based Explanation
 */

export type AIRecommendationType =
  | 'PROCEED'
  | 'PROCEED_WITH_REVIEW'
  | 'REVIEW_REQUIRED'
  | 'DO_NOT_PROCEED_WITHOUT_REVIEW'
  | 'INSUFFICIENT_EVIDENCE';

export interface EvidenceRef {
  source_type: string;
  source_id: string;
  title: string;
  page?: number | null;
  rule_code?: string | null;
  summary: string;
}

export interface AIRecommendationResponse {
  id?: string | null;
  bid_id: string;
  score_snapshot_id?: string | null;
  risk_snapshot_id?: string | null;
  recommendation: AIRecommendationType | string;
  recommendation_reason: string;
  summary: string;
  strengths: string[];
  concerns: string[];
  review_items: string[];
  evidence_refs: EvidenceRef[];
  limitations: string[];
  confidence_label: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  model_provider: string;
  model_name: string;
  prompt_version: string;
  guardrail_applied: boolean;
  guardrail_reason?: string | null;
  is_stale: boolean;
  disclaimer: string;
  created_at?: string | null;
}

export interface AIQuestionRequest {
  question: string;
}

export interface AIQuestionResponse {
  question: string;
  answer: string;
  evidence_refs: EvidenceRef[];
  limitations: string[];
  disclaimer: string;
}
