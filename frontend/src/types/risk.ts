/**
 * Risk Domain Types for Part 7C & Part 7D: Deterministic Risk & Overrides Engine
 * Represents base risk, adjusted risk, override triggers, feature vectors, and explainable contributions.
 */

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export const RiskLevelEnum = {
  LOW: 'LOW' as const,
  MEDIUM: 'MEDIUM' as const,
  HIGH: 'HIGH' as const,
  CRITICAL: 'CRITICAL' as const,
};

export type RiskIndicator =
  | 'COMPLIANCE_DEFICIT'
  | 'RULE_FAILURES'
  | 'REVIEW_UNCERTAINTY'
  | 'PENDING_UNCERTAINTY'
  | 'MANDATORY_FAILURES'
  | 'INTEGRITY_CONCERNS';

export type RiskOverrideType =
  | 'RISK_FLOOR'
  | 'RISK_INCREMENT'
  | 'LEVEL_FLOOR'
  | 'SCORE_CAP'
  | 'REVIEW_ESCALATION';

export interface RiskContribution {
  indicator: RiskIndicator | string;
  name: string;
  raw_value: string;
  normalized_value: number | string;
  weight: number | string;
  weighted_contribution: number | string;
  reason: string;
}

export interface RiskOverride {
  rule_code?: string | null;
  override_type: RiskOverrideType | string;
  trigger: string;
  source_result_id?: string | null;
  source_requirement_id?: string | null;
  previous_score?: number | string | null;
  new_score?: number | string | null;
  previous_level?: string | null;
  new_level?: string | null;
  risk_floor?: number | string | null;
  risk_increment?: number | string | null;
  minimum_level?: string | null;
  reason: string;
  severity: 'INFO' | 'WARNING' | 'HIGH' | 'CRITICAL' | string;
}

export interface RiskFeatures {
  overall_compliance_score?: number | string | null;
  total_rules: number;
  applicable_rules: number;
  passed_count: number;
  fail_count: number;
  review_count: number;
  pending_count: number;
  not_applicable_count: number;

  mandatory_rules_count: number;
  mandatory_failure_count: number;
  critical_failure_count: number;

  integrity_rules_count: number;
  integrity_fail_count: number;
  integrity_review_count: number;
  cross_document_mismatch_count: number;
  low_confidence_count: number;

  scoring_complete: boolean;
  human_review_required: boolean;
}

export interface BidRiskAssessmentResponse {
  id?: string | null;
  bid_id: string;
  tender_id: string;
  risk_version: number;
  risk_formula_version: string;
  override_formula_version?: string;

  // Part 7C: Mathematical Base Risk
  base_risk_score?: number | string | null;
  base_risk_level?: RiskLevel | string | null;

  // Part 7D: Deterministic Adjusted Risk
  adjusted_risk_score?: number | string | null;
  adjusted_risk_level?: RiskLevel | string | null;

  // Overrides Applied
  override_applied?: boolean;
  override_count?: number;
  applied_overrides?: RiskOverride[];

  // Operational & Readiness Flags
  risk_complete: boolean;
  is_provisional: boolean;
  human_review_required: boolean;

  // Granular Signals & Explanations
  features: RiskFeatures;
  contributions: RiskContribution[];
  summary_reasons: string[];
  calculation_details?: Record<string, any>;
  calculated_at?: string | null;
}
