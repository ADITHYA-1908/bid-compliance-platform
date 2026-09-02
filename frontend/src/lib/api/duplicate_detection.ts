/**
 * API Client for Part 10: Duplicate / Reuse Document Detection
 */

import { api } from "@/lib/api";
import {
  DuplicateMatchDetail,
  DuplicateMatchListResponse,
  DuplicateReviewRequest,
  DuplicateReviewResponse,
  DuplicateScanResponse,
} from "@/types/duplicate_detection";

export async function triggerTenderDuplicateScan(tenderId: string): Promise<DuplicateScanResponse> {
  return api.post<DuplicateScanResponse>(`/api/v1/procurement/tenders/${tenderId}/duplicate-scan`);
}

export async function getTenderDuplicateMatches(
  tenderId: string,
  status?: string,
  matchType?: string
): Promise<DuplicateMatchListResponse> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (matchType) params.append("match_type", matchType);

  const qs = params.toString() ? `?${params.toString()}` : "";
  return api.get<DuplicateMatchListResponse>(`/api/v1/procurement/tenders/${tenderId}/duplicate-matches${qs}`);
}

export async function getDuplicateMatchDetail(matchId: string): Promise<DuplicateMatchDetail> {
  return api.get<DuplicateMatchDetail>(`/api/v1/procurement/duplicate-matches/${matchId}`);
}

export async function submitDuplicateReview(
  matchId: string,
  payload: DuplicateReviewRequest
): Promise<DuplicateReviewResponse> {
  return api.post<DuplicateReviewResponse>(`/api/v1/procurement/duplicate-matches/${matchId}/review`, payload);
}
