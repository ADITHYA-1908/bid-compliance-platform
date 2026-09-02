/**
 * Notification Center Types
 * Part 12 — In-App Notifications for BidVerify AI
 */

export type NotificationSeverity = "INFO" | "SUCCESS" | "WARNING" | "CRITICAL";

export type NotificationType =
  | "BID_SUBMITTED"
  | "DOCUMENT_MISSING"
  | "DOCUMENT_QUALITY_REVIEW_REQUIRED"
  | "DOCUMENT_PROCESSING_COMPLETED"
  | "VERIFICATION_COMPLETED"
  | "VERIFICATION_REVIEW_REQUIRED"
  | "DUPLICATE_DOCUMENT_ALERT"
  | "COMPLIANCE_REVIEW_REQUIRED"
  | "CRITICAL_RISK_DETECTED"
  | "CLARIFICATION_REQUESTED"
  | "CLARIFICATION_RECEIVED"
  | "CERTIFICATE_EXPIRING"
  | "TENDER_DEADLINE_APPROACHING"
  | "BULK_EVALUATION_COMPLETED"
  | "BULK_EVALUATION_PARTIAL"
  | "FINAL_DECISION_RECORDED";

export interface NotificationItem {
  id: string;
  recipient_profile_id: string;
  organization_id: string;
  tender_id?: string | null;
  bid_id?: string | null;
  document_id?: string | null;
  notification_type: NotificationType | string;
  severity: NotificationSeverity;
  title: string;
  message: string;
  is_read: boolean;
  read_at?: string | null;
  action_url?: string | null;
  dedupe_key?: string | null;
  metadata_json?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface NotificationMarkReadResponse {
  success: boolean;
  marked_count: number;
  unread_count: number;
  message: string;
}

export interface NotificationFilterParams {
  page?: number;
  page_size?: number;
  is_read?: boolean;
  severity?: string;
  notification_type?: string;
  tender_id?: string;
  bid_id?: string;
  search?: string;
}
