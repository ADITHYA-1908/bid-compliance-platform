/**
 * Centralized API Client for BidVerify AI
 * Provides type-safe request methods, error extraction, token attachment,
 * and unified backend integration.
 */

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization?: string | null;
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface SignupPayload {
  full_name: string;
  email: string;
  password: string;
  organization_name: string;
  organization_type?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RoleTestResponse {
  message: string;
  role: string;
  user_email: string;
  organization: string | null;
}

export interface HealthResponse {
  status?: string;
  database?: string;
  message?: string;
}

export interface RoleItem {
  id: string;
  name: string;
  description: string;
}

export interface TenderRequirement {
  id: string;
  tender_id: string;
  code: string;
  name: string;
  description?: string | null;
  category: string;
  requirement_type: string;
  operator: string;
  expected_value?: any;
  is_mandatory: boolean;
  weight?: number | null;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Tender {
  id: string;
  tender_number: string;
  title: string;
  description?: string | null;
  department?: string | null;
  category?: string | null;
  procurement_type?: string | null;
  estimated_value?: number | string | null;
  currency: string;
  publish_date?: string | null;
  submission_start_date?: string | null;
  submission_end_date?: string | null;
  evaluation_start_date?: string | null;
  published_at?: string | null;
  opened_at?: string | null;
  closed_at?: string | null;
  evaluation_started_at?: string | null;
  awarded_at?: string | null;
  archived_at?: string | null;
  organization_id: string;
  created_by_profile_id: string;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  requirements?: TenderRequirement[];
  allowed_transitions?: string[];
}

export interface TenderCreatePayload {
  tender_number: string;
  title: string;
  description?: string | null;
  department?: string | null;
  category?: string | null;
  procurement_type?: string | null;
  estimated_value?: number | string | null;
  currency?: string;
  publish_date?: string | null;
  submission_start_date?: string | null;
  submission_end_date?: string | null;
  evaluation_start_date?: string | null;
}

export interface TenderUpdatePayload {
  title?: string;
  description?: string | null;
  department?: string | null;
  category?: string | null;
  procurement_type?: string | null;
  estimated_value?: number | string | null;
  currency?: string;
  publish_date?: string | null;
  submission_start_date?: string | null;
  submission_end_date?: string | null;
  evaluation_start_date?: string | null;
}

export interface TenderListResponse {
  items: Tender[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface TenderListParams {
  page?: number;
  page_size?: number;
  status?: string;
  search?: string;
  include_archived?: boolean;
}

export interface TenderRequirementCreatePayload {
  code: string;
  name: string;
  description?: string | null;
  category?: string;
  requirement_type?: string;
  operator?: string;
  expected_value?: any;
  is_mandatory?: boolean;
  weight?: number;
  display_order?: number;
}

export interface TenderRequirementUpdatePayload {
  code?: string;
  name?: string;
  description?: string | null;
  category?: string;
  requirement_type?: string;
  operator?: string;
  expected_value?: any;
  is_mandatory?: boolean;
  weight?: number;
  display_order?: number;
  is_active?: boolean;
}

export const TOKEN_STORAGE_KEY = "bidverify_auth_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  }
}

export function clearStoredToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export class ApiError extends Error {
  status: number;
  detail?: any;
  isNetworkError: boolean;

  constructor(message: string, status: number, detail?: any, isNetworkError: boolean = false) {
    super(message);
    this.status = status;
    this.detail = detail;
    this.isNetworkError = isNetworkError;
    this.name = "ApiError";
  }
}

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

if (typeof window !== "undefined" && !process.env.NEXT_PUBLIC_API_URL) {
  console.warn(
    "[BidVerify API] NEXT_PUBLIC_API_URL is not explicitly set in environment. Using default http://127.0.0.1:8000"
  );
}

interface RequestOptions extends RequestInit {
  token?: string | null;
  params?: Record<string, string | number | boolean | undefined>;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  let url = `${API_BASE_URL}${endpoint}`;

  if (options.params) {
    const searchParams = new URLSearchParams();
    Object.entries(options.params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        searchParams.append(key, String(val));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString;
    }
  }

  const token = options.token !== undefined ? options.token : getStoredToken();

  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }


  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = `HTTP Error ${response.status}`;
      let detailData: any = null;

      try {
        detailData = await response.json();
        if (detailData?.detail) {
          if (typeof detailData.detail === "string") {
            errorMessage = detailData.detail;
          } else if (Array.isArray(detailData.detail)) {
            errorMessage = detailData.detail
              .map((d: any) => d.msg || JSON.stringify(d))
              .join(", ");
          } else {
            errorMessage = JSON.stringify(detailData.detail);
          }
        }
      } catch {
        // Non-JSON error body
      }

      // Handle 401 Unauthorized centralized cleanup and safe redirect
      if (response.status === 401) {
        clearStoredToken();
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("bidverify:unauthorized"));
          const currentPath = window.location.pathname;
          if (
            !currentPath.startsWith("/login") &&
            !currentPath.startsWith("/signup") &&
            currentPath !== "/"
          ) {
            window.location.href = "/login";
          }
        }
      }

      throw new ApiError(errorMessage, response.status, detailData, false);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    // Network / offline error
    throw new ApiError(
      "Unable to connect to the BidVerify API. Please ensure the backend server is running.",
      0,
      null,
      true
    );
  }
}

