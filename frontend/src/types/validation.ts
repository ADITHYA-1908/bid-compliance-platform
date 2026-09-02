/**
 * Empirical Validation and Benchmarking Types
 */

export interface ValidationRun {
  id: string;
  organization_id?: string | null;
  name: string;
  dataset_version: string;
  engine_versions?: Record<string, any> | null;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  total_cases: number;
  passed_cases: number;
  failed_cases: number;

  // Accuracies
  ocr_accuracy: number;
  classification_accuracy: number;
  field_extraction_accuracy: number;
  compliance_accuracy: number;

  // Confusion Matrix
  true_positives: number;
  true_negatives: number;
  false_positives: number;
  false_negatives: number;

  // Statistical Rates
  precision: number;
  recall: number;
  f1_score: number;
  false_positive_rate: number;
  false_negative_rate: number;

  // RAG
  rag_retrieval_accuracy: number;
  rag_citation_accuracy: number;

  // Timing
  average_processing_time_ms: number;
  average_manual_time_sec: number;
  time_reduction_percentage: number;

  summary_json?: {
    confusion_matrix?: {
      true_positives: number;
      true_negatives: number;
      false_positives: number;
      false_negatives: number;
    };
    quality_correlation?: Record<string, { count: number; avg_ocr_accuracy: number }>;
    category_breakdown?: Record<string, { total: number; accuracy: number; avg_ocr: number; avg_extraction: number }>;
    document_type_breakdown?: Record<string, { total: number; accuracy: number }>;
    load_performance?: Record<string, { bids_count: number; estimated_total_time_sec: number; success_rate: number }>;
  } | null;

  notes?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ValidationCaseResult {
  id: string;
  validation_run_id: string;
  test_case_id: string;
  title: string;
  category: string;
  document_type: string;
  quality_level: string;
  expected_result_json: Record<string, any>;
  actual_result_json: Record<string, any>;
  is_correct: boolean;
  error_type: string;
  error_reason?: string | null;
  ocr_correct: boolean;
  ocr_accuracy: number;
  classification_correct: boolean;
  extraction_correct: boolean;
  compliance_correct: boolean;
  rag_correct: boolean;
  processing_time_ms: number;
  manual_baseline_sec: number;
  details_json?: Record<string, any> | null;
  created_at: string;
}

export interface ValidationRunListResponse {
  items: ValidationRun[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ValidationCaseListResponse {
  items: ValidationCaseResult[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ValidationPPTSummary {
  slide_title: string;
  dataset_overview: Record<string, any>;
  performance_metrics: Record<string, string>;
  speed_and_efficiency_gains: Record<string, string>;
  key_takeaways: string[];
  observed_limitations: string[];
}
