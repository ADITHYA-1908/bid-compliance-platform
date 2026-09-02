/**
 * Certificate Validity API Client
 * Part 14 — Certificate Validity Monitoring for BidVerify AI
 */

import { api } from "@/lib/api";
import {
  BidderCertificateListResponse,
  CertificateValidityRecheckResponse,
  DocumentValidityItem,
  PeriodicValidityCheckResponse,
  ProcurementCertificateListResponse,
} from "@/types/certificate_validity";

export const certificateValidityApi = {
  // Bidder Endpoints
  async getBidderCertificates(
    params?: {
      page?: number;
      page_size?: number;
      status?: string;
      search?: string;
    },
    token?: string
  ): Promise<BidderCertificateListResponse> {
    return api.get<BidderCertificateListResponse>("/api/v1/bidder/certificates/validity", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  async getDocumentValidity(documentId: string, token?: string): Promise<DocumentValidityItem> {
    return api.get<DocumentValidityItem>(
      `/api/v1/bidder/certificates/documents/${documentId}/validity`,
      { token }
    );
  },

  async recheckDocumentValidity(
    documentId: string,
    token?: string
  ): Promise<CertificateValidityRecheckResponse> {
    return api.post<CertificateValidityRecheckResponse>(
      `/api/v1/bidder/certificates/documents/${documentId}/validity/recheck`,
      {},
      { token }
    );
  },

  // Procurement Endpoints
  async getProcurementCertificates(
    params?: {
      page?: number;
      page_size?: number;
      tender_id?: string;
      bid_id?: string;
      status?: string;
      search?: string;
    },
    token?: string
  ): Promise<ProcurementCertificateListResponse> {
    return api.get<ProcurementCertificateListResponse>("/api/v1/procurement/certificates/validity", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  async getBidCertificatesValidity(
    bidId: string,
    token?: string
  ): Promise<ProcurementCertificateListResponse> {
    return api.get<ProcurementCertificateListResponse>(
      `/api/v1/procurement/certificates/bids/${bidId}/certificate-validity`,
      { token }
    );
  },

  async procurementRecheckDocument(
    documentId: string,
    token?: string
  ): Promise<CertificateValidityRecheckResponse> {
    return api.post<CertificateValidityRecheckResponse>(
      `/api/v1/procurement/certificates/documents/${documentId}/validity/recheck`,
      {},
      { token }
    );
  },

  async triggerPeriodicCheck(
    referenceDate?: string,
    token?: string
  ): Promise<PeriodicValidityCheckResponse> {
    const query = referenceDate ? `?reference_date=${encodeURIComponent(referenceDate)}` : "";
    return api.post<PeriodicValidityCheckResponse>(
      `/api/v1/procurement/certificates/periodic-check${query}`,
      {},
      { token }
    );
  },
};
