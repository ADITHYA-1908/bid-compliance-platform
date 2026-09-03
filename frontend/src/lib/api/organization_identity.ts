import { apiRequest } from '../api';

export interface OrganizationIdentityAssessment {
  id: string;
  organization_id: string;
  bid_id?: string | null;
  legal_name_status: string;
  pan_status: string;
  gst_status: string;
  cin_status: string;
  udyam_status: string;
  address_status: string;
  pan_gst_embedded_status: string;
  identity_score: number;
  identity_status: string;
  signals_json: Array<{
    signal: string;
    severity: 'INFO' | 'WARNING' | 'CRITICAL';
    message: string;
  }>;
  evidence_json: Record<string, any>;
  is_current: boolean;
  evaluated_at: string;
}

export interface OrganizationDuplicateMatch {
  id: string;
  organization_a_id: string;
  organization_b_id: string;
  organization_a_name?: string | null;
  organization_b_name?: string | null;
  tender_id?: string | null;
  match_type: string;
  matched_identifiers: Record<string, any>;
  similarity_score: number;
  status: string;
  notes?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at: string;
}

export interface OrganizationIdentityOverview {
  assessment: OrganizationIdentityAssessment;
  duplicate_matches: OrganizationDuplicateMatch[];
}

export async function getBidderOrganizationIdentity(): Promise<OrganizationIdentityOverview> {
  return apiRequest<OrganizationIdentityOverview>('/identity/bidder/organization/identity', {
    method: 'GET',
  });
}

export async function evaluateBidderOrganizationIdentity(): Promise<OrganizationIdentityOverview> {
  return apiRequest<OrganizationIdentityOverview>('/identity/bidder/organization/identity/evaluate', {
    method: 'POST',
  });
}

export async function getProcurementOrganizationIdentity(orgId: string): Promise<OrganizationIdentityOverview> {
  return apiRequest<OrganizationIdentityOverview>(`/identity/procurement/organizations/${orgId}/identity`, {
    method: 'GET',
  });
}

export async function resolveOrganizationDuplicateMatch(
  matchId: string,
  status: string,
  notes?: string
): Promise<OrganizationDuplicateMatch> {
  return apiRequest<OrganizationDuplicateMatch>(`/identity/procurement/organizations/duplicates/${matchId}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ status, notes }),
  });
}
