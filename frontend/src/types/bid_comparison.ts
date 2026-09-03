/**
 * Type definitions for Part 8B: Bid Comparison & Shortlisting View
 */

export interface ShortlistActionRequest {
  reason?: string | null;
}

export interface ShortlistRecordResponse {
  id: string;
  tender_id: string;
  bid_id: string;
  is_shortlisted: boolean;
  reason?: string | null;
  shortlisted_by_id?: string | null;
  shortlisted_by_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CriticalFindingComparisonItem {
  requirement_code: string;
  requirement_name: string;
  category: string;
  compliance_status: string;
  is_mandatory: boolean;
  is_critical: boolean;
  risk_override?: string | null;
  finding_reason: string;
}

export interface CategoryScoreComparisonValue {
  category: string;
  score?: number | null;
  earned_weight: number;
  eligible_weight: number;
  is_na: boolean;
  total_rules: number;
  passed_rules: number;
  failed_rules: number;
  review_rules: number;
  pending_rules: number;
}

export interface CategoryComparisonRow {
  category_code: string;
  display_name: string;
  bid_scores: Record<string, CategoryScoreComparisonValue>;
  all_match: boolean;
}

export interface RequirementBidResultItem {
  bid_id: string;
  compliance_status:
    | "PASS"
    | "FAIL"
    | "REVIEW"
    | "NOT_APPLICABLE"
    | "PENDING"
    | "NOT_EVALUATED";
  actual_value?: any;
  expected_value?: any;
  operator?: string | null;
  reason?: string | null;
  evidence_summary?: string | null;
  has_evidence: boolean;
  source_verification_ids: string[];
}

export interface RequirementComparisonRow {
  requirement_id: string;
  code: string;
  name: string;
  category: string;
  requirement_type: string;
  is_mandatory: boolean;
  is_critical: boolean;
  weight: number;
  expected_value?: any;
  operator?: string | null;
  bid_results: Record<string, RequirementBidResultItem>;
  all_match: boolean;
  has_failure: boolean;
  has_review: boolean;
  has_critical_issue: boolean;
}

export interface BidComparisonItem {
  bid_id: string;
  bid_number: string;
  bidder_organization_id: string;
  bidder_legal_name: string;
  trade_name?: string | null;
  submitted_at?: string | null;
  quoted_amount?: number | null;
  currency: string;

  is_shortlisted: boolean;
  shortlist_reason?: string | null;
  shortlisted_at?: string | null;

  overall_score?: number | null;
  is_score_provisional: boolean;
  scoring_complete: boolean;
  earned_weight: number;
  eligible_weight: number;

  base_risk_score?: number | null;
  base_risk_level?: string | null;
  adjusted_risk_score?: number | null;
  adjusted_risk_level?: string | null;
  override_applied: boolean;
  applied_overrides: Array<{
    rule_code?: string;
    override_type: string;
    risk_floor?: number;
    reason: string;
    severity: string;
  }>;
  is_risk_provisional: boolean;
  risk_complete: boolean;

  mandatory_failure_count: number;
  mandatory_failures: string[];
  critical_failure_count: number;
  critical_findings: CriticalFindingComparisonItem[];
  review_count: number;
  review_items: string[];
  pending_count: number;
  pending_items: string[];

  ai_recommendation?: string | null;
  ai_status: "CURRENT" | "STALE" | "UNAVAILABLE" | "NOT_GENERATED";
  ai_summary?: string | null;
  ai_confidence?: string | null;

  evaluation_status:
    | "NOT_STARTED"
    | "PROCESSING"
    | "PROVISIONAL"
    | "REVIEW_REQUIRED"
    | "EVALUATION_COMPLETE"
    | "AI_STALE";
  is_evaluation_complete: boolean;
  stale_components: string[];

  category_scores: Record<string, CategoryScoreComparisonValue>;
  human_decision_status?: string;

  // Commercial Evaluation
  eligibility_status?: string;
  commercial_rank?: number | null;
  rank_label?: string;
  is_l1?: boolean;
  is_tie?: boolean;
  financial_score?: number | null;
  final_score?: number | null;
  has_critical_blocker?: boolean;
  blocker_reason?: string | null;
  commercial_explanation?: string | null;
}

export interface ComparisonHighlights {
  highest_compliance_score_bid_id?: string | null;
  lowest_risk_score_bid_id?: string | null;
  lowest_quoted_amount_bid_id?: string | null;
}

export interface BidComparisonResponse {
  tender_id: string;
  tender_number: string;
  tender_title: string;
  tender_status: string;
  procurement_organization_name: string;
  submission_end_date?: string | null;
  evaluation_method?: string;
  technical_weight?: number | null;
  financial_weight?: number | null;
  lowest_compliant_price?: number | null;
  total_compared_bids: number;
  bids: BidComparisonItem[];
  categories: CategoryComparisonRow[];
  requirements: RequirementComparisonRow[];
  highlights: ComparisonHighlights;
  generated_at: string;
}

export type RequirementFilterMode =
  | "ALL"
  | "FAILURES_ONLY"
  | "REVIEW_ONLY"
  | "CRITICAL_ONLY"
  | "MANDATORY_ONLY";
