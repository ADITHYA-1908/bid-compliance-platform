/**
 * Procurement Analytics API Client (Part 13)
 */

import { api } from "@/lib/api";
import {
  BulkAnalytics,
  ComplianceAnalytics,
  DocumentQualityAnalytics,
  DuplicateAnalytics,
  HumanReviewAndDecision,
  OverviewKPIs,
  RiskAnalytics,
  TenderSpecificAnalytics,
  TimeSeriesPoint,
  VerificationAnalytics,
} from "@/types/analytics";

export interface AnalyticsFilterParams {
  tender_id?: string;
  start_date?: string;
  end_date?: string;
  days?: number;
}

export const analyticsApi = {
  /**
   * Retrieves high-level overview KPIs and impact savings.
   */
  async getOverviewKPIs(params?: AnalyticsFilterParams, token?: string): Promise<OverviewKPIs> {
    return api.get<OverviewKPIs>("/api/v1/procurement/analytics/overview", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  /**
   * Retrieves compliance results and root-cause failure breakdown.
   */
  async getComplianceAnalytics(params?: AnalyticsFilterParams, token?: string): Promise<ComplianceAnalytics> {
    return api.get<ComplianceAnalytics>("/api/v1/procurement/analytics/compliance", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  /**
   * Retrieves risk distribution and override signals.
   */
  async getRiskAnalytics(params?: AnalyticsFilterParams, token?: string): Promise<RiskAnalytics> {
    return api.get<RiskAnalytics>("/api/v1/procurement/analytics/risk", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  /**
   * Retrieves verification outcomes and multi-source breakdown.
   */
  async getVerificationAnalytics(params?: AnalyticsFilterParams, token?: string): Promise<VerificationAnalytics> {
    return api.get<VerificationAnalytics>("/api/v1/procurement/analytics/verification", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  /**
   * Retrieves document quality tier diagnostics (Part 11).
   */
  async getDocumentQualityAnalytics(
    params?: AnalyticsFilterParams,
    token?: string
  ): Promise<DocumentQualityAnalytics> {
    return api.get<DocumentQualityAnalytics>("/api/v1/procurement/analytics/documents", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  /**
   * Retrieves duplicate and reuse detection analytics (Part 10).
   */
  async getDuplicateAnalytics(params?: AnalyticsFilterParams, token?: string): Promise<DuplicateAnalytics> {
    return api.get<DuplicateAnalytics>("/api/v1/procurement/analytics/duplicates", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  /**
   * Retrieves bulk verification batch telemetry (Part 9).
   */
  async getBulkAnalytics(params?: AnalyticsFilterParams, token?: string): Promise<BulkAnalytics> {
    return api.get<BulkAnalytics>("/api/v1/procurement/analytics/bulk", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  /**
   * Retrieves human review workload and final human qualification decisions (Part 8C & 8D).
   */
  async getHumanReviewsAndDecisions(
    params?: AnalyticsFilterParams,
    token?: string
  ): Promise<HumanReviewAndDecision> {
    return api.get<HumanReviewAndDecision>("/api/v1/procurement/analytics/reviews", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  /**
   * Retrieves daily activity trends time-series.
   */
  async getActivityTrends(params?: AnalyticsFilterParams, token?: string): Promise<TimeSeriesPoint[]> {
    return api.get<TimeSeriesPoint[]>("/api/v1/procurement/analytics/trends", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  /**
   * Retrieves complete deep-dive analytics for a single tender.
   */
  async getTenderSpecificAnalytics(tenderId: string, token?: string): Promise<TenderSpecificAnalytics> {
    return api.get<TenderSpecificAnalytics>(`/api/v1/procurement/analytics/tenders/${tenderId}`, { token });
  },

  /**
   * Export CSV download URL.
   */
  getExportUrl(params?: AnalyticsFilterParams): string {
    const searchParams = new URLSearchParams();
    if (params?.tender_id) searchParams.set("tender_id", params.tender_id);
    if (params?.start_date) searchParams.set("start_date", params.start_date);
    if (params?.end_date) searchParams.set("end_date", params.end_date);
    return `/api/v1/procurement/analytics/export?${searchParams.toString()}`;
  },
};
