/**
 * API client for Part 8E: Audit Trail & Decision History
 */

import { api } from '@/lib/api';
import {
  AuditEventItem,
  AuditFilterParams,
  AuditListResponse,
} from '@/types/audit';

export async function getAuditEvents(
  params?: AuditFilterParams
): Promise<AuditListResponse> {
  const searchParams = new URLSearchParams();

  if (params) {
    if (params.tender_id) searchParams.append('tender_id', params.tender_id);
    if (params.bid_id) searchParams.append('bid_id', params.bid_id);
    if (params.actor_user_id) searchParams.append('actor_user_id', params.actor_user_id);
    if (params.event_type) searchParams.append('event_type', params.event_type);
    if (params.entity_type) searchParams.append('entity_type', params.entity_type);
    if (params.date_from) searchParams.append('date_from', params.date_from);
    if (params.date_to) searchParams.append('date_to', params.date_to);
    if (params.search) searchParams.append('search', params.search);
    if (params.page) searchParams.append('page', params.page.toString());
    if (params.page_size) searchParams.append('page_size', params.page_size.toString());
  }

  const query = searchParams.toString();
  const endpoint = `/procurement/audit${query ? `?${query}` : ''}`;
  return await api.get<AuditListResponse>(endpoint);
}

export async function getTenderAuditEvents(
  tenderId: string,
  eventType?: string,
  page: number = 1,
  pageSize: number = 20
): Promise<AuditListResponse> {
  const searchParams = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });
  if (eventType) searchParams.append('event_type', eventType);

  return await api.get<AuditListResponse>(
    `/procurement/tenders/${tenderId}/audit?${searchParams.toString()}`
  );
}

export async function getBidAuditEvents(
  tenderId: string,
  bidId: string,
  page: number = 1,
  pageSize: number = 50
): Promise<AuditListResponse> {
  const searchParams = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });

  return await api.get<AuditListResponse>(
    `/procurement/tenders/${tenderId}/bids/${bidId}/audit?${searchParams.toString()}`
  );
}

export async function getBidTimeline(
  tenderId: string,
  bidId: string
): Promise<AuditEventItem[]> {
  return await api.get<AuditEventItem[]>(
    `/procurement/tenders/${tenderId}/bids/${bidId}/timeline`
  );
}
