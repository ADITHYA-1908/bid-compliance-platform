/**
 * Procurement Analytics & Impact Types (Part 13)
 */

export interface ProcurementImpact {
  measured_time_reduction_percentage: number;
  avg_automated_time_ms: number;
  avg_manual_baseline_sec: number;
  total_validation_cases: number;
  dataset_version: string;
}

export interface OverviewKPIs {
  total_tenders: number;
  active_tenders: number;
  total_bids: number;
  submitted_bids: number;
  evaluated_bids: number;
  compliance_rate_percentage?: number | null;
  open_reviews_count: number;
  high_critical_risk_bids: number;
  average_risk_score?: number | null;
  poor_quality_documents_count: number;
  average_quality_score?: number | null;
  duplicate_alerts_count: number;
  procurement_impact?: ProcurementImpact | null;
}

export interface FailedRequirementSummary {
  requirement_code: string;
  title: string;
  category: string;
  fail_count: number;
}

export interface CommonFailureReason {
  reason: string;
  count: number;
}

export interface ComplianceAnalytics {
  distribution: Record<string, number>;
  total_evaluations: number;
  overall_compliance_rate?: number | null;
  mandatory_failures_count: number;
  top_failed_requirements: FailedRequirementSummary[];
  common_failure_reasons: CommonFailureReason[];
}

export interface RiskAnalytics {
  distribution: Record<string, number>;
  total_risk_evaluated_bids: number;
  average_risk_score?: number | null;
  overrides_applied_count: number;
}

export interface VerificationSourceBreakdown {
  verification_type: string;
  total: number;
  verified: number;
  failed: number;
  review_required: number;
  success_rate: number;
}

export interface VerificationAnalytics {
  status_distribution: Record<string, number>;
  total_verifications: number;
  source_breakdown: VerificationSourceBreakdown[];
}

export interface QualityDiagnostics {
  blurry_documents: number;
  blank_page_documents: number;
  low_resolution_documents: number;
}

export interface DocumentQualityAnalytics {
  distribution: Record<string, number>;
  total_documents_analyzed: number;
  average_quality_score?: number | null;
  diagnostics: QualityDiagnostics;
}

export interface DuplicateAnalytics {
  total_duplicate_alerts: number;
  match_type_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
}

export interface BulkAnalytics {
  total_jobs: number;
  status_distribution: Record<string, number>;
  total_bids_processed: number;
  job_success_rate?: number | null;
}

export interface ReviewTypeSummary {
  review_type: string;
  count: number;
}

export interface DisqualificationCategorySummary {
  category: string;
  count: number;
}

export interface HumanReviewAndDecision {
  total_reviews: number;
  review_status_distribution: Record<string, number>;
  review_types_breakdown: ReviewTypeSummary[];
  total_human_decisions: number;
  decision_status_distribution: Record<string, number>;
  disqualification_categories: DisqualificationCategorySummary[];
}

export interface TimeSeriesPoint {
  date: string;
  submitted_bids: number;
  evaluated_bids: number;
}

export interface TenderSpecificAnalytics {
  tender_id: string;
  tender_number: string;
  title: string;
  status: string;
  estimated_amount?: number | null;
  overview_kpis: OverviewKPIs;
  compliance_analytics: ComplianceAnalytics;
  risk_analytics: RiskAnalytics;
  verification_analytics: VerificationAnalytics;
  human_reviews_and_decisions: HumanReviewAndDecision;
}
