import { api } from "@/lib/api";
import {
  ProcurementDashboardSummaryResponse,
  TenderBidEvaluationsListResponse,
  TenderBidEvaluationsQueryParams,
} from "@/types/procurement_dashboard";

/**
 * Fetches high-level procurement dashboard metrics and active tender evaluation statuses.
 */
export async function getProcurementDashboardSummary(): Promise<ProcurementDashboardSummaryResponse> {
  return await api.get<ProcurementDashboardSummaryResponse>(
    "/procurement/dashboard"
  );
}

/**
 * Fetches the paginated, filtered evaluation matrix for all submitted bids of a tender.
 */
export async function getTenderBidEvaluations(
  tenderId: string,
  params?: TenderBidEvaluationsQueryParams
): Promise<TenderBidEvaluationsListResponse> {
  const query = new URLSearchParams();

  if (params?.search) query.append("search", params.search);
  if (params?.status) query.append("status", params.status);
  if (params?.risk_level) query.append("risk_level", params.risk_level);
  if (params?.review_required !== undefined) {
    query.append("review_required", String(params.review_required));
  }
  if (params?.critical_only) {
    query.append("critical_only", "true");
  }
  if (params?.recommendation) {
    query.append("recommendation", params.recommendation);
  }
  if (params?.shortlisted_only) {
    query.append("shortlisted_only", "true");
  }
  if (params?.sort_by) query.append("sort_by", params.sort_by);
  if (params?.sort_dir) query.append("sort_dir", params.sort_dir);
  if (params?.page) query.append("page", String(params.page));
  if (params?.page_size) query.append("page_size", String(params.page_size));

  const url = `/procurement/tenders/${tenderId}/evaluations${
    query.toString() ? `?${query.toString()}` : ""
  }`;

  return await api.get<TenderBidEvaluationsListResponse>(url);
}
