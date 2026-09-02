export type DuplicateMatchType =
  | 'EXACT_FILE_DUPLICATE'
  | 'CONTENT_DUPLICATE'
  | 'STRUCTURED_DATA_MATCH'
  | 'HIGH_SIMILARITY'
  | 'POSSIBLE_REUSE';

export type DuplicateMatchStatus =
  | 'DETECTED'
  | 'REVIEW_REQUIRED'
  | 'CONFIRMED_BENIGN'
  | 'CONFIRMED_REUSE'
  | 'DISMISSED';

export interface MatchedFieldDetail {
  field_key: string;
  label: string;
  value_a?: string | null;
  value_b?: string | null;
  is_exact_match: boolean;
  weight: number;
}

export interface DocumentComparisonMeta {
  document_id: string;
  bid_id: string;
  bid_number?: string | null;
  bidder_organization_id: string;
  bidder_name: string;
  document_type: string;
  document_name: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  file_hash?: string | null;
  normalized_content_hash?: string | null;
  uploaded_at?: string | null;
  extracted_fields: Record<string, any>;
  text_snippet?: string | null;
}

export interface DuplicateMatchListItem {
  id: string;
  organization_id: string;
  tender_id: string;

  document_a_id: string;
  bid_a_id: string;
  bid_a_number?: string | null;
  bidder_a_name: string;
  document_a_name: string;

  document_b_id: string;
  bid_b_id: string;
  bid_b_number?: string | null;
  bidder_b_name: string;
  document_b_name: string;

  document_type: string;
  match_type: DuplicateMatchType;
  file_hash_match: boolean;
  content_hash_match: boolean;
  structured_field_match_score: number;
  text_similarity_score: number;
  overall_confidence: number;

  status: DuplicateMatchStatus;
  review_required: boolean;
  matched_fields_summary: string[];
  created_at: string;
  updated_at: string;
}

export interface DuplicateMatchDetail {
  id: string;
  organization_id: string;
  tender_id: string;
  tender_title?: string | null;
  tender_number?: string | null;

  document_a: DocumentComparisonMeta;
  document_b: DocumentComparisonMeta;

  match_type: DuplicateMatchType;
  file_hash_match: boolean;
  content_hash_match: boolean;
  structured_field_match_score: number;
  text_similarity_score: number;
  overall_confidence: number;

  status: DuplicateMatchStatus;
  review_required: boolean;
  matched_fields_details: MatchedFieldDetail[];
  evidence_summary: Record<string, any>;

  reviewer_notes?: string | null;
  reviewed_by_profile_id?: string | null;
  reviewed_by_name?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DuplicateMatchSummaryCounts {
  total: number;
  detected: number;
  review_required: number;
  confirmed_reuse: number;
  confirmed_benign: number;
  dismissed: number;
  exact_file_duplicates: number;
  content_duplicates: number;
  structured_matches: number;
  high_similarity: number;
}

export interface DuplicateMatchListResponse {
  items: DuplicateMatchListItem[];
  total: number;
  counts: DuplicateMatchSummaryCounts;
}

export interface DuplicateScanResponse {
  tender_id: string;
  tender_number: string;
  scanned_documents: number;
  scanned_bids: number;
  new_matches_found: number;
  total_active_matches: number;
  duration_ms: number;
  summary: string;
}

export interface DuplicateReviewRequest {
  resolution: 'CONFIRMED_BENIGN' | 'CONFIRMED_REUSE' | 'DISMISSED';
  reviewer_notes?: string;
}

export interface DuplicateReviewResponse {
  match_id: string;
  status: DuplicateMatchStatus;
  resolution: string;
  reviewed_by_name: string;
  reviewed_at: string;
  reviewer_notes?: string | null;
  message: string;
}
