import { api } from '@/lib/api';
import { BidRiskAssessmentResponse } from '@/types/risk';

export async function getBidRisk(bidId: string): Promise<BidRiskAssessmentResponse> {
  return await api.get<BidRiskAssessmentResponse>(`/bidder/bids/${bidId}/risk`);
}

export async function calculateBidRisk(bidId: string): Promise<BidRiskAssessmentResponse> {
  return await api.post<BidRiskAssessmentResponse>(`/bidder/bids/${bidId}/risk/calculate`);
}

export async function getProcurementBidRisk(bidId: string): Promise<BidRiskAssessmentResponse> {
  return await api.get<BidRiskAssessmentResponse>(`/procurement/bids/${bidId}/risk`);
}

export async function calculateProcurementBidRisk(bidId: string): Promise<BidRiskAssessmentResponse> {
  return await api.post<BidRiskAssessmentResponse>(`/procurement/bids/${bidId}/risk/calculate`);
}
