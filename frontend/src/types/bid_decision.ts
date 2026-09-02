/**
 * TypeScript Interfaces for Part 8D: Final Human Decision Workflow
 */

export type BidDecisionStatus = 'NOT_DECIDED' | 'UNDER_REVIEW' | 'QUALIFIED' | 'DISQUALIFIED';

export type DisqualificationReasonCategory =
  | 'MANDATORY_REQUIREMENT_FAILURE'
  | 'CRITICAL_REQUIREMENT_FAILURE'
  | 'DOCUMENT_INSUFFICIENT'
  | 'REGISTRATION_NON_COMPLIANCE'
  | 'FINANCIAL_NON_COMPLIANCE'
  | 'TECHNICAL_NON_COMPLIANCE'
  | 'INTEGRITY_CONCERN'
  | 'OTHER';

export interface DecisionReadiness {
  can_qualify: boolean;
  can_disqualify: boolean;
  can_defer: boolean;
  blocking_reasons: string[];
  warnings: string[];
  evaluation_complete: boolean;
  evaluation_version: number;
  open_review_count: number;
  critical_open_review_count: number;
  mandatory_failures_count: number;
  critical_failures_count: number;
  has_pending_critical_verifications: boolean;
  overall_score?: number | null;
  adjusted_risk_level?: string | null;
  adjusted_risk_score?: number | null;
  ai_recommendation?: string | null;
  is_score_stale: boolean;
  is_risk_stale: boolean;
  is_ai_stale: boolean;
}

export interface DecidedByProfileSummary {
  profile_id: string;
  full_name: string;
  role_name: string;
  organization_name?: string | null;
}

export interface EvaluationSnapshotReference {
  evaluation_version: number;
  score_snapshot_id?: string | null;
  overall_score?: number | null;
  risk_snapshot_id?: string | null;
  adjusted_risk_score?: number | null;
  adjusted_risk_level?: string | null;
  ai_recommendation_id?: string | null;
  ai_recommendation?: string | null;
}

export interface BidDecision {
  id: string;
  organization_id: string;
  tender_id: string;
  bid_id: string;
  bid_number?: string | null;
  bidder_name?: string | null;
  decision: BidDecisionStatus;
  reason: string;
  decision_summary?: string | null;
  category?: string | null;
  decided_at: string;
  decision_version: number;
  decided_by: DecidedByProfileSummary;
  is_current: boolean;
  is_stale: boolean;
  stale_reason?: string | null;
  snapshot_reference: EvaluationSnapshotReference;
  readiness?: DecisionReadiness | null;
}

export interface BidDecisionHistoryItem {
  id: string;
  decision_version: number;
  decision: BidDecisionStatus;
  reason: string;
  decision_summary?: string | null;
  category?: string | null;
  decided_at: string;
  decided_by_name: string;
  decided_by_role: string;
  is_current: boolean;
  is_stale: boolean;
  stale_reason?: string | null;
  superseded_at?: string | null;
}

export interface RecordBidDecisionRequest {
  decision: BidDecisionStatus;
  reason: string;
  decision_summary?: string | null;
  category?: DisqualificationReasonCategory | null;
}
