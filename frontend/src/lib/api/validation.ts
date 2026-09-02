/**
 * Validation and Benchmarking API Client
 */

import { api } from "@/lib/api";
import {
  ValidationCaseListResponse,
  ValidationPPTSummary,
  ValidationRun,
  ValidationRunListResponse,
} from "@/types/validation";

export const validationApi = {
  /**
   * Triggers a new benchmark execution.
   */
  async createValidationRun(
    payload?: { name?: string; tags?: string[]; max_cases?: number; notes?: string },
    token?: string
  ): Promise<ValidationRun> {
    return api.post<ValidationRun>("/api/v1/admin/validation/runs", payload || {}, { token });
  },

  /**
   * Retrieves historical validation runs.
   */
  async getValidationRuns(
    params?: { page?: number; page_size?: number },
    token?: string
  ): Promise<ValidationRunListResponse> {
    return api.get<ValidationRunListResponse>("/api/v1/admin/validation/runs", {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  /**
   * Retrieves detailed metrics for a specific run.
   */
  async getValidationRun(runId: string, token?: string): Promise<ValidationRun> {
    return api.get<ValidationRun>(`/api/v1/admin/validation/runs/${runId}`, { token });
  },

  /**
   * Retrieves granular case results for a specific run.
   */
  async getValidationCaseResults(
    runId: string,
    params?: {
      category?: string;
      error_type?: string;
      failed_only?: boolean;
      search?: string;
      page?: number;
      page_size?: number;
    },
    token?: string
  ): Promise<ValidationCaseListResponse> {
    return api.get<ValidationCaseListResponse>(`/api/v1/admin/validation/runs/${runId}/cases`, {
      params: params as Record<string, string | number | boolean | undefined>,
      token,
    });
  },

  /**
   * Generates PPT-ready executive performance summary.
   */
  async getPPTSummary(runId: string, token?: string): Promise<ValidationPPTSummary> {
    return api.get<ValidationPPTSummary>(`/api/v1/admin/validation/runs/${runId}/ppt-summary`, { token });
  },

  /**
   * Export CSV download URL.
   */
  getExportUrl(runId: string, format: "csv" | "json" = "csv"): string {
    return `/api/v1/admin/validation/runs/${runId}/export?format=${format}`;
  },
};
