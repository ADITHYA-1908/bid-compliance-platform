"use client";

import React from "react";
import { CheckCircle2, Clock, AlertTriangle, XCircle } from "lucide-react";

interface TenderStatusBadgeProps {
  status: string;
  className?: string;
  size?: "sm" | "md";
}

export function TenderStatusBadge({
  status,
  className = "",
  size = "md",
}: TenderStatusBadgeProps) {
  const normalizedStatus = (status || "DRAFT").toUpperCase();

  let badgeStyle = "bg-slate-100 text-slate-800 border-slate-300";
  let IconComponent: React.ElementType = Clock;
  let label = normalizedStatus;

  switch (normalizedStatus) {
    case "DRAFT":
      badgeStyle = "bg-slate-100 text-slate-700 border-slate-300";
      IconComponent = Clock;
      label = "Draft";
      break;
    case "PUBLISHED":
      badgeStyle = "bg-blue-50 text-blue-800 border-blue-200";
      IconComponent = CheckCircle2;
      label = "Published";
      break;
    case "OPEN":
      badgeStyle = "bg-emerald-50 text-emerald-800 border-emerald-200";
      IconComponent = CheckCircle2;
      label = "Open for Bidding";
      break;
    case "CLOSED":
      badgeStyle = "bg-amber-50 text-amber-800 border-amber-200";
      IconComponent = AlertTriangle;
      label = "Closed";
      break;
    case "UNDER_EVALUATION":
      badgeStyle = "bg-purple-50 text-purple-800 border-purple-200";
      IconComponent = Clock;
      label = "Under Evaluation";
      break;
    case "AWARDED":
      badgeStyle = "bg-indigo-50 text-indigo-800 border-indigo-200";
      IconComponent = CheckCircle2;
      label = "Awarded";
      break;
    case "ARCHIVED":
      badgeStyle = "bg-rose-50 text-rose-800 border-rose-200";
      IconComponent = XCircle;
      label = "Archived";
      break;
    default:
      label = normalizedStatus.replace(/_/g, " ");
      IconComponent = Clock;
  }

  const sizeClasses =
    size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-0.5 text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold tracking-wide shrink-0 ${sizeClasses} ${badgeStyle} ${className}`}
    >
      <IconComponent className="h-3 w-3 shrink-0" />
      <span>{label}</span>
    </span>
  );
}
