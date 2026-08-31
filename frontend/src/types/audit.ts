export interface AuditEventActorSummary {
  user_id?: string | null;
  profile_id?: string | null;
  name?: string | null;
  role?: string | null;
  source: string;
}

export interface AuditEventItem {
  id: string;
  organization_id: string;
  tender_id?: string | null;
  bid_id?: string | null;
  tender_number?: string | null;
  bid_number?: string | null;
  bidder_name?: string | null;
  actor: AuditEventActorSummary;
  event_type: string;
  event_label: string;
  entity_type: string;
  entity_id?: string | null;
  action: string;
  summary: string;
  metadata: Record<string, any>;
  ip_address?: string | null;
  created_at: string;
}

export interface AuditKPIs {
  total_events: number;
  events_today: number;
  decisions_recorded: number;
  reviews_resolved: number;
  ai_events: number;
  system_events: number;
}

export interface AuditListResponse {
  items: AuditEventItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  kpis: AuditKPIs;
}

export interface AuditFilterParams {
  tender_id?: string;
  bid_id?: string;
  actor_user_id?: string;
  event_type?: string;
  entity_type?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}
