import { api } from '@/lib/api';
import { BidScoringFoundationResponse } from '@/types/scoring';

export async function getBidScore(bidId: string): Promise<BidScoringFoundationResponse> {
  return await api.get<BidScoringFoundationResponse>(`/bidder/bids/${bidId}/score`);
}

export async function calculateBidScore(bidId: string): Promise<BidScoringFoundationResponse> {
  return await api.post<BidScoringFoundationResponse>(`/bidder/bids/${bidId}/score/calculate`);
}

export async function getProcurementBidScore(bidId: string): Promise<BidScoringFoundationResponse> {
  return await api.get<BidScoringFoundationResponse>(`/procurement/bids/${bidId}/score`);
}

export async function calculateProcurementBidScore(bidId: string): Promise<BidScoringFoundationResponse> {
  return await api.post<BidScoringFoundationResponse>(`/procurement/bids/${bidId}/score/calculate`);
}
