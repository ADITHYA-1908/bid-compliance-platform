/**
 * Certificate Validity Monitoring Types
 * Part 14 — Certificate Validity Monitoring for BidVerify AI
 */

export enum ValidityStatus {
  VALID = "VALID",
  EXPIRING_SOON = "EXPIRING_SOON",
  EXPIRED = "EXPIRED",
  NO_EXPIRY = "NO_EXPIRY",
  UNKNOWN = "UNKNOWN",
  REVIEW_REQUIRED = "REVIEW_REQUIRED",
}

export enum ValidityDateSource {
  STRUCTURED_EXTRACTION = "STRUCTURED_EXTRACTION",
  VERIFICATION_ADAPTER = "VERIFICATION_ADAPTER",
  MANUAL_OVERRIDE = "MANUAL_OVERRIDE",
}

export interface DocumentValidityItem {
  id: string;
  document_id: string;
  bid_id?: string | null;
  organization_id: string;
  document_name?: string | null;
  document_type: string;
  issue_date?: string | null;
  expiry_date?: string | null;
  validity_status: ValidityStatus | string;
  days_until_expiry?: number | null;
  date_source: string;
  source_page?: number | null;
  source_text?: string | null;
  confidence: number;
  is_current: boolean;
  submission_validity_status?: string | null;
  last_checked_at: string;
  next_check_at?: string | null;
  metadata_json: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CertificateValidityStats {
  total_monitored: number;
  valid_count: number;
  expiring_soon_count: number;
  expired_count: number;
  no_expiry_count: number;
  review_required_count: number;
  unknown_count: number;
}

export interface BidderCertificateListResponse {
  items: DocumentValidityItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  stats: CertificateValidityStats;
}

export interface ProcurementCertificateListResponse {
  items: DocumentValidityItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CertificateValidityRecheckResponse {
  record: DocumentValidityItem;
  message: string;
}

export interface PeriodicValidityCheckResponse {
  total_checked: number;
  status_transitions: number;
  status_breakdown: Record<string, number>;
  reference_date: string;
}
