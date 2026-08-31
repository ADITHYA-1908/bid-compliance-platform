/**
 * Scoring Types for Part 7A
 * Represents scoring readiness, weight totals, rule contributions, and audit snapshots.
 */

export type ScoringStatus =
  | 'READY'
  | 'INCOMPLETE'
  | 'BLOCKED'
  | 'NO_SCORABLE_REQUIREMENTS';

export const ScoringStatusEnum = {
  READY: 'READY' as const,
  INCOMPLETE: 'INCOMPLETE' as const,
  BLOCKED: 'BLOCKED' as const,
  NO_SCORABLE_REQUIREMENTS: 'NO_SCORABLE_REQUIREMENTS' as const,
};

export interface RuleScoreContribution {
  compliance_result_id?: string | null;
  requirement_id: string;
  requirement_code: string;
  requirement_name: string;
  category: string;
  status: string;

  weight: number | string;
  score_factor: number | string;
  earned_weight: number | string;
  eligible_weight: number | string;

  is_mandatory: boolean;
  is_critical: boolean;
  critical_failure: boolean;

  excluded_from_score: boolean;
  exclusion_reason?: string | null;
}

export interface ScoringReadiness {
  scoring_ready: boolean;
  scoring_complete: boolean;
  human_review_required: boolean;
  scoring_status: ScoringStatus;

  total_rules: number;
  passed_rules: number;
  failed_rules: number;
  review_rules: number;
  pending_rules: number;
  not_applicable_rules: number;
  mandatory_failures: number;
  critical_failures: number;
}

export interface CategoryScore {
  category: string;
  display_name: string;

  total_rules: number;
  passed_rules: number;
  failed_rules: number;
  review_rules: number;
  pending_rules: number;
  not_applicable_rules: number;
  mandatory_failures: number;
  critical_failures: number;

  earned_weight: number | string;
  eligible_weight: number | string;

  raw_score?: number | string | null;
  display_score?: number | string | null;

  scoring_complete: boolean;
  human_review_required: boolean;
  is_provisional: boolean;
  rule_contributions?: RuleScoreContribution[];
}

export interface BidScoringFoundationResponse {
  bid_id: string;
  tender_id: string;
  scoring_version: number;
  scoring_formula_version: string;

  readiness: ScoringReadiness;
  earned_weight: number | string;
  eligible_weight: number | string;

  overall_score?: number | string | null;
  is_provisional?: boolean;

  category_scores?: Record<string, CategoryScore>;
  rule_contributions: RuleScoreContribution[];
  calculation_details?: Record<string, any>;
  calculated_at?: string;
}

