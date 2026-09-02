/**
 * Clarification Request Workflow API Client
 * Part 16 — Clarification Request Workflow for BidVerify AI
 * Provides full client endpoints for Procurement Officers and Bidders.
 */

import { api } from "@/lib/api";
import {
  ClarificationAnalyticsResponse,
  ClarificationRequestCreate,
  ClarificationRequestDetailResponse,
  ClarificationRequestListResponse,
  ClarificationResolveRequest,
  ClarificationResponseCreate,
  ClarificationResponseDTO,
  ClarificationSummaryResponse,
} from "@/types/clarification";

export interface ListClarificationParams {
  tender_id?: string;
  bid_id?: string;
  status_filter?: string;
  priority_filter?: string;
  type_filter?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export const procurementClarificationsApi = {
  /**
   * Create a new clarification request for a specific Bid.
   */
  async createClarification(
    tenderId: string,
    bidId: string,
    payload: ClarificationRequestCreate,
    token?: string
  ): Promise<ClarificationRequestDetailResponse> {
    return api.post<ClarificationRequestDetailResponse>(
      `/api/v1/procurement/tenders/${tenderId}/bids/${bidId}/clarifications`,
      payload,
      { token }
    );
  },

  /**
   * List clarification requests scoped to the Procurement Officer's organization.
   */
  async listClarifications(
    params?: ListClarificationParams,
    token?: string
  ): Promise<ClarificationRequestListResponse> {
    return api.get<ClarificationRequestListResponse>(
      "/api/v1/procurement/clarifications",
      { params: params as Record<string, any>, token }
    );
  },

  /**
   * Get KPI summary counts for procurement dashboard badges.
   */
  async getSummary(token?: string): Promise<ClarificationSummaryResponse> {
    return api.get<ClarificationSummaryResponse>(
      "/api/v1/procurement/clarifications/summary",
      { token }
    );
  },

  /**
   * Get analytics & resolution telemetry.
   */
  async getAnalytics(token?: string): Promise<ClarificationAnalyticsResponse> {
    return api.get<ClarificationAnalyticsResponse>(
      "/api/v1/procurement/clarifications/analytics",
      { token }
    );
  },

  /**
   * Retrieve full thread context and responses for a single clarification.
   */
  async getClarification(
    clarificationId: string,
    token?: string
  ): Promise<ClarificationRequestDetailResponse> {
    return api.get<ClarificationRequestDetailResponse>(
      `/api/v1/procurement/clarifications/${clarificationId}`,
      { token }
    );
  },

  /**
   * Send a DRAFT clarification to the Bidder.
   */
  async sendClarification(
    clarificationId: string,
    token?: string
  ): Promise<ClarificationRequestDetailResponse> {
    return api.post<ClarificationRequestDetailResponse>(
      `/api/v1/procurement/clarifications/${clarificationId}/send`,
      {},
      { token }
    );
  },

  /**
   * Mark a clarification as UNDER_REVIEW while evaluating bidder response.
   */
  async markUnderReview(
    clarificationId: string,
    token?: string
  ): Promise<ClarificationRequestDetailResponse> {
    return api.post<ClarificationRequestDetailResponse>(
      `/api/v1/procurement/clarifications/${clarificationId}/review`,
      {},
      { token }
    );
  },

  /**
   * Resolve a clarification request with formal auditable notes.
   */
  async resolveClarification(
    clarificationId: string,
    payload: ClarificationResolveRequest,
    token?: string
  ): Promise<ClarificationRequestDetailResponse> {
    return api.post<ClarificationRequestDetailResponse>(
      `/api/v1/procurement/clarifications/${clarificationId}/resolve`,
      payload,
      { token }
    );
  },

  /**
   * Cancel an open clarification request.
   */
  async cancelClarification(
    clarificationId: string,
    reason?: string,
    token?: string
  ): Promise<ClarificationRequestDetailResponse> {
    return api.post<ClarificationRequestDetailResponse>(
      `/api/v1/procurement/clarifications/${clarificationId}/cancel`,
      { reason },
      { token }
    );
  },

  /**
   * Trigger deterministic re-evaluation of criteria using updated evidence.
   */
  async reevaluateEvidence(
    clarificationId: string,
    token?: string
  ): Promise<{
    bid_id: string;
    compliance_status: string;
    total_score?: number | null;
    risk_level?: string | null;
  }> {
    return api.post(
      `/api/v1/procurement/clarifications/${clarificationId}/reevaluate`,
      {},
      { token }
    );
  },
};

export const bidderClarificationsApi = {
  /**
   * List clarification requests scoped to the Bidder's organization.
   */
  async listClarifications(
    params?: ListClarificationParams,
    token?: string
  ): Promise<ClarificationRequestListResponse> {
    return api.get<ClarificationRequestListResponse>(
      "/api/v1/bidder/clarifications",
      { params: params as Record<string, any>, token }
    );
  },

  /**
   * Get Bidder KPI summary counts.
   */
  async getSummary(token?: string): Promise<ClarificationSummaryResponse> {
    return api.get<ClarificationSummaryResponse>(
      "/api/v1/bidder/clarifications/summary",
      { token }
    );
  },

  /**
   * Retrieve single clarification thread (marks status as VIEWED if previously SENT).
   */
  async getClarification(
    clarificationId: string,
    token?: string
  ): Promise<ClarificationRequestDetailResponse> {
    return api.get<ClarificationRequestDetailResponse>(
      `/api/v1/bidder/clarifications/${clarificationId}`,
      { token }
    );
  },

  /**
   * Submit text response and linked document attachment.
   */
  async respondToClarification(
    clarificationId: string,
    payload: ClarificationResponseCreate,
    token?: string
  ): Promise<ClarificationResponseDTO> {
    return api.post<ClarificationResponseDTO>(
      `/api/v1/bidder/clarifications/${clarificationId}/respond`,
      payload,
      { token }
    );
  },

  /**
   * Securely upload supporting or replacement document with automated quality & AI processing.
   */
  async uploadSupportingDocument(
    clarificationId: string,
    file: File,
    documentType: string = "SUPPORTING_EVIDENCE",
    isReplacement: boolean = false,
    replacesDocumentId?: string,
    token?: string
  ): Promise<{
    document_id: string;
    original_filename: string;
    status: string;
    version: number;
    quality_score?: number | null;
  }> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", documentType);
    formData.append("is_replacement", String(isReplacement));
    if (replacesDocumentId) {
      formData.append("replaces_document_id", replacesDocumentId);
    }

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/bidder/clarifications/${clarificationId}/upload-document`,
      {
        method: "POST",
        headers,
        body: formData,
      }
    );

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Failed to upload document");
    }

    return res.json();
  },
};
