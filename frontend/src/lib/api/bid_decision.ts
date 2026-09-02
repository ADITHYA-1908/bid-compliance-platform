/**
 * API client for Part 8D: Final Human Decision Workflow
 */

import { api } from '@/lib/api';
import {
  BidDecision,
  BidDecisionHistoryItem,
  RecordBidDecisionRequest,
} from '@/types/bid_decision';

export async function getBidDecision(
  tenderId: string,
  bidId: string
): Promise<BidDecision> {
  return await api.get<BidDecision>(
    `/procurement/tenders/${tenderId}/bids/${bidId}/decision`
  );
}

export async function recordBidDecision(
  tenderId: string,
  bidId: string,
  payload: RecordBidDecisionRequest
): Promise<BidDecision> {
  return await api.post<BidDecision>(
    `/procurement/tenders/${tenderId}/bids/${bidId}/decision`,
    payload
  );
}

export async function getBidDecisionHistory(
  tenderId: string,
  bidId: string
): Promise<BidDecisionHistoryItem[]> {
  return await api.get<BidDecisionHistoryItem[]>(
    `/procurement/tenders/${tenderId}/bids/${bidId}/decisions`
  );
}