export const api = {
  // Generic HTTP helpers
  get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return apiRequest<T>(endpoint, { ...options, method: "GET" });
  },

  post<T>(endpoint: string, body?: any, options?: RequestOptions): Promise<T> {
    return apiRequest<T>(endpoint, {
      ...options,
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },

  put<T>(endpoint: string, body?: any, options?: RequestOptions): Promise<T> {
    return apiRequest<T>(endpoint, {
      ...options,
      method: "PUT",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },

  patch<T>(endpoint: string, body?: any, options?: RequestOptions): Promise<T> {
    return apiRequest<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },

  delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return apiRequest<T>(endpoint, { ...options, method: "DELETE" });
  },

  upload<T>(endpoint: string, formData: FormData, options?: RequestOptions): Promise<T> {
    return apiRequest<T>(endpoint, {
      ...options,
      method: "POST",
      body: formData,
    });
  },

  putUpload<T>(endpoint: string, formData: FormData, options?: RequestOptions): Promise<T> {
    return apiRequest<T>(endpoint, {
      ...options,
      method: "PUT",
      body: formData,
    });
  },


  // Authentication
  async signup(payload: SignupPayload): Promise<AuthResponse> {
    return api.post<AuthResponse>("/api/v1/auth/signup", payload);
  },

  async login(payload: LoginPayload): Promise<AuthResponse> {
    return api.post<AuthResponse>("/api/v1/auth/login", payload);
  },

  async getCurrentUser(token?: string): Promise<User> {
    return api.get<User>("/api/v1/auth/me", { token });
  },

  // Health checks
  async checkHealth(): Promise<HealthResponse> {
    return api.get<HealthResponse>("/health");
  },

  async checkDatabaseHealth(): Promise<HealthResponse> {
    return api.get<HealthResponse>("/health/database");
  },

  // Roles & RBAC
  async getRoles(): Promise<RoleItem[]> {
    return api.get<RoleItem[]>("/api/v1/roles");
  },

  async testBidderRole(token?: string): Promise<RoleTestResponse> {
    return api.get<RoleTestResponse>("/api/v1/bidder/test", { token });
  },

  async testProcurementRole(token?: string): Promise<RoleTestResponse> {
    return api.get<RoleTestResponse>("/api/v1/procurement/test", { token });
  },

  async testAdminRole(token?: string): Promise<RoleTestResponse> {
    return api.get<RoleTestResponse>("/api/v1/admin/test", { token });
  },

  // Tender Management (Part 2B / 2C)
  async getTenders(params?: TenderListParams): Promise<TenderListResponse> {
    return api.get<TenderListResponse>("/api/v1/tenders", {
      params: params as Record<string, string | number | boolean | undefined>,
    });
  },

  async getTender(id: string): Promise<Tender> {
    return api.get<Tender>(`/api/v1/tenders/${id}`);
  },

  async createTender(payload: TenderCreatePayload): Promise<Tender> {
    return api.post<Tender>("/api/v1/tenders", payload);
  },

  async updateTender(id: string, payload: TenderUpdatePayload): Promise<Tender> {
    return api.patch<Tender>(`/api/v1/tenders/${id}`, payload);
  },

  async archiveTender(id: string): Promise<Tender> {
    return api.delete<Tender>(`/api/v1/tenders/${id}`);
  },

  async transitionTenderStatus(
    id: string,
    targetStatus: string,
    remarks?: string
  ): Promise<Tender> {
    return api.post<Tender>(`/api/v1/tenders/${id}/transition`, {
      target_status: targetStatus,
      remarks,
    });
  },

  // Tender Requirements / Eligibility Rules (Part 2D)
  async getTenderRequirements(tenderId: string, includeInactive: boolean = false): Promise<TenderRequirement[]> {
    return api.get<TenderRequirement[]>(`/api/v1/tenders/${tenderId}/requirements`, {
      params: includeInactive ? { include_inactive: true } : undefined,
    });
  },

  async createTenderRequirement(tenderId: string, payload: TenderRequirementCreatePayload): Promise<TenderRequirement> {
    return api.post<TenderRequirement>(`/api/v1/tenders/${tenderId}/requirements`, payload);
  },

  async updateTenderRequirement(
    tenderId: string,
    requirementId: string,
    payload: TenderRequirementUpdatePayload
  ): Promise<TenderRequirement> {
    return api.patch<TenderRequirement>(`/api/v1/tenders/${tenderId}/requirements/${requirementId}`, payload);
  },

  async disableTenderRequirement(tenderId: string, requirementId: string): Promise<TenderRequirement> {
    return api.delete<TenderRequirement>(`/api/v1/tenders/${tenderId}/requirements/${requirementId}`);
  },

  // Bidder Profile & Organization Setup (Part 3A)
  async getBidderProfile(token?: string): Promise<BidderProfileResponse> {
    return api.get<BidderProfileResponse>("/api/v1/bidder/profile", { token });
  },

  async updateBidderProfile(payload: BidderProfileUpdatePayload): Promise<BidderProfileResponse> {
    return api.patch<BidderProfileResponse>("/api/v1/bidder/profile", payload);
  },

  async getBidderOrganization(token?: string): Promise<BidderOrganizationResponse> {
    return api.get<BidderOrganizationResponse>("/api/v1/bidder/organization", { token });
  },

  async updateBidderOrganization(payload: BidderOrganizationUpdatePayload): Promise<BidderOrganizationResponse> {
    return api.patch<BidderOrganizationResponse>("/api/v1/bidder/organization", payload);
  },

  // Bidder Tender Discovery (Part 3B)
  async getAvailableTenders(params?: BidderTenderListParams): Promise<BidderTenderListResponse> {
    return api.get<BidderTenderListResponse>("/api/v1/bidder/tenders", {
      params: params as Record<string, string | number | boolean | undefined>,
    });
  },

  async getBidderTender(id: string): Promise<BidderTenderDetail> {
    return api.get<BidderTenderDetail>(`/api/v1/bidder/tenders/${id}`);
  },

  // Bid Creation & Tender Participation (Part 3C)
  async createBid(tenderId: string, payload?: BidCreatePayload): Promise<BidDetail> {
    return api.post<BidDetail>(`/api/v1/bidder/tenders/${tenderId}/bids`, payload || {});
  },

  async checkTenderBid(tenderId: string): Promise<BidListItem | null> {
    return api.get<BidListItem | null>(`/api/v1/bidder/tenders/${tenderId}/bid`);
  },

  async getMyBids(params?: BidListParams): Promise<BidListResponse> {
    return api.get<BidListResponse>("/api/v1/bidder/bids", {
      params: params as Record<string, string | number | boolean | undefined>,
    });
  },

  async getBid(bidId: string): Promise<BidDetail> {
    return api.get<BidDetail>(`/api/v1/bidder/bids/${bidId}`);
  },

  async updateBid(bidId: string, payload: BidUpdatePayload): Promise<BidDetail> {
    return api.patch<BidDetail>(`/api/v1/bidder/bids/${bidId}`, payload);
  },

  // Bid Document Upload & Management (Part 3D)
  async uploadBidDocument(bidId: string, formData: FormData): Promise<BidDocument> {
    return api.upload<BidDocument>(`/api/v1/bidder/bids/${bidId}/documents`, formData);
  },

  async getBidDocuments(bidId: string, includeInactive: boolean = false): Promise<BidDocumentListResponse> {
    return api.get<BidDocumentListResponse>(`/api/v1/bidder/bids/${bidId}/documents`, {
      params: includeInactive ? { include_inactive: true } : undefined,
    });
  },

  async getBidDocument(bidId: string, documentId: string): Promise<BidDocument> {
    return api.get<BidDocument>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}`);
  },

  async getBidDocumentDownloadUrl(bidId: string, documentId: string): Promise<BidDocumentDownloadResponse> {
    return api.get<BidDocumentDownloadResponse>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}/download-url`);
  },

  async replaceBidDocument(bidId: string, documentId: string, formData: FormData): Promise<BidDocument> {
    return api.putUpload<BidDocument>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}`, formData);
  },

  async removeBidDocument(bidId: string, documentId: string): Promise<BidDocument> {
    return api.delete<BidDocument>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}`);
  },

  // Bid Review & Final Submission (Part 3E)
  async getBidSubmissionReadiness(bidId: string): Promise<BidSubmissionReadinessResponse> {
    return api.get<BidSubmissionReadinessResponse>(`/api/v1/bidder/bids/${bidId}/readiness`);
  },

  async submitFinalBid(bidId: string, payload: BidSubmitPayload): Promise<BidSubmitResponse> {
    return api.post<BidSubmitResponse>(`/api/v1/bidder/bids/${bidId}/submit`, payload);
  },

  // Document Ingestion & Processing Foundation (Part 4A)
  async getDocumentProcessing(bidId: string, documentId: string): Promise<DocumentProcessing> {
    return api.get<DocumentProcessing>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}/processing`);
  },

  async processDocument(bidId: string, documentId: string): Promise<DocumentProcessTriggerResponse> {
    return api.post<DocumentProcessTriggerResponse>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}/process`);
  },

  async retryDocumentProcessing(bidId: string, documentId: string): Promise<DocumentProcessTriggerResponse> {
    return api.post<DocumentProcessTriggerResponse>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}/retry`);
  },

  async getDocumentExtractedText(bidId: string, documentId: string): Promise<DocumentExtractedTextResponse> {
    return api.get<DocumentExtractedTextResponse>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}/extracted-text`);
  },

  async getDocumentClassification(bidId: string, documentId: string): Promise<DocumentClassificationResponse> {
    return api.get<DocumentClassificationResponse>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}/classification`);
  },

  async getDocumentExtractedData(bidId: string, documentId: string): Promise<DocumentExtractedDataResponse> {
    return api.get<DocumentExtractedDataResponse>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}/extracted-data`);
  },

  // Verification Engine Foundation (Part 5A)
  async verifyDocumentClaims(bidId: string, documentId: string): Promise<VerificationTriggerResponse> {
    return api.post<VerificationTriggerResponse>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}/verify`);
  },

  async getDocumentVerifications(bidId: string, documentId: string): Promise<DocumentVerificationListResponse> {
    return api.get<DocumentVerificationListResponse>(`/api/v1/bidder/bids/${bidId}/documents/${documentId}/verifications`);
  },

  async getBidVerifications(bidId: string): Promise<BidVerificationListResponse> {
    return api.get<BidVerificationListResponse>(`/api/v1/bidder/bids/${bidId}/verifications`);
  },

  async retryVerification(bidId: string, verificationId: string): Promise<VerificationRetryResponse> {
    return api.post<VerificationRetryResponse>(`/api/v1/bidder/bids/${bidId}/verifications/${verificationId}/retry`);
  },
};

export type DocumentProcessingStatus =
  | "QUEUED"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "NEEDS_REVIEW";

export type DocumentProcessingStage =
  | "INGESTION"
  | "TEXT_EXTRACTION"
  | "OCR"
  | "CLASSIFICATION"
  | "STRUCTURED_EXTRACTION"
  | "COMPLETED";

export type ExtractionMethod = "NONE" | "DIGITAL_PDF" | "OCR" | "HYBRID";

export interface DocumentProcessing {
  id: string;
  bid_document_id: string;
  processing_status: DocumentProcessingStatus | string;
  processing_stage: DocumentProcessingStage | string;
  extraction_method: ExtractionMethod | string;
  page_count?: number | null;
  detected_document_type?: string | null;
  classification_confidence?: number | null;
  classification_confidence_level?: string | null;
  classification_method?: string | null;
  classification_reason?: string | null;
  classification_requires_review?: boolean;
  extracted_data?: Record<string, any> | null;
  extraction_confidence?: number | null;
  extraction_requires_review?: boolean;
  structured_extraction_method?: string | null;
  processing_started_at?: string | null;
  processing_completed_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentProcessTriggerResponse {
  message: string;
  processing: DocumentProcessing;
}

export interface ExtractedFieldItem {
  value: any;
  confidence: number;
  evidence: string;
  page: number;
  is_conflict?: boolean;
  conflict_values?: any[];
}

export interface DocumentExtractedDataResponse {
  document_id: string;
  bid_id: string;
  document_type: string;
  fields: Record<string, ExtractedFieldItem>;
  extraction_confidence: number;
  confidence_level: "HIGH" | "MEDIUM" | "LOW" | string;
  extraction_method: string;
  requires_review: boolean;
  review_reasons: string[];
}

export interface DocumentExtractedTextResponse {
  document_id: string;
  bid_id: string;
  processing_status: string;
  processing_stage: string;
  extraction_method: string;
  page_count?: number | null;
  character_count?: number | null;
  raw_text?: string | null;
  normalized_text?: string | null;
  is_ocr_required: boolean;
  quality_label?: string | null;
  detected_document_type?: string | null;
  classification_confidence?: number | null;
  classification_confidence_level?: string | null;
  classification_reason?: string | null;
  classification_requires_review?: boolean;
  extracted_data?: Record<string, any> | null;
  extraction_confidence?: number | null;
  extraction_requires_review?: boolean;
}

export interface DocumentClassificationResponse {
  document_id: string;
  bid_id: string;
  processing_status: string;
  processing_stage: string;
  detected_document_type: string;
  expected_document_type?: string | null;
  classification_confidence: number;
  confidence_level: string;
  classification_method: string;
  classification_reason: string;
  classification_requires_review: boolean;
}

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
  processing?: DocumentProcessing | null;
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

export interface BidderOrgPublicSummary {
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
  bidder_organization?: BidderOrgPublicSummary | null;
}


export interface BidListParams {
  search?: string;
  status?: string;
  page?: number;
  page_size?: number;
}


export interface ProfileCompletionInfo {
  completion_percentage: number;
  is_complete: boolean;
  missing_required_fields: string[];
  completed_fields_count: number;
  total_required_fields: number;
}

export interface BidderOrganizationSummary {
  id: string;
  name: string;
  trade_name?: string | null;
  organization_type?: string | null;
  business_category?: string | null;
  city?: string | null;
  state?: string | null;
  pan_number?: string | null;
  gstin?: string | null;
  udyam_number?: string | null;
}

export interface BidderOrganizationDetails {
  id: string;
  name: string;
  trade_name?: string | null;
  organization_type?: string | null;
  business_category?: string | null;
  year_established?: number | null;
  registration_number?: string | null;
  registered_address?: string | null;
  city?: string | null;
  state?: string | null;
  pincode?: string | null;
  country?: string | null;
  official_email?: string | null;
  official_phone?: string | null;
  website?: string | null;
  pan_number?: string | null;
  gstin?: string | null;
  udyam_number?: string | null;
  cin_llpin?: string | null;
  startup_india_number?: string | null;
  nsic_number?: string | null;
  epfo_code?: string | null;
  esic_code?: string | null;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface BidderProfileDetails {
  id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  designation?: string | null;
  role: string;
  is_active: boolean;
  organization?: BidderOrganizationSummary | null;
}

export interface BidderProfileResponse {
  profile: BidderProfileDetails;
  completion: ProfileCompletionInfo;
}

export interface BidderOrganizationResponse {
  organization: BidderOrganizationDetails;
  completion: ProfileCompletionInfo;
}

export interface BidderProfileUpdatePayload {
  full_name?: string;
  phone?: string;
  designation?: string;
}

export interface BidderOrganizationUpdatePayload {
  name?: string;
  trade_name?: string;
  organization_type?: string;
  business_category?: string;
  year_established?: number;
  registered_address?: string;
  city?: string;
  state?: string;
  pincode?: string;
  country?: string;
  official_email?: string;
  official_phone?: string;
  website?: string;
  pan_number?: string;
  gstin?: string;
  udyam_number?: string;
  cin_llpin?: string;
  startup_india_number?: string;
  nsic_number?: string;
  epfo_code?: string;
  esic_code?: string;
}

export interface BidderTenderListParams {
  search?: string;
  category?: string;
  procurement_type?: string;
  status?: string;
  sort_by?: string;
  page?: number;
  page_size?: number;
}

export interface BidderOrganizationPublicSummary {
  id: string;
  name: string;
  organization_type?: string | null;
  city?: string | null;
  state?: string | null;
}

export interface BidderTenderRequirementSummary {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  category: string;
  requirement_type: string;
  operator: string;
  expected_value?: any;
  condition_text: string;
  is_mandatory: boolean;
  display_order: number;
}

export interface BidderTenderSummary {
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
  updated_at?: string | null;
}

export interface BidderTenderDetail {
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
  evaluation_start_date?: string | null;
  published_at?: string | null;
  opened_at?: string | null;
  organization: BidderOrganizationPublicSummary;
  requirements: BidderTenderRequirementSummary[];
  updated_at?: string | null;
}

// =============================================================================
// Part 5A: Verification Engine Types
// =============================================================================

export type VerificationType =
  | "GST"
  | "PAN"
  | "UDYAM"
  | "MCA"
  | "STARTUP_INDIA"
  | "NSIC"
  | "EPFO"
  | "ESIC"
  | "OEM_AUTHORIZATION"
  | "LOCAL_CONTENT"
  | "BLACKLISTING"
  | "DEBARMENT"
  | "CROSS_DOCUMENT"
  | "OTHER";

export type VerificationStatus =
  | "PENDING"
  | "IN_PROGRESS"
  | "VERIFIED"
  | "NOT_VERIFIED"
  | "NEEDS_REVIEW"
  | "UNAVAILABLE"
  | "FAILED";

export type VerificationSourceType =
  | "MOCK"
  | "SANDBOX"
  | "OFFICIAL_API"
  | "THIRD_PARTY"
  | "MANUAL"
  | "INTERNAL";

export type VerificationMatchStatus =
  | "MATCH"
  | "MISMATCH"
  | "PARTIAL_MATCH"
  | "NOT_APPLICABLE"
  | "UNKNOWN";

export interface VerificationEvidence {
  field?: string;
  claimed_value?: any;
  source?: string;
  matched?: boolean;
  details?: string;
  [key: string]: any;
}

export interface VerificationRecord {
  id: string;
  bid_id: string;
  bid_document_id?: string | null;
  document_processing_id?: string | null;
  verification_type: VerificationType | string;
  verification_status: VerificationStatus | string;
  source_name: string;
  source_type: VerificationSourceType | string;
  claim_source: string;
  claimed_value: string;
  verified_value?: string | null;
  match_status: VerificationMatchStatus | string;
  confidence: number;
  evidence?: VerificationEvidence | null;
  error_code?: string | null;
  error_message?: string | null;
  attempt_number: number;
  trigger_source: string;
  verification_started_at?: string | null;
  verification_completed_at?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface VerificationSummaryItem {
  id: string;
  verification_type: VerificationType | string;
  verification_status: VerificationStatus | string;
  source_name: string;
  source_type: VerificationSourceType | string;
  claimed_value: string;
  verified_value?: string | null;
  match_status: VerificationMatchStatus | string;
  confidence: number;
  error_code?: string | null;
  error_message?: string | null;
  attempt_number: number;
  is_retryable: boolean;
  evidence?: VerificationEvidence | Record<string, any> | null;
  claim_payload?: Record<string, any> | null;
  response_payload?: Record<string, any> | null;
  match_summary?: Record<string, string> | null;
  verification_completed_at?: string | null;
}

export interface DocumentVerificationListResponse {
  bid_id: string;
  bid_document_id: string;
  document_name: string;
  detected_document_type?: string | null;
  total_verifications: number;
  verifications: VerificationSummaryItem[];
}

export interface BidVerificationListResponse {
  bid_id: string;
  bid_number: string;
  total_verifications: number;
  verified_count: number;
  not_verified_count: number;
  needs_review_count: number;
  unavailable_count: number;
  failed_count: number;
  pending_count: number;
  verifications: VerificationSummaryItem[];
}

export interface VerificationTriggerResponse {
  message: string;
  bid_id: string;
  bid_document_id: string;
  created_count: number;
  results: VerificationSummaryItem[];
}

export interface VerificationRetryResponse {
  message: string;
  verification: VerificationRecord;
}

export interface BidderTenderListResponse {
  items: BidderTenderSummary[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}



