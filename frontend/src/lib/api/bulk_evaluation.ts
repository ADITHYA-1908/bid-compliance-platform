/**
 * API Client for Part 9: Bulk Verification & Batch Processing
 */

import { api } from "@/lib/api";
import {
  BulkEvaluationCancelResponse,
  BulkEvaluationJobCreateResponse,
  BulkEvaluationJobItemsListResponse,
  BulkEvaluationJobStatusResponse,
  BulkEvaluationRetryResponse,
  BulkEvaluationJobItem,
} from "@/types/bulk_evaluation";

export async function triggerBulkEvaluation(tenderId: string): Promise<BulkEvaluationJobCreateResponse> {
  return api.post<BulkEvaluationJobCreateResponse>(`/api/v1/procurement/tenders/${tenderId}/bulk-evaluation`);
}

export async function getActiveTenderBulkEvaluation(tenderId: string): Promise<BulkEvaluationJobStatusResponse | null> {
  return api.get<BulkEvaluationJobStatusResponse | null>(`/api/v1/procurement/tenders/${tenderId}/bulk-evaluation/active`);
}

export async function getBulkEvaluationStatus(jobId: string): Promise<BulkEvaluationJobStatusResponse> {
  return api.get<BulkEvaluationJobStatusResponse>(`/api/v1/procurement/bulk-evaluations/${jobId}`);
}

export async function getBulkEvaluationItems(
  jobId: string,
  status?: string,
  page = 1,
  pageSize = 20
): Promise<BulkEvaluationJobItemsListResponse> {
  const query = new URLSearchParams();
  if (status) query.append("status", status);
  query.append("page", page.toString());
  query.append("page_size", pageSize.toString());

  return api.get<BulkEvaluationJobItemsListResponse>(
    `/api/v1/procurement/bulk-evaluations/${jobId}/items?${query.toString()}`
  );
}

export async function retryFailedBulkItems(jobId: string): Promise<BulkEvaluationRetryResponse> {
  return api.post<BulkEvaluationRetryResponse>(`/api/v1/procurement/bulk-evaluations/${jobId}/retry-failed`);
}

export async function retrySingleBulkItem(jobId: string, itemId: string): Promise<BulkEvaluationJobItem> {
  return api.post<BulkEvaluationJobItem>(`/api/v1/procurement/bulk-evaluations/${jobId}/items/${itemId}/retry`);
}

export async function cancelBulkEvaluation(jobId: string): Promise<BulkEvaluationCancelResponse> {
  return api.post<BulkEvaluationCancelResponse>(`/api/v1/procurement/bulk-evaluations/${jobId}/cancel`);
}
