"use client";

import React from "react";

interface TenderStatusBadgeProps {
  status: string;
  className?: string;
}

export function TenderStatusBadge({ status, className = "" }: TenderStatusBadgeProps) {
  const normalizedStatus = (status || "DRAFT").toUpperCase();

  let badgeStyle = "bg-slate-800/70 text-slate-300 border-slate-700";
  let dotColor = "bg-slate-400";
  let label = normalizedStatus;

  switch (normalizedStatus) {
    case "DRAFT":
      badgeStyle = "bg-slate-800/70 text-slate-300 border-slate-700";
      dotColor = "bg-slate-400";
      label = "Draft";
      break;
    case "PUBLISHED":
      badgeStyle = "bg-blue-950/70 text-blue-300 border-blue-700/50";
      dotColor = "bg-blue-400";
      label = "Published";
      break;
    case "OPEN":
      badgeStyle = "bg-emerald-950/70 text-emerald-300 border-emerald-700/50";
      dotColor = "bg-emerald-400 animate-pulse";
      label = "Open for Bidding";
      break;
    case "CLOSED":
      badgeStyle = "bg-amber-950/70 text-amber-300 border-amber-700/50";
      dotColor = "bg-amber-400";
      label = "Closed";
      break;
    case "UNDER_EVALUATION":
      badgeStyle = "bg-purple-950/70 text-purple-300 border-purple-700/50";
      dotColor = "bg-purple-400";
      label = "Under Evaluation";
      break;
    case "AWARDED":
      badgeStyle = "bg-indigo-950/70 text-indigo-300 border-indigo-700/50";
      dotColor = "bg-indigo-400";
      label = "Awarded";
      break;
    case "ARCHIVED":
      badgeStyle = "bg-rose-950/70 text-rose-300 border-rose-700/50";
      dotColor = "bg-rose-400";
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
