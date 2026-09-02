import { api } from '@/lib/api';
import { BidEvaluationSummaryResponse } from '@/types/evaluation';

export async function getProcurementBidEvaluationSummary(
  bidId: string
): Promise<BidEvaluationSummaryResponse> {
  return await api.get<BidEvaluationSummaryResponse>(
    `/procurement/bids/${bidId}/evaluation`
  );
}

export async function refreshProcurementBidEvaluation(
  bidId: string,
  refreshAi: boolean = false
): Promise<BidEvaluationSummaryResponse> {
  return await api.post<BidEvaluationSummaryResponse>(
    `/procurement/bids/${bidId}/evaluation/refresh?refresh_ai=${refreshAi}`
  );
}

export async function regenerateProcurementBidAIEvaluation(
  bidId: string
): Promise<BidEvaluationSummaryResponse> {
  return await api.post<BidEvaluationSummaryResponse>(
    `/procurement/bids/${bidId}/evaluation/ai/regenerate`
  );
}
