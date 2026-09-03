import { apiRequest } from '../api';

export interface CommercialEvaluationResultItem {
  id: string;
  tender_id: string;
  bid_id: string;
  bid_number?: string | null;
  bidder_name?: string | null;
  evaluation_method: string;
  eligibility_status: string;
  quoted_amount?: number | null;
  currency: string;
  technical_score?: number | null;
  financial_score?: number | null;
  final_score?: number | null;
  commercial_rank?: number | null;
  rank_label: string;
  is_l1: boolean;
  is_tie: boolean;
  has_critical_blocker: boolean;
  blocker_reason?: string | null;
  explanation: string;
  formula_snapshot: Record<string, any>;
  evaluated_at: string;
  is_current: boolean;
}

export interface TenderCommercialEvaluationResponse {
  tender_id: string;
  tender_number: string;
  tender_title: string;
  evaluation_method: string;
  technical_weight?: number | null;
  financial_weight?: number | null;
  custom_weights?: Record<string, any> | null;
  total_evaluated_bids: number;
  eligible_bids_count: number;
  ineligible_bids_count: number;
  lowest_compliant_price?: number | null;
  results: CommercialEvaluationResultItem[];
  evaluated_at: string;
}

export async function getTenderCommercialEvaluation(tenderId: string): Promise<TenderCommercialEvaluationResponse> {
  return apiRequest<TenderCommercialEvaluationResponse>(`/procurement/tenders/${tenderId}/commercial-evaluation`, {
    method: 'GET',
  });
}

export async function reevaluateTenderCommercials(tenderId: string): Promise<TenderCommercialEvaluationResponse> {
  return apiRequest<TenderCommercialEvaluationResponse>(`/procurement/tenders/${tenderId}/commercial-evaluation/evaluate`, {
    method: 'POST',
  });
}
