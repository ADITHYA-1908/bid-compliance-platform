/**
 * Part 16: Clarification Request Workflow TypeScript Interfaces
 * Defines types for formal clarification exchanges, responses, replacement documents,
 * audit threads, status filters, and KPIs.
 */

export type ClarificationStatus =
  | "DRAFT"
  | "SENT"
  | "VIEWED"
  | "RESPONDED"
  | "UNDER_REVIEW"
  | "RESOLVED"
  | "CLOSED"
  | "EXPIRED"
  | "CANCELLED";

export type ClarificationType =
  | "MISSING_DOCUMENT"
  | "UNCLEAR_DOCUMENT"
  | "LOW_OCR_CONFIDENCE"
  | "VERIFICATION_MISMATCH"
  | "COMPLIANCE_REVIEW"
  | "DUPLICATE_REUSE_EXPLANATION"
  | "CERTIFICATE_VALIDITY"
  | "CONFLICTING_INFORMATION"
  | "ADDITIONAL_EVIDENCE"
  | "OTHER";

export type ClarificationPriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";

export interface ClarificationResponseDTO {
  id: string;
  clarification_request_id: string;
  responded_by_profile_id: string;
  responded_by_name?: string | null;
  response_text: string;
  attached_document_id?: string | null;
  attached_document_name?: string | null;
  is_replacement_document: boolean;
  replaced_document_id?: string | null;
  replaced_document_name?: string | null;
  metadata_json?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface ClarificationRequestListItemResponse {
  id: string;
  tender_id: string;
  tender_number: string;
  tender_title: string;
  bid_id: string;
  bid_number: string;
  bidder_organization_name: string;
  tender_organization_name: string;
  created_by_profile_id: string;
  created_by_name?: string | null;
  subject: string;
  clarification_type: ClarificationType;
  priority: ClarificationPriority;
  status: ClarificationStatus;
  due_date?: string | null;
  sent_at?: string | null;
  viewed_at?: string | null;
  responded_at?: string | null;
  resolved_at?: string | null;
  responses_count: number;
  is_overdue: boolean;
  related_requirement_code?: string | null;
  related_document_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClarificationRequestDetailResponse {
  id: string;
  tender_id: string;
  tender_number: string;
  tender_title: string;
  bid_id: string;
  bid_number: string;
  tender_organization_id: string;
  tender_organization_name: string;
  bidder_organization_id: string;
  bidder_organization_name: string;
  created_by_profile_id: string;
  created_by_name?: string | null;
  assigned_bidder_profile_id?: string | null;
  assigned_bidder_name?: string | null;
  subject: string;
  message: string;
  clarification_type: ClarificationType;
  priority: ClarificationPriority;
  status: ClarificationStatus;
  due_date?: string | null;
  sent_at?: string | null;
  viewed_at?: string | null;
  responded_at?: string | null;
  resolved_at?: string | null;
  resolved_by_profile_id?: string | null;
  resolved_by_name?: string | null;
  resolution_note?: string | null;
  related_document_id?: string | null;
  related_document_name?: string | null;
  related_document_type?: string | null;
  related_requirement_id?: string | null;
  related_requirement_code?: string | null;
  related_rule_version_id?: string | null;
  related_rule_version_number?: number | null;
  related_verification_record_id?: string | null;
  related_compliance_result_id?: string | null;
  related_review_item_id?: string | null;
  related_duplicate_match_id?: string | null;
  responses: ClarificationResponseDTO[];
  is_overdue: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClarificationRequestListResponse {
  items: ClarificationRequestListItemResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ClarificationSummaryResponse {
  total: number;
  open: number;
  draft: number;
  sent: number;
  viewed: number;
  responded: number;
  under_review: number;
  resolved: number;
  closed: number;
  overdue: number;
  urgent_priority: number;
}

export interface ClarificationAnalyticsResponse {
  total_clarifications: number;
  open_clarifications: number;
  resolved_clarifications: number;
  overdue_clarifications: number;
  avg_response_time_hours?: number | null;
  avg_resolution_time_hours?: number | null;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  by_priority: Record<string, number>;
}

export interface ClarificationRequestCreate {
  subject: string;
  message: string;
  clarification_type?: ClarificationType;
  priority?: ClarificationPriority;
  due_date?: string | null;
  send_immediately?: boolean;
  related_document_id?: string | null;
  related_requirement_id?: string | null;
  related_verification_record_id?: string | null;
  related_compliance_result_id?: string | null;
  related_review_item_id?: string | null;
  related_duplicate_match_id?: string | null;
}

export interface ClarificationResponseCreate {
  response_text: string;
  attached_document_id?: string | null;
  is_replacement_document?: boolean;
  replaced_document_id?: string | null;
}

export interface ClarificationResolveRequest {
  resolution_note: string;
  trigger_reevaluation?: boolean;
}
