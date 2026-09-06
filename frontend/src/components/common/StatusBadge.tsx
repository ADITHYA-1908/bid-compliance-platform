import React from "react";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  CircleDot,
  Loader2,
  MinusCircle,
} from "lucide-react";

export type StatusType =
  | "PASS"
  | "PASSED"
  | "COMPLIANT"
  | "COMPLIANCE_PASS"
  | "FAIL"
  | "FAILED"
  | "NON_COMPLIANT"
  | "COMPLIANCE_FAIL"
  | "CRITICAL_FAIL"
  | "REVIEW"
  | "REVIEW_REQUIRED"
  | "NEEDS_REVIEW"
  | "PENDING"
  | "VERIFICATION_PENDING"
  | "VALID"
  | "VALID_CERTIFICATE"
  | "NO_EXPIRY"
  | "PERMANENT"
  | "EXPIRING_SOON"
  | "EXPIRED"
  | "GOOD"
  | "ACCEPTABLE"
  | "POOR"
  | "UNUSABLE"
  | "QUALIFIED"
  | "DISQUALIFIED"
  | "UNDER_REVIEW"
  | "IN_REVIEW"
  | "AWAITING_REVIEW"
  | "AWAITING_BIDDER"
  | "DRAFT"
  | "DRAFTING"
  | "PUBLISHED"
  | "OPEN"
  | "CLOSED"
  | "UNDER_EVALUATION"
  | "AWARDED"
  | "ARCHIVED"
  | "SUBMITTED"
  | "UPLOADED"
  | "DOCUMENT_UPLOADED"
  | "VERIFIED"
  | "PROFILE_VERIFIED"
  | "NOT_VERIFIED"
  | "QUALITY_CHECK_COMPLETE"
  | "QUALITY_CHECKED"
  | "EXTRACTION_COMPLETE"
  | "DATA_EXTRACTED"
  | "TEXT_EXTRACTED"
  | "FIELDS_EXTRACTED"
  | "PROCESSING_COMPLETE"
  | "COMPLETE"
  | "EVALUATION_COMPLETE"
  | "RESOLVED"
  | "CLARIFICATION_RESOLVED"
  | "WARNING"
  | "PARTIAL_MATCH"
  | "PARTIAL"
  | "MISMATCH"
  | "VERIFICATION_MISMATCH"
  | "MATCH"
  | "EXACT"
  | "SUCCESS"
  | "ACTION_REQUIRED"
  | "INCOMPLETE"
  | "CANCELLED"
  | "ESCALATED"
  | "SUPERSEDED"
  | "NOT_APPLICABLE"
  | string;

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
  showIcon?: boolean;
}

