"use client";

import React from "react";

interface TenderStatusBadgeProps {
  status: string;
  className?: string;
}

export function TenderStatusBadge({ status, className = "" }: TenderStatusBadgeProps) {
  const normalizedStatus = (status || "DRAFT").toUpperCase();

  let badgeStyle = "bg-slate-100 text-slate-800 border-slate-300";
  let dotColor = "bg-slate-500";
  let label = normalizedStatus;

  switch (normalizedStatus) {
    case "DRAFT":
      badgeStyle = "bg-slate-100 text-slate-700 border-slate-300";
      dotColor = "bg-slate-500";
      label = "Draft";
      break;
    case "PUBLISHED":
      badgeStyle = "bg-blue-50 text-blue-800 border-blue-200";
      dotColor = "bg-blue-600";
      label = "Published";
      break;
    case "OPEN":
      badgeStyle = "bg-emerald-50 text-emerald-800 border-emerald-200";
      dotColor = "bg-emerald-600 animate-pulse";
      label = "Open for Bidding";
      break;
    case "CLOSED":
      badgeStyle = "bg-amber-50 text-amber-800 border-amber-200";
      dotColor = "bg-amber-600";
      label = "Closed";
      break;
    case "UNDER_EVALUATION":
      badgeStyle = "bg-purple-50 text-purple-800 border-purple-200";
      dotColor = "bg-purple-600";
      label = "Under Evaluation";
      break;
    case "AWARDED":
      badgeStyle = "bg-indigo-50 text-indigo-800 border-indigo-200";
      dotColor = "bg-indigo-600";
      label = "Awarded";
      break;
    case "ARCHIVED":
      badgeStyle = "bg-rose-50 text-rose-800 border-rose-200";
      dotColor = "bg-rose-600";
      label = "Archived";
      break;
    default:
      label = normalizedStatus;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide ${badgeStyle} ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dotColor}`} />
      {label}
    </span>
  );
}
