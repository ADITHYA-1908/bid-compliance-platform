/**
 * API Client for Part 8C: Human Review & Evidence Inspection Workflow
 */

import { api } from "@/lib/api";
import {
  ReviewQueueResponse,
  ReviewDetailResponse,
  AddReviewNoteRequest,
  ResolveReviewRequest,
} from "@/types/human_review";

export async function getHumanReviewQueue(params?: {
  tender_id?: string;
  bid_id?: string;
  status?: string;
  severity?: string;
  review_type?: string;
  category?: string;
  critical_only?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<ReviewQueueResponse> {
  const query = new URLSearchParams();
  if (params?.tender_id) query.append("tender_id", params.tender_id);
  if (params?.bid_id) query.append("bid_id", params.bid_id);
  if (params?.status) query.append("status", params.status);
  if (params?.severity) query.append("severity", params.severity);
  if (params?.review_type) query.append("review_type", params.review_type);
  if (params?.category) query.append("category", params.category);
  if (params?.critical_only !== undefined) query.append("critical_only", String(params.critical_only));
  if (params?.search) query.append("search", params.search);
  if (params?.page) query.append("page", String(params.page));
  if (params?.page_size) query.append("page_size", String(params.page_size));

  const endpoint = `/procurement/reviews${query.toString() ? `?${query.toString()}` : ""}`;
  return api.get<ReviewQueueResponse>(endpoint);
}

export async function getHumanReviewDetail(reviewId: string): Promise<ReviewDetailResponse> {
  return api.get<ReviewDetailResponse>(`/procurement/reviews/${reviewId}`);
}

export async function startHumanReview(reviewId: string): Promise<ReviewDetailResponse> {
  return api.post<ReviewDetailResponse>(`/procurement/reviews/${reviewId}/start`, {});
}

export async function addHumanReviewNote(
  reviewId: string,
  request: AddReviewNoteRequest
): Promise<ReviewDetailResponse> {
  return api.post<ReviewDetailResponse>(`/procurement/reviews/${reviewId}/notes`, request);
}

export async function resolveHumanReview(
  reviewId: string,
  request: ResolveReviewRequest
): Promise<ReviewDetailResponse> {
  return api.post<ReviewDetailResponse>(`/procurement/reviews/${reviewId}/resolve`, request);
}

export async function syncBidReviews(tenderId: string, bidId: string): Promise<ReviewDetailResponse[]> {
  return api.post<ReviewDetailResponse[]>(`/procurement/tenders/${tenderId}/bids/${bidId}/sync-reviews`, {});
}
