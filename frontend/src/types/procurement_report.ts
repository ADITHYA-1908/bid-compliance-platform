export interface ReportTenderInfo {
  tender_id: string;
  tender_number: string;
  title: string;
  status: string;
  organization_name: string;
  category?: string | null;
  procurement_type?: string | null;
  currency: string;
  estimated_value?: number | null;
  published_at?: string | null;
  submission_end_date?: string | null;
}

export interface ReportBidderInfo {
  organization_id: string;
  name: string;
  pan_number?: string | null;
  gstin?: string | null;
  udyam_number?: string | null;
  business_type?: string | null;
  state?: string | null;
  city?: string | null;
}

export interface ReportBidInfo {
  bid_id: string;
  bid_number: string;
  status: string;
  submitted_at?: string | null;
  quoted_amount?: number | null;
  currency: string;
  is_shortlisted: boolean;
  shortlist_reason?: string | null;
}

export interface ReportComplianceSection {
  evaluation_complete: boolean;
  evaluation_version: number;
  total_requirements: number;
  passed_count: number;
  failed_count: number;
  review_count: number;
  pending_count: number;
  not_applicable_count: number;
  mandatory_failures_count: number;
  critical_failures_count: number;
}

export interface ReportScoreSection {
  overall_compliance_score?: number | null;
  score_type: string;
  scoring_complete: boolean;
  earned_weight: number;
  eligible_weight: number;
  category_scores: Record<string, any>;
  scoring_version: number;
  is_stale: boolean;
}

export interface ReportRiskSection {
  base_risk_score?: number | null;
  base_risk_level?: string | null;
  adjusted_risk_score?: number | null;
  adjusted_risk_level?: string | null;
  override_applied: boolean;
  applied_overrides: Array<Record<string, any>>;
  risk_complete: boolean;
  risk_version: number;
  is_stale: boolean;
}

export interface ReportDefectItem {
  requirement_code: string;
  requirement_name: string;
  category: string;
  compliance_status: string;
  is_mandatory: boolean;
  is_critical: boolean;
  reason?: string | null;
}

export interface ReportHumanReviewItem {
  id: string;
  review_type: string;
  severity: string;
  status: string;
  resolution?: string | null;
  reason?: string | null;
  resolved_by_name?: string | null;
  resolved_at?: string | null;
  notes_count: number;
}

export interface ReportAISection {
  recommendation?: string | null;
  recommendation_reason?: string | null;
  summary?: string | null;
  strengths: string[];
  concerns: string[];
  model_provider?: string | null;
  model_name?: string | null;
  prompt_version?: string | null;
  guardrail_applied: boolean;
  guardrail_reason?: string | null;
  confidence_label?: string | null;
  is_stale: boolean;
  advisory_disclaimer: string;
}

export interface ReportFinalDecisionSection {
  decision: string;
  reason?: string | null;
  decision_summary?: string | null;
  category?: string | null;
  decided_by_name?: string | null;
  decided_by_role?: string | null;
  decided_at?: string | null;
  decision_version: number;
  is_current: boolean;
  is_stale: boolean;
  stale_reason?: string | null;
}

export interface ReportDecisionHistoryItem {
  decision_version: number;
  decision: string;
  reason: string;
  decision_summary?: string | null;
  decided_by_name?: string | null;
  decided_at: string;
  is_current: boolean;
  superseded_at?: string | null;
}

export interface ReportAuditEventSummaryItem {
  event_type: string;
  event_label: string;
  action: string;
  actor_name: string;
  actor_source: string;
  summary: string;
  created_at: string;
}

export interface BidEvaluationReportResponse {
  report_id: string;
  report_title: string;
  generated_at: string;
  generated_by: string;
  tender: ReportTenderInfo;
  bidder: ReportBidderInfo;
  bid: ReportBidInfo;
  compliance: ReportComplianceSection;
  score: ReportScoreSection;
  risk: ReportRiskSection;
  mandatory_failures: ReportDefectItem[];
  critical_findings: ReportDefectItem[];
  human_reviews: ReportHumanReviewItem[];
  ai_recommendation?: ReportAISection | null;
  final_human_decision: ReportFinalDecisionSection;
  decision_history: ReportDecisionHistoryItem[];
  stale_warnings: string[];
  mock_verification_disclaimer?: string | null;
  audit_timeline: ReportAuditEventSummaryItem[];
}

export interface TenderSummaryBidItem {
  bid_id: string;
  bid_number: string;
  bidder_name: string;
  quoted_amount?: number | null;
  compliance_score?: number | null;
  adjusted_risk_level?: string | null;
  human_decision_status: string;
  is_shortlisted: boolean;
  critical_defects_count: number;
  open_reviews_count: number;
}

export interface TenderReportResponse {
  report_id: string;
  report_title: string;
  generated_at: string;
  generated_by: string;
  tender: ReportTenderInfo;
  total_bids_submitted: number;
  total_bids_evaluated: number;
  total_qualified: number;
  total_disqualified: number;
  total_under_review: number;
  total_not_decided: number;
  total_shortlisted: number;
  risk_distribution: Record<string, number>;
  average_compliance_score?: number | null;
  total_critical_defects: number;
  total_open_reviews: number;
  bids: TenderSummaryBidItem[];
}
