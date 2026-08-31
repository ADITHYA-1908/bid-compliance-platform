/**
 * Bid API Client Module for Part 3C, 3D & Part 3E
 * Handles Bid Creation, Draft Workspace, Document Uploads, Review, and Final Submission
 */

import { api, API_BASE_URL, getStoredToken } from "@/lib/api";

export type BidStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "UNDER_VERIFICATION"
  | "UNDER_EVALUATION"
  | "QUALIFIED"
  | "DISQUALIFIED"
  | "WITHDRAWN";

export interface BidTenderSummary {
  id: string;
  tender_number: string;
  title: string;
  description?: string | null;
  department?: string | null;
  category?: string | null;
  procurement_type?: string | null;
  estimated_value?: number | string | null;
  currency: string;
  status: string;
  publish_date?: string | null;
  submission_start_date?: string | null;
  submission_end_date?: string | null;
  organization_name?: string | null;
  organization_city?: string | null;
  organization_state?: string | null;
  active_requirements_count: number;
}

export interface BidderOrgSummary {
  id: string;
  name: string;
  trade_name?: string | null;
  pan_number?: string | null;
  gstin?: string | null;
  city?: string | null;
  state?: string | null;
}

export interface BidCreatePayload {
  quoted_amount?: number | string | null;
  currency?: string;
  technical_summary?: string | null;
  commercial_notes?: string | null;
  remarks?: string | null;
}

export interface BidUpdatePayload {
  quoted_amount?: number | string | null;
  currency?: string | null;
  technical_summary?: string | null;
  commercial_notes?: string | null;
  remarks?: string | null;
}

