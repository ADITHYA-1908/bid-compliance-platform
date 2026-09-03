import React from "react";
import { Sparkles } from "lucide-react";

interface ConfidenceBadgeProps {
  score?: number | null;
  className?: string;
  showIcon?: boolean;
}

export function ConfidenceBadge({
  score,
  className = "",
  showIcon = true,
}: ConfidenceBadgeProps) {
  if (score === null || score === undefined) {
    return (
      <span className={`inline-flex items-center rounded-full bg-slate-100 border border-slate-200 px-2 py-0.5 text-[10px] font-mono font-bold text-slate-500 ${className}`}>
        N/A
      </span>
    );
  }

  const percentage = score <= 1 ? Math.round(score * 100) : Math.round(score);

  let colorClasses = "bg-red-50 text-red-800 border-red-200";
  if (percentage >= 90) {
    colorClasses = "bg-emerald-50 text-emerald-800 border-emerald-200";
  } else if (percentage >= 70) {
    colorClasses = "bg-amber-50 text-amber-800 border-amber-200";
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-mono-score font-bold shadow-2xs ${colorClasses} ${className}`}
      title={`AI Extraction Confidence: ${percentage}%`}
    >
      {showIcon && <Sparkles className="h-2.5 w-2.5 shrink-0" />}
      <span>{percentage}%</span>
    </span>
  );
}
