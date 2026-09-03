import React from "react";
import { CheckCircle2, XCircle, AlertCircle, Clock, ShieldCheck, ShieldAlert } from "lucide-react";

export type StatusType =
  | "PASS"
  | "FAIL"
  | "REVIEW"
  | "PENDING"
  | "VALID"
  | "EXPIRING_SOON"
  | "EXPIRED"
  | "GOOD"
  | "ACCEPTABLE"
  | "POOR"
  | "UNUSABLE"
  | "QUALIFIED"
  | "DISQUALIFIED"
  | "UNDER_REVIEW"
  | "DRAFT"
  | "PUBLISHED"
  | "OPEN"
  | "CLOSED"
  | "UNDER_EVALUATION"
  | "AWARDED"
  | "ARCHIVED"
  | "SUBMITTED";

interface StatusBadgeProps {
  status: StatusType | string;
  size?: "sm" | "md" | "lg";
  className?: string;
  showIcon?: boolean;
}

export function StatusBadge({
  status,
  size = "md",
  className = "",
  showIcon = true,
}: StatusBadgeProps) {
  const normStatus = (status || "").toUpperCase();

  let colorClasses = "bg-slate-100 text-slate-700 border-slate-200";
  let IconComponent: React.ElementType | null = Clock;
  const label = normStatus.replace(/_/g, " ");

  switch (normStatus) {
    // Compliant / Valid / Pass / Qualified / Awarded
    case "PASS":
    case "VALID":
    case "GOOD":
    case "QUALIFIED":
    case "AWARDED":
    case "COMPLIANT":
      colorClasses = "bg-emerald-50 text-emerald-800 border-emerald-200";
      IconComponent = CheckCircle2;
      break;

    // Fail / Expired / Disqualified / Non-Compliant
    case "FAIL":
    case "EXPIRED":
    case "POOR":
    case "UNUSABLE":
    case "DISQUALIFIED":
    case "NON_COMPLIANT":
      colorClasses = "bg-red-50 text-red-800 border-red-200";
      IconComponent = XCircle;
      break;

    // Review Required / Expiring Soon / Under Review
    case "REVIEW":
    case "REVIEW_REQUIRED":
    case "EXPIRING_SOON":
    case "ACCEPTABLE":
    case "UNDER_REVIEW":
      colorClasses = "bg-amber-50 text-amber-900 border-amber-200";
      IconComponent = AlertCircle;
      break;

    // Open / Published / Submitted
    case "OPEN":
    case "PUBLISHED":
    case "SUBMITTED":
      colorClasses = "bg-blue-50 text-blue-900 border-blue-200";
      IconComponent = ShieldCheck;
      break;

    // Pending / Processing / Under Evaluation / Draft
    case "PENDING":
    case "PROCESSING":
    case "UNDER_EVALUATION":
    case "DRAFT":
      colorClasses = "bg-slate-100 text-slate-700 border-slate-300";
      IconComponent = Clock;
      break;

    // Closed / Archived
    case "CLOSED":
    case "ARCHIVED":
      colorClasses = "bg-slate-100 text-slate-600 border-slate-200";
      IconComponent = ShieldAlert;
      break;

    default:
      colorClasses = "bg-slate-100 text-slate-700 border-slate-200";
      IconComponent = null;
  }

  const sizeClasses =
    size === "sm"
      ? "px-2 py-0.5 text-[10px]"
      : size === "lg"
      ? "px-3 py-1 text-xs"
      : "px-2.5 py-0.5 text-[11px]";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border font-bold uppercase tracking-wide ${sizeClasses} ${colorClasses} ${className}`}
    >
      {showIcon && IconComponent && <IconComponent className="h-3 w-3 shrink-0" />}
      <span>{label}</span>
    </span>
  );
}
