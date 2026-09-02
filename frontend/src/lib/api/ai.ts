import { api } from '@/lib/api';
import {
  AIQuestionRequest,
  AIQuestionResponse,
  AIRecommendationResponse,
} from '@/types/ai';

export async function getProcurementBidAIRecommendation(
  bidId: string
): Promise<AIRecommendationResponse | null> {
  return await api.get<AIRecommendationResponse | null>(
    `/procurement/bids/${bidId}/ai/recommendation`
  );
}

export async function generateProcurementBidAIRecommendation(
  bidId: string
): Promise<AIRecommendationResponse> {
  return await api.post<AIRecommendationResponse>(
    `/procurement/bids/${bidId}/ai/recommendation`
  );
}

export async function askProcurementBidAIQuestion(
  bidId: string,
  question: string
): Promise<AIQuestionResponse> {
  return await api.post<AIQuestionResponse>(
    `/procurement/bids/${bidId}/ai/ask`,
    { question }
  );
}
