/**
 * Compliance Rule Version History API Client
 * Part 15 — Compliance Rule Version History for BidVerify AI
 */

import { api } from "@/lib/api";
import {
  ReevaluationResultResponse,
  TenderRequirementUpdateWithVersionRequest,
  TenderRequirementVersionCompareResponse,
  TenderRequirementVersionListResponse,
  TenderRequirementVersionResponse,
} from "@/types/rule_versions";

export const ruleVersionsApi = {
  /**
   * Get complete version history timeline for a tender requirement.
   */
  async getRequirementVersions(
    tenderId: string,
    requirementId: string,
    token?: string
  ): Promise<TenderRequirementVersionListResponse> {
    return api.get<TenderRequirementVersionListResponse>(
      `/api/v1/tenders/${tenderId}/requirements/${requirementId}/versions`,
      { token }
    );
  },

  /**
   * Get a specific version record by version number or UUID.
   */
  async getRequirementVersion(
    tenderId: string,
    requirementId: string,
    versionIdentifier: string | number,
    token?: string
  ): Promise<TenderRequirementVersionResponse> {
    return api.get<TenderRequirementVersionResponse>(
      `/api/v1/tenders/${tenderId}/requirements/${requirementId}/versions/${versionIdentifier}`,
      { token }
    );
  },

  /**
   * Compare two versions side-by-side with field-level diffs and impact classifications.
   */
  async compareRequirementVersions(
    tenderId: string,
    requirementId: string,
    v1: number,
    v2: number,
    token?: string
  ): Promise<TenderRequirementVersionCompareResponse> {
    return api.get<TenderRequirementVersionCompareResponse>(
      `/api/v1/tenders/${tenderId}/requirements/${requirementId}/versions/compare`,
      {
        params: { v1, v2 },
        token,
      }
    );
  },

  /**
   * Update a requirement creating an immutable version record with change rationale.
   */
  async updateRequirementWithVersion(
    tenderId: string,
    requirementId: string,
    data: TenderRequirementUpdateWithVersionRequest,
    token?: string
  ): Promise<any> {
    return api.put<any>(
      `/api/v1/tenders/${tenderId}/requirements/${requirementId}`,
      data,
      { token }
    );
  },

  /**
   * Re-evaluate all submitted bids for a tender against latest version of a specific requirement.
   */
  async reevaluateRequirementBids(
    tenderId: string,
    requirementId: string,
    token?: string
  ): Promise<ReevaluationResultResponse> {
    return api.post<ReevaluationResultResponse>(
      `/api/v1/tenders/${tenderId}/requirements/${requirementId}/reevaluate`,
      {},
      { token }
    );
  },

  /**
   * Re-evaluate all submitted bids across all requirements for a tender.
   */
  async reevaluateAllTenderRules(
    tenderId: string,
    token?: string
  ): Promise<ReevaluationResultResponse> {
    return api.post<ReevaluationResultResponse>(
      `/api/v1/tenders/${tenderId}/reevaluate-all-rules`,
      {},
      { token }
    );
  },
};
