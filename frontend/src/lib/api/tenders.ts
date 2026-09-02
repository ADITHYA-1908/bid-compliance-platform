import {
  api,
  TenderListParams,
  TenderListResponse,
  TenderCreatePayload,
  TenderUpdatePayload,
} from "@/lib/api";
import { Tender } from "@/types/tender";

export async function getTendersList(
  params?: TenderListParams
): Promise<TenderListResponse> {
  return api.getTenders(params);
}

export async function getTenderDetail(id: string): Promise<Tender> {
  return api.getTender(id);
}

export async function createTender(
  payload: TenderCreatePayload
): Promise<Tender> {
  return api.createTender(payload);
}

export async function updateTender(
  id: string,
  payload: TenderUpdatePayload
): Promise<Tender> {
  return api.updateTender(id, payload);
}

export async function archiveTender(id: string): Promise<Tender> {
  return api.archiveTender(id);
}

export async function transitionTenderStatus(
  id: string,
  targetStatus: string,
  remarks?: string
): Promise<Tender> {
  return api.transitionTenderStatus(id, targetStatus, remarks);
}
