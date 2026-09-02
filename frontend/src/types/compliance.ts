export type ComplianceStatus =
  | 'PASS'
  | 'FAIL'
  | 'REVIEW'
  | 'NOT_APPLICABLE'
  | 'PENDING'
  | 'BLOCKED';

export const ComplianceStatus = {
  PASS: 'PASS' as const,
  FAIL: 'FAIL' as const,
  REVIEW: 'REVIEW' as const,
  NOT_APPLICABLE: 'NOT_APPLICABLE' as const,
  PENDING: 'PENDING' as const,
  BLOCKED: 'BLOCKED' as const,
};

export interface ComplianceReviewItemResponse {
  requirement_code: string;
  requirement_name: string;
  category: string;
  review_type?: string | null;
  review_reason: string;
  source_name?: string | null;
  is_mandatory: boolean;
  is_critical: boolean;
}

export interface ComplianceResultItem {
  id: string;
  bid_id: string;
  tender_id: string;
  tender_requirement_id: string;
  requirement_code: string;
  requirement_name: string;
  category: string;
  requirement_type: string;
  compliance_status: ComplianceStatus;
  actual_value?: any;
  expected_value?: any;
  operator?: string;
  reason?: string;
  evidence?: Record<string, any>;
  source_verification_ids?: string[];
  is_mandatory: boolean;
  is_critical?: boolean;
  critical_failure?: boolean;
  weight?: number;
  evaluation_version: number;
  is_current: boolean;
  rule_version_id?: string | null;
  rule_version_number?: number | null;
  rule_version_code?: string | null;
  rule_version_name?: string | null;
  rule_version_operator?: string | null;
  rule_version_expected_value?: any;
  evaluated_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ComplianceSummaryCounts {
  total: number;
  passed: number;
  failed: number;
  review: number;
  pending: number;
  not_applicable: number;
  blocked: number;
  mandatory_failures?: number;
  critical_failures?: number;
}

export interface BidComplianceSummaryResponse {
  bid_id: string;
  tender_id: string;
  tender_number?: string;
  bidder_name?: string;
  compliance_evaluation_complete: boolean;
  counts: ComplianceSummaryCounts;
  results: ComplianceResultItem[];
  review_items?: ComplianceReviewItemResponse[];
  evaluated_at?: string;
  evaluation_version?: number;
}

