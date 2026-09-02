/**
 * Part 15: Compliance Rule Version History TypeScript Interfaces
 * Defines types for immutable requirement version history, field diff comparisons,
 * author provenance, and bid re-evaluation telemetry.
 */

export interface TenderRequirementVersionResponse {
  id: string;
  tender_requirement_id: string;
  tender_id: string;
  version_number: number;
  code: string;
  name: string;
  description?: string | null;
  category: string;
  requirement_type: string;
  operator: string;
  expected_value: any;
  unit?: string | null;
  is_mandatory: boolean;
  is_critical: boolean;
  weight?: number | null;
  display_order: number;
  source_clause?: string | null;
  source_page?: number | null;
  corrigendum_number?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  change_reason?: string | null;
  changed_by_profile_id?: string | null;
  changed_by_name?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TenderRequirementVersionListResponse {
  requirement_id: string;
  tender_id: string;
  code: string;
  name: string;
  current_version_number: number;
  total_versions: number;
  versions: TenderRequirementVersionResponse[];
}

export type DiffImpactLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";

export interface TenderRequirementFieldDiff {
  field_name: string;
  field_label: string;
  old_value: any;
  new_value: any;
  is_different: boolean;
  impact_level: DiffImpactLevel;
  impact_summary?: string | null;
}

export interface TenderRequirementVersionCompareResponse {
  tender_id: string;
  requirement_id: string;
  code: string;
  name: string;
  v1_number: number;
  v2_number: number;
  v1_id: string;
  v2_id: string;
  v1_created_at: string;
  v2_created_at: string;
  v1_reason?: string | null;
  v2_reason?: string | null;
  v1_author?: string | null;
  v2_author?: string | null;
  has_differences: boolean;
  differences_count: number;
  diffs: TenderRequirementFieldDiff[];
}

export interface ReevaluationBidResult {
  bid_id: string;
  bid_number: string;
  bidder_name?: string | null;
  previous_compliance_status?: string | null;
  new_compliance_status: string;
  status_changed: boolean;
  is_critical_failure: boolean;
  score?: number | null;
  risk_level?: string | null;
}

export interface ReevaluationResultResponse {
  tender_id: string;
  tender_number: string;
  requirement_id?: string | null;
  total_bids_evaluated: number;
  status_changes_count: number;
  human_decisions_preserved: number;
  bids: ReevaluationBidResult[];
  reevaluated_at: string;
}

export interface TenderRequirementUpdateWithVersionRequest {
  name?: string;
  description?: string;
  category?: string;
  requirement_type?: string;
  operator?: string;
  expected_value?: any;
  unit?: string;
  is_mandatory?: boolean;
  is_critical?: boolean;
  weight?: number;
  display_order?: number;
  source_clause?: string;
  source_page?: number;
  corrigendum_number?: string;
  effective_from?: string;
  effective_to?: string;
  change_reason?: string;
  is_active?: boolean;
}
