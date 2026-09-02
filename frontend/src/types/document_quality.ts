/**
 * TypeScript Interfaces for Part 11: Advanced Document Quality Check
 */

export type QualityLevel = "GOOD" | "ACCEPTABLE" | "POOR" | "UNUSABLE";

export interface DocumentPageQuality {
  id: string;
  quality_result_id: string;
  document_id: string;
  page_number: number;
  blur_score: number;
  width?: number | null;
  height?: number | null;
  dpi?: number | null;
  resolution?: string | null;
  ocr_confidence?: number | null;
  is_blank: boolean;
  is_unreadable: boolean;
  is_skewed: boolean;
  skew_angle?: number | null;
  quality_level: QualityLevel | string;
  review_reason?: string | null;
  issues: string[];
  created_at: string;
  updated_at: string;
}

export interface DocumentQualityResult {
  id: string;
  document_id: string;
  processing_id?: string | null;
  quality_score: number;
  quality_level: QualityLevel | string;
  is_blurry: boolean;
  has_blank_pages: boolean;
  has_unreadable_pages: boolean;
  has_low_resolution_pages: boolean;
  has_skewed_pages: boolean;
  is_corrupted: boolean;
  is_password_protected: boolean;
  ocr_confidence?: number | null;
  average_ocr_confidence?: number | null;
  min_page_ocr_confidence?: number | null;
  page_count: number;
  review_required: boolean;
  review_reasons: string[];
  bidder_feedback: string[];
  metrics_summary: Record<string, any>;
  page_qualities: DocumentPageQuality[];
  created_at: string;
  updated_at: string;
}

export interface QualityCheckTriggerResponse {
  document_id: string;
  quality_score: number;
  quality_level: QualityLevel | string;
  review_required: boolean;
  message: string;
  bidder_feedback: string[];
  created_at: string;
}
