/**
 * TypeScript Interfaces for Part 9: Bulk Verification & Batch Processing
 */

export interface BulkEvaluationSummaryCounts {
  total: number;
  processed: number;
  successful: number;
  failed: number;
  review_required: number;
  critical_findings: number;
  remaining: number;
  progress_percentage: number;
}

export interface BulkEvaluationJobCreateResponse {
  job_id: string;
  tender_id: string;
  status: string;
  total_bids: number;
  message: string;
  created_at: string;
}

export interface BulkEvaluationJobStatusResponse {
  id: string;
  organization_id: string;
  tender_id: string;
  tender_number?: string | null;
  tender_title?: string | null;
  status: "QUEUED" | "RUNNING" | "COMPLETED" | "PARTIALLY_COMPLETED" | "FAILED" | "CANCELLED" | string;
  counts: BulkEvaluationSummaryCounts;
  started_by_name?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  error_summary?: Record<string, any> | null;
}

export interface BulkEvaluationJobItem {
  id: string;
  job_id: string;
  bid_id: string;
  bid_number?: string | null;
  bidder_name?: string | null;
  status: "QUEUED" | "RUNNING" | "SUCCESS" | "FAILED" | "REVIEW_REQUIRED" | "SKIPPED" | string;
  current_stage: "QUEUED" | "DOCUMENT_PROCESSING" | "VERIFICATION" | "COMPLIANCE" | "SCORING" | "RISK" | "COMPLETED" | "FAILED" | "SKIPPED" | string;
  document_processing_status: string;
  verification_status: string;
  compliance_status: string;
  score_status: string;
  risk_status: string;
  final_score?: number | null;
  risk_level?: string | null;
  review_required: boolean;
  critical_findings_count: number;
  error_code?: string | null;
  error_message?: string | null;
  is_retryable: boolean;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface BulkEvaluationJobItemsListResponse {
  items: BulkEvaluationJobItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface BulkEvaluationRetryResponse {
  job_id: string;
  retried_count: number;
  status: string;
  message: string;
}

export interface BulkEvaluationCancelResponse {
  job_id: string;
  status: string;
  message: string;
}
