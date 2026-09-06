/**
 * Frontend TypeScript Types for Part 8C: Human Review & Evidence Inspection Workflow
 */

export type ReviewType =
  | "COMPLIANCE_REVIEW"
  | "VERIFICATION_REVIEW"
  | "DOCUMENT_REVIEW"
  | "IDENTITY_MISMATCH"
  | "ORGANIZATION_MISMATCH"
  | "LOW_CONFIDENCE"
  | "PENDING_SOURCE"
  | "CRITICAL_REVIEW"
  | "POTENTIAL_DOCUMENT_REUSE"
  | "DOCUMENT_REUSE_ALERT"
  | "CROSS_BIDDER_REUSE"
  | "POOR_DOCUMENT_QUALITY"
  | "EXPIRED_CERTIFICATE"
  | "BLACKLISTING_SIGNAL"
  | "UNRESOLVED_CLARIFICATION"
  | "OTHER";

export type ReviewSeverity = "LOW" | "NORMAL" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ReviewStatus =
  | "OPEN"
  | "IN_REVIEW"
  | "IN_PROGRESS"
  | "AWAITING_CLARIFICATION"
  | "RESOLVED"
  | "DISMISSED"
  | "ESCALATED"
  | "SUPERSEDED";

export type ReviewResolution =
  | "CONFIRMED"
  | "CONFIRMED_BENIGN"
  | "CONFIRMED_REUSE"
  | "REJECTED"
  | "DISMISSED"
  | "NEEDS_MORE_EVIDENCE"
  | "ESCALATED"
  | "NOT_APPLICABLE";

export interface ReviewQueueItem {
  id: string;
  tender_id: string;
  tender_number: string;
  tender_title: string;
  bid_id: string;
  bid_number: string;
  bidder_name: string;
  bidder_pan?: string | null;
  bidder_gstin?: string | null;
  requirement_code?: string | null;
  requirement_name?: string | null;
  category?: string | null;
  review_type: ReviewType;
  issue_type_display?: string | null;
  severity: ReviewSeverity;
  status: ReviewStatus;
  source_type: string;
  title: string;
  reason: string;
  is_critical: boolean;
  is_mandatory: boolean;
  claimed_by_name?: string | null;
  resolved_by_name?: string | null;
  resolution?: ReviewResolution | null;
  created_at: string;
  resolved_at?: string | null;
}

export interface ReviewQueueKPIs {
  total_open: number;
  critical_open: number;
  high_open: number;
  awaiting_clarification: number;
  in_review: number;
  resolved_today: number;
  escalated: number;
}

export interface ReviewQueueResponse {
  kpis: ReviewQueueKPIs;
  items: ReviewQueueItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ReviewNoteItem {
  id: string;
  author_id: string;
  author_name: string;
  author_email: string;
  author_role: string;
  note_text: string;
  created_at: string;
}

export interface AddReviewNoteRequest {
  note_text: string;
}

export interface ResolveReviewRequest {
  resolution: ReviewResolution;
  reason: string;
  effective_compliance_status?: string | null;
}

export interface ReviewRequirementSection {
  requirement_id?: string | null;
  code: string;
  name: string;
  category?: string | null;
  requirement_type?: string | null;
  expected_value?: any;
  operator?: string | null;
  is_mandatory: boolean;
  is_critical: boolean;
  weight?: number | null;
}

export interface ReviewActualEvidenceSection {
  claimed_value?: any;
  verified_value?: any;
  match_status?: string | null;
  extraction_confidence?: number | null;
  field_confidence?: string | null;
  compliance_status?: string | null;
  system_reason?: string | null;
}

export interface ReviewSourceDocumentSection {
  document_id?: string | null;
  document_name?: string | null;
  document_type?: string | null;
  file_size?: number | null;
  content_type?: string | null;
  uploaded_at?: string | null;
  processing_status?: string | null;
  page_number?: number | null;
  extracted_text_snippet?: string | null;
  ocr_confidence?: number | null;
  secure_download_url?: string | null;
}

export interface ReviewVerificationEvidenceSection {
  verification_record_id?: string | null;
  verification_type?: string | null;
  verification_status?: string | null;
  registry_status?: string | null;
  match_status?: string | null;
  source_type?: string | null;
  source_name?: string | null;
  source_badge_label?: string | null;
  is_mock: boolean;
  is_available: boolean;
  confidence_score?: number | null;
  evidence_payload?: Record<string, any> | null;
}

export interface ReviewComplianceEvidenceSection {
  compliance_result_id?: string | null;
  compliance_status?: string | null;
  expected_value?: any;
  actual_value?: any;
  operator?: string | null;
  reason?: string | null;
  is_mandatory: boolean;
  is_critical: boolean;
  effective_compliance_status?: string | null;
  human_resolution?: string | null;
  human_reason?: string | null;
}

export interface ReviewRiskSection {
  risk_level: string;
  risk_score?: number | null;
  top_signals: string[];
  is_critical: boolean;
}

export interface ReviewClarificationSection {
  clarification_id?: string | null;
  status?: string | null;
  status_label?: string | null;
  subject?: string | null;
  question?: string | null;
  response?: string | null;
  has_active_request: boolean;
}

export interface CrossDocumentComparisonRow {
  field_name: string;
  pan_doc_value?: string | null;
  gst_doc_value?: string | null;
  mca_doc_value?: string | null;
  other_doc_value?: string | null;
  is_match: boolean;
  discrepancy_note?: string | null;
}

export interface ReviewAICitationItem {
  citation_id: string;
  source_type: string;
  title: string;
  page?: number | null;
  snippet?: string | null;
}

export interface ReviewAIExplanationSection {
  recommendation?: string | null;
  confidence_label?: string | null;
  summary?: string | null;
  strengths: string[];
  concerns: string[];
  review_items: string[];
  grounded_citations: ReviewAICitationItem[];
  disclaimer: string;
  is_stale: boolean;
  is_available: boolean;
}

export interface ReviewDetailResponse {
  review_id: string;
  organization_id: string;
  tender_id: string;
  tender_number: string;
  tender_title: string;
  bid_id: string;
  bid_number: string;
  bidder_legal_name: string;
  trade_name?: string | null;
  bidder_pan?: string | null;
  bidder_gstin?: string | null;
  review_type: ReviewType;
  issue_type_display?: string | null;
  severity: ReviewSeverity;
  status: ReviewStatus;
  title: string;
  reason: string;
  system_finding: Record<string, any>;
  resolution?: ReviewResolution | null;
  resolution_reason?: string | null;
  effective_compliance_status?: string | null;
  claimed_by_name?: string | null;
  claimed_by_id?: string | null;
  resolved_by_name?: string | null;
  resolved_by_id?: string | null;
  resolved_at?: string | null;
  version: number;
  created_at: string;
  updated_at: string;

  requirement_section?: ReviewRequirementSection | null;
  actual_evidence_section?: ReviewActualEvidenceSection | null;
  source_document_section?: ReviewSourceDocumentSection | null;
  verification_section?: ReviewVerificationEvidenceSection | null;
  compliance_section?: ReviewComplianceEvidenceSection | null;
  risk_section?: ReviewRiskSection | null;
  clarification_section?: ReviewClarificationSection | null;
  cross_document_section: CrossDocumentComparisonRow[];
  ai_explanation_section?: ReviewAIExplanationSection | null;
  notes_history: ReviewNoteItem[];
}
