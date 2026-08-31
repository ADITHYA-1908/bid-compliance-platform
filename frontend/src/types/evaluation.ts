/**
 * Evaluation TypeScript Interfaces for Part 7F: Unified Bid Evaluation Summary
 */

export interface EvaluationComplianceSection {
  total_requirements: number;
  pass_count: number;
  fail_count: number;
  review_count: number;
  pending_count: number;
  not_applicable_count: number;
  mandatory_failures_count: number;
  critical_failures_count: number;
  evaluation_complete: boolean;
  evaluation_version: number;
}

export interface CategoryScoreItem {
  category: string;
  score: number | null;
  earned_weight: number;
  eligible_weight: number;
  rule_count: number;
  passed_count: number;
  failed_count: number;
  review_count: number;
  pending_count: number;
}

export interface EvaluationScoreSection {
  overall_compliance_score: number | null;
  score_type: "FINAL" | "PROVISIONAL" | string;
  scoring_complete: boolean;
  earned_weight: number;
  eligible_weight: number;
  category_scores: Record<string, CategoryScoreItem>;
  formula_version: string;
  is_stale: boolean;
  snapshot_id?: string | null;
  scoring_version: number;
}

export interface AppliedOverrideItem {
  override_type: string;
  severity: "WARNING" | "HIGH" | "CRITICAL" | string;
  risk_floor: number;
  target_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;
  rule_code?: string | null;
  reason: string;
}

export interface EvaluationRiskSection {
  base_risk_score: number | null;
  base_risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | null | string;
  adjusted_risk_score: number | null;
  adjusted_risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | null | string;
  override_applied: boolean;
  applied_overrides: AppliedOverrideItem[];
  risk_complete: boolean;
  is_provisional: boolean;
  risk_formula_version: string;
  override_formula_version: string;
  is_stale: boolean;
  snapshot_id?: string | null;
  risk_version: number;
  summary_reasons: string[];
}

export interface EvidenceRef {
  source_type: string;
  source_id: string;
  title: string;
  page?: number | null;
  rule_code?: string | null;
  summary: string;
}

export interface EvaluationAISection {
  status: "CURRENT" | "STALE" | "UNAVAILABLE" | "NOT_GENERATED" | string;
  recommendation?: "PROCEED" | "PROCEED_WITH_REVIEW" | "REVIEW_REQUIRED" | "DO_NOT_PROCEED_WITHOUT_REVIEW" | "INSUFFICIENT_EVIDENCE" | null | string;
  recommendation_reason?: string | null;
  summary?: string | null;
  strengths: string[];
  concerns: string[];
  review_items: string[];
  evidence_refs: EvidenceRef[];
  limitations: string[];
  confidence_label?: "HIGH" | "MEDIUM" | "LOW" | null | string;
  model_provider?: string | null;
  model_name?: string | null;
  prompt_version?: string | null;
  guardrail_applied: boolean;
  guardrail_reason?: string | null;
  recommendation_id?: string | null;
  is_stale: boolean;
}

export interface CriticalFindingItem {
  requirement_code: string;
  requirement_name: string;
  category: string;
  compliance_status: string;
  is_mandatory: boolean;
  is_critical: boolean;
  risk_override?: string | null;
  finding_reason: string;
  evidence_ref?: string | null;
}

export interface EvaluationCriticalSummary {
  critical_failure_present: boolean;
  critical_failure_count: number;
  critical_review_count: number;
  critical_override_applied: boolean;
  critical_findings: CriticalFindingItem[];
}

export interface EvaluationReviewSummary {
  human_review_required: boolean;
  total_review_items: number;
  review_reasons: string[];
  is_provisional: boolean;
}

export interface BidEvaluationSummaryResponse {
  bid_id: string;
  tender_id: string;
  bid_number: string;
  tender_number: string;
  tender_title: string;
  bidder_name: string;
  bid_status: string;

  compliance: EvaluationComplianceSection;
  score: EvaluationScoreSection;
  risk: EvaluationRiskSection;
  ai_recommendation: EvaluationAISection;

  critical_summary: EvaluationCriticalSummary;
  review_summary: EvaluationReviewSummary;

  evaluation_complete: boolean;
  human_review_required: boolean;
  stale_components: string[];
  final_decision_status: string;
  generated_at: string;
}