export interface BidListItem {
  id: string;
  bid_number: string;
  status: BidStatus | string;
  quoted_amount?: number | string | null;
  currency: string;
  tender_id: string;
  tender_number: string;
  tender_title: string;
  tender_status: string;
  department?: string | null;
  category?: string | null;
  procurement_type?: string | null;
  submission_end_date?: string | null;
  procuring_organization_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BidListResponse {
  items: BidListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface BidDetail {
  id: string;
  tender_id: string;
  bidder_organization_id: string;
  created_by_profile_id: string;
  submitted_by_profile_id?: string | null;
  bid_number: string;
  status: BidStatus | string;
  quoted_amount?: number | string | null;
  currency: string;
  technical_summary?: string | null;
  commercial_notes?: string | null;
  remarks?: string | null;
  submitted_at?: string | null;
  declaration_accepted?: boolean;
  declaration_accepted_at?: string | null;
  submission_reference?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  tender: BidTenderSummary;
  bidder_organization?: BidderOrgSummary | null;
}

export interface BidListParams {
  search?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

// =========================================================================
// Part 3D: Bid Documents Types
// =========================================================================

export interface BidDocument {
  id: string;
  bid_id: string;
  tender_requirement_id?: string | null;
  uploaded_by_profile_id: string;
  document_type: string;
  document_name: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  status: string;
  version: number;
  notes?: string | null;
  is_active: boolean;
  uploaded_at: string;
  updated_at: string;
  download_url?: string | null;
  requirement_code?: string | null;
  requirement_name?: string | null;
  is_mandatory?: boolean | null;
}

export interface BidDocumentsSummary {
  total_required: number;
  uploaded_required: number;
  missing_required: number;
  total_uploaded: number;
  is_ready_for_submission: boolean;
}

export interface BidDocumentListResponse {
  items: BidDocument[];
  summary: BidDocumentsSummary;
}

export interface BidDocumentDownloadResponse {
  document_id: string;
  filename: string;
  mime_type: string;
  download_url?: string | null;
  expires_in_seconds: number;
}

// =========================================================================
// Part 3E: Bid Submission Types
// =========================================================================

export interface BidSubmissionReadinessChecks {
  profile_complete: boolean;
  bid_details_complete: boolean;
  mandatory_documents_complete: boolean;
  tender_open: boolean;
  deadline_valid: boolean;
}


export interface BidSubmissionReadinessResponse {
  bid_id: string;
  bid_number: string;
  ready_to_submit: boolean;
  checks: BidSubmissionReadinessChecks;
  missing_required_fields: string[];
  missing_documents: string[];
  tender_title: string;
  tender_number: string;
  tender_status: string;
  submission_end_date?: string | null;
}

export interface BidSubmitPayload {
  declaration_accepted: boolean;
}

export interface BidSubmitResponse {
  id: string;
  bid_number: string;
  submission_reference: string;
  status: string;
  submitted_at: string;
  submitted_by_email: string;
  submitted_by_name: string;
  tender_id: string;
  tender_number: string;
  tender_title: string;
  bidder_organization_name: string;
  quoted_amount?: number | string | null;
  currency: string;
  message: string;
}

/**
 * Creates a new DRAFT bid participation record for an OPEN tender.
 */
export async function createBid(
  tenderId: string,
  payload?: BidCreatePayload
): Promise<BidDetail> {
  return api.post<BidDetail>(`/api/v1/bidder/tenders/${tenderId}/bids`, payload || {});
}

/**
 * Checks if the current bidder organization already has an active bid for a tender.
 */
export async function checkTenderBid(
  tenderId: string
): Promise<BidListItem | null> {
  return api.get<BidListItem | null>(`/api/v1/bidder/tenders/${tenderId}/bid`);
}

/**
 * Retrieves paginated list of bids belonging to the authenticated bidder organization.
 */
export async function getMyBids(
  params?: BidListParams
): Promise<BidListResponse> {
  return api.get<BidListResponse>("/api/v1/bidder/bids", {
    params: params as Record<string, string | number | boolean | undefined>,
  });
}

/**
 * Retrieves detailed bid workspace by bid ID.
 */
export async function getBid(bidId: string): Promise<BidDetail> {
  return api.get<BidDetail>(`/api/v1/bidder/bids/${bidId}`);
}

/**
 * Updates commercial and technical fields of a DRAFT bid.
 */
export async function updateBid(
  bidId: string,
  payload: BidUpdatePayload
): Promise<BidDetail> {
  return api.patch<BidDetail>(`/api/v1/bidder/bids/${bidId}`, payload);
}

// =========================================================================
// Part 3D Document API Functions
// =========================================================================

/**
 * Uploads a document against a draft bid.
 */
export async function uploadBidDocument(
  bidId: string,
  formData: FormData
): Promise<BidDocument> {
  return api.upload<BidDocument>(`/api/v1/bidder/bids/${bidId}/documents`, formData);
}

/**
 * Retrieves all uploaded documents and readiness summary for a bid.
 */
export async function getBidDocuments(
  bidId: string,
  includeInactive: boolean = false
): Promise<BidDocumentListResponse> {
  return api.get<BidDocumentListResponse>(`/api/v1/bidder/bids/${bidId}/documents`, {
    params: includeInactive ? { include_inactive: true } : undefined,
  });
}

/**
 * Retrieves single document details.
 */
export async function getBidDocument(
  bidId: string,
  documentId: string
): Promise<BidDocument> {
  return api.get<BidDocument>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}`);
}

/**
 * Gets a signed or secure download URL metadata for direct viewing.
 */
export async function getBidDocumentDownloadUrl(
  bidId: string,
  documentId: string
): Promise<BidDocumentDownloadResponse> {
  return api.get<BidDocumentDownloadResponse>(
    `/api/v1/bidder/bids/${bidId}/documents/${documentId}/download-url`
  );
}

/**
 * Directly downloads document file as a blob.
 */
export async function downloadBidDocumentBlob(
  bidId: string,
  documentId: string
): Promise<{ blob: Blob; filename: string }> {
  const token = getStoredToken();
  const url = `${API_BASE_URL}/api/v1/bidder/bids/${bidId}/documents/${documentId}/download`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!res.ok) {
    throw new Error(`Failed to download file (HTTP ${res.status})`);
  }

  const disposition = res.headers.get("content-disposition");
  let filename = "document.pdf";
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename=["']?([^"';]+)["']?/);
    if (match && match[1]) filename = match[1];
  }

  const blob = await res.blob();
  return { blob, filename };
}

/**
 * Replaces an existing active document with a new file.
 */
export async function replaceBidDocument(
  bidId: string,
  documentId: string,
  formData: FormData
): Promise<BidDocument> {
  return api.putUpload<BidDocument>(
    `/api/v1/bidder/bids/${bidId}/documents/${documentId}`,
    formData
  );
}

/**
 * Soft-removes an uploaded document from active bid.
 */
export async function removeBidDocument(
  bidId: string,
  documentId: string
): Promise<BidDocument> {
  return api.delete<BidDocument>(
    `/api/v1/bidder/bids/${bidId}/documents/${documentId}`
  );
}

// =========================================================================
// Part 3E Submission API Functions
// =========================================================================

/**
 * Retrieves granular submission readiness checklist and missing requirements.
 */
export async function getBidSubmissionReadiness(
  bidId: string
): Promise<BidSubmissionReadinessResponse> {
  return api.get<BidSubmissionReadinessResponse>(
    `/api/v1/bidder/bids/${bidId}/readiness`
  );
}

/**
 * Submits final bid proposal atomically and locks it from further mutation.
 */
export async function submitFinalBid(
  bidId: string,
  payload: BidSubmitPayload
): Promise<BidSubmitResponse> {
  return api.post<BidSubmitResponse>(
    `/api/v1/bidder/bids/${bidId}/submit`,
    payload
  );
}
