/**
 * API Client for Part 11: Advanced Document Quality Check
 */

import { api } from "@/lib/api";
import { DocumentQualityResult, QualityCheckTriggerResponse } from "@/types/document_quality";

export const documentQualityApi = {
  /**
   * Retrieves document quality telemetry and page diagnostics for a bidder's document.
   */
  getBidderDocumentQuality: async (
    bidId: string,
    documentId: string
  ): Promise<DocumentQualityResult> => {
    return api.get<DocumentQualityResult>(
      `/api/v1/bidder/bids/${bidId}/documents/${documentId}/quality`
    );
  },

  /**
   * Triggers explicit pre-flight document quality evaluation.
   */
  triggerQualityCheck: async (
    bidId: string,
    documentId: string
  ): Promise<QualityCheckTriggerResponse> => {
    return api.post<QualityCheckTriggerResponse>(
      `/api/v1/bidder/bids/${bidId}/documents/${documentId}/quality-check`,
      {}
    );
  },

  /**
   * Retrieves complete document quality evidence and diagnostic metrics for Procurement Officers.
   */
  getProcurementDocumentQuality: async (
    tenderId: string,
    bidId: string,
    documentId: string
  ): Promise<DocumentQualityResult> => {
    return api.get<DocumentQualityResult>(
      `/api/v1/procurement/tenders/${tenderId}/bids/${bidId}/documents/${documentId}/quality`
    );
  },
};
