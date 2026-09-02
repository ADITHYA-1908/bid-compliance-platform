/**
 * Type definitions for Part 8A: Procurement Evaluation Dashboard Foundation
 */

export interface ProcurementDashboardCounts {
  active_tenders: number;
  open_tenders: number;
  closed_under_evaluation: number;
  total_submitted_bids: number;
  bids_requiring_review: number;
  critical_risk_bids: number;
  pending_evaluations: number;
  evaluation_completed_bids: number;
}

export interface TenderEvaluationOverviewItem {
  tender_id: string;
  tender_number: string;
  title: string;
  category?: string | null;
  department?: string | null;
  status: string;
  estimated_value?: number | null;
  currency: string;
  submission_end_date?: string | null;
  total_submitted_bids: number;
  evaluated_bids: number;
  pending_bids: number;
  review_required_bids: number;
  critical_risk_bids: number;
  evaluation_progress_percentage: number;
  created_at: string;
}

export interface ProcurementDashboardSummaryResponse {
  counts: ProcurementDashboardCounts;
  tenders: TenderEvaluationOverviewItem[];
  generated_at: string;
}

export interface BidEvaluationListItem {
  bid_id: string;
  tender_id: string;
  bid_number: string;
  bidder_organization_id: string;
  bidder_legal_name: string;
  trade_name?: string | null;
  submitted_at?: string | null;
  quoted_amount?: number | null;
  currency: string;
  is_shortlisted: boolean;

  compliance_score?: number | null;
  is_score_provisional: boolean;

  base_risk_score?: number | null;
  base_risk_level?: string | null;
  adjusted_risk_score?: number | null;
  adjusted_risk_level?: string | null;
  is_risk_provisional: boolean;

  mandatory_failures_count: number;
  critical_failures_count: number;
  review_items_count: number;
  has_critical_findings: boolean;
  critical_findings_count: number;
  human_review_required: boolean;

  ai_recommendation?: string | null;
  ai_status: "CURRENT" | "STALE" | "UNAVAILABLE" | "NOT_GENERATED";

  evaluation_status:
    | "NOT_STARTED"
    | "PROCESSING"
    | "PROVISIONAL"
    | "REVIEW_REQUIRED"
    | "EVALUATION_COMPLETE"
    | "AI_STALE";
  is_evaluation_complete: boolean;
  stale_components: string[];
  human_decision_status?: string;
}

export interface TenderBidEvaluationsListResponse {
  tender_id: string;
  tender_number: string;
  tender_title: string;
  tender_status: string;
  procurement_organization_name: string;
  submission_end_date?: string | null;
  total_submitted_bids: number;
  evaluated_bids: number;
  bids: BidEvaluationListItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  generated_at: string;
}

export interface TenderBidEvaluationsQueryParams {
  search?: string;
  status?: string;
  risk_level?: string;
  review_required?: boolean;
  critical_only?: boolean;
  recommendation?: string;
  shortlisted_only?: boolean;
  sort_by?: "submitted_at" | "score" | "risk" | "review_count" | "critical_count";
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}