export function StatusBadge({
  status,
  label: customLabel,
  size = "md",
  className = "",
  showIcon = true,
}: StatusBadgeProps) {
  const normStatus = (status || "").toUpperCase().trim();

  let colorClasses = "bg-slate-100 text-slate-700 border-slate-200";
  let IconComponent: React.ElementType | null = Clock;
  let defaultLabel = normStatus.replace(/_/g, " ");

  switch (normStatus) {
    // ==========================================
    // ✓ CHECK / VERIFIED / SUCCESS / PASS STATES
    // ==========================================
    case "PASS":
    case "PASSED":
    case "COMPLIANT":
    case "COMPLIANCE_PASS":
    case "VALID":
    case "VALID_CERTIFICATE":
    case "NO_EXPIRY":
    case "PERMANENT":
    case "VERIFIED":
    case "PROFILE_VERIFIED":
    case "UPLOADED":
    case "DOCUMENT_UPLOADED":
    case "SUBMITTED":
    case "QUALITY_CHECK_COMPLETE":
    case "QUALITY_CHECKED":
    case "EXTRACTION_COMPLETE":
    case "DATA_EXTRACTED":
    case "TEXT_EXTRACTED":
    case "FIELDS_EXTRACTED":
    case "PROCESSING_COMPLETE":
    case "COMPLETE":
    case "COMPLETED":
    case "EVALUATION_COMPLETE":
    case "RESOLVED":
    case "CLARIFICATION_RESOLVED":
    case "QUALIFIED":
    case "AWARDED":
    case "MATCH":
    case "EXACT":
    case "EXACT_MATCH":
    case "GOOD":
    case "SUCCESS":
    case "CONFIRMED_BENIGN":
    case "CLEAN":
    case "PROCEED":
      colorClasses = "bg-emerald-50 text-emerald-800 border-emerald-200";
      IconComponent = CheckCircle2;
      if (normStatus === "PROFILE_VERIFIED") defaultLabel = "Profile Verified";
      if (normStatus === "DOCUMENT_UPLOADED") defaultLabel = "Document Uploaded";
      if (normStatus === "QUALITY_CHECKED" || normStatus === "QUALITY_CHECK_COMPLETE")
        defaultLabel = "Quality Checked";
      if (normStatus === "DATA_EXTRACTED" || normStatus === "EXTRACTION_COMPLETE")
        defaultLabel = "Data Extracted";
      if (normStatus === "COMPLIANCE_PASS") defaultLabel = "Compliance PASS";
      if (normStatus === "CLARIFICATION_RESOLVED") defaultLabel = "Clarification Resolved";
      break;

    // ==========================================
    // ! ALERT / WARNING / REVIEW REQUIRED STATES
    // ==========================================
    case "REVIEW":
    case "REVIEW_REQUIRED":
    case "NEEDS_REVIEW":
    case "EXPIRING_SOON":
    case "WARNING":
    case "PARTIAL":
    case "PARTIAL_MATCH":
    case "PARTIALLY_COMPLETED":
    case "ACTION_REQUIRED":
    case "INCOMPLETE":
    case "INCOMPLETE_PROFILE":
    case "POOR":
    case "ACCEPTABLE":
    case "LOW_SCAN_QUALITY":
    case "PROCEED_WITH_REVIEW":
    case "HIGH":
    case "HIGH_RISK":
    case "CRITICAL_RISK":
    case "ESCALATED":
    case "AI_STALE":
      colorClasses = "bg-amber-50 text-amber-900 border-amber-200";
      IconComponent = AlertTriangle;
      if (normStatus === "REVIEW_REQUIRED" || normStatus === "NEEDS_REVIEW")
        defaultLabel = "Review Required";
      if (normStatus === "EXPIRING_SOON") defaultLabel = "Expiring Soon";
      if (normStatus === "PARTIAL_MATCH" || normStatus === "PARTIAL")
        defaultLabel = "Partial Match";
      break;

    // ==========================================
    // ○ CLOCK / PENDING / PROCESSING / DRAFT STATES
    // ==========================================
    case "PENDING":
    case "VERIFICATION_PENDING":
    case "PROCESSING":
    case "RUNNING":
    case "QUEUED":
    case "AWAITING_REVIEW":
    case "AWAITING_BIDDER":
    case "IN_REVIEW":
    case "UNDER_REVIEW":
    case "UNDER_EVALUATION":
    case "DRAFT":
    case "DRAFTING":
    case "OPEN":
    case "PUBLISHED":
    case "RESPONDED":
    case "PROVISIONAL":
    case "NOT_STARTED":
    case "UNAVAILABLE":
      colorClasses = "bg-slate-100 text-slate-700 border-slate-300";
      IconComponent = Clock;
      if (normStatus === "VERIFICATION_PENDING") defaultLabel = "Verification Pending";
      if (normStatus === "AWAITING_REVIEW") defaultLabel = "Awaiting Review";
      if (normStatus === "AWAITING_BIDDER") defaultLabel = "Awaiting Bidder";
      break;

    // ==========================================
    // × X / FAIL / EXPIRED / MISMATCH STATES
    // ==========================================
    case "FAIL":
    case "FAILED":
    case "COMPLIANCE_FAIL":
    case "NON_COMPLIANT":
    case "CRITICAL_FAIL":
    case "DISQUALIFIED":
    case "EXPIRED":
    case "MISMATCH":
    case "VERIFICATION_MISMATCH":
    case "NOT_VERIFIED":
    case "UNUSABLE":
    case "CORRUPTED":
    case "PASSWORD_PROTECTED":
    case "CANCELLED":
    case "CONFIRMED_REUSE":
    case "DO_NOT_PROCEED":
    case "CLOSED":
    case "ARCHIVED":
    case "SUPERSEDED":
      colorClasses = "bg-rose-50 text-rose-800 border-rose-200";
      IconComponent = XCircle;
      if (normStatus === "COMPLIANCE_FAIL" || normStatus === "FAIL")
        defaultLabel = "Compliance Failed";
      if (normStatus === "VERIFICATION_MISMATCH" || normStatus === "MISMATCH")
        defaultLabel = "Verification Mismatch";
      if (normStatus === "NOT_VERIFIED") defaultLabel = "Not Verified";
      break;

    case "NOT_APPLICABLE":
    case "N/A":
    case "NA":
      colorClasses = "bg-slate-100 text-slate-600 border-slate-200";
      IconComponent = MinusCircle;
      defaultLabel = "N/A";
      break;

    default:
      colorClasses = "bg-slate-100 text-slate-700 border-slate-200";
      IconComponent = CircleDot;
  }

  const sizeClasses =
    size === "sm"
      ? "px-2 py-0.5 text-[10px]"
      : size === "lg"
      ? "px-3 py-1 text-xs"
      : "px-2.5 py-0.5 text-[11px]";

  const displayLabel = customLabel || defaultLabel;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border font-bold uppercase tracking-wide shrink-0 ${sizeClasses} ${colorClasses} ${className}`}
    >
      {showIcon && IconComponent && <IconComponent className="h-3 w-3 shrink-0" />}
      <span>{displayLabel}</span>
    </span>
  );
}
