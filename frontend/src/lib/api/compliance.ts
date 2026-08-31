import { api } from '@/lib/api';
import { BidComplianceSummaryResponse } from '@/types/compliance';

export async function getBidCompliance(bidId: string): Promise<BidComplianceSummaryResponse> {
  return await api.get<BidComplianceSummaryResponse>(`/bidder/bids/${bidId}/compliance`);
}

export async function evaluateBidCompliance(bidId: string): Promise<BidComplianceSummaryResponse> {
  return await api.post<BidComplianceSummaryResponse>(`/bidder/bids/${bidId}/compliance/evaluate`);
}

export async function getProcurementBidCompliance(bidId: string): Promise<BidComplianceSummaryResponse> {
  return await api.get<BidComplianceSummaryResponse>(`/procurement/bids/${bidId}/compliance`);
}

export async function evaluateProcurementBidCompliance(bidId: string): Promise<BidComplianceSummaryResponse> {
  return await api.post<BidComplianceSummaryResponse>(`/procurement/bids/${bidId}/compliance/evaluate`);
}
