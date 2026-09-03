import React from "react";
import { ShieldCheck, ShieldAlert, AlertTriangle, AlertOctagon } from "lucide-react";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

interface RiskBadgeProps {
  level: RiskLevel | string;
  score?: number | null;
  className?: string;
  showIcon?: boolean;
}

export function RiskBadge({
  level,
  score,
  className = "",
  showIcon = true,
}: RiskBadgeProps) {
  const normLevel = (level || "LOW").toUpperCase();

  let colorClasses = "bg-emerald-50 text-emerald-800 border-emerald-200";
  let IconComponent = ShieldCheck;

  switch (normLevel) {
    case "CRITICAL":
      colorClasses = "bg-rose-100 text-rose-900 border-rose-300";
      IconComponent = AlertOctagon;
      break;
    case "HIGH":
      colorClasses = "bg-red-50 text-red-800 border-red-200";
      IconComponent = ShieldAlert;
      break;
    case "MEDIUM":
      colorClasses = "bg-amber-50 text-amber-800 border-amber-200";
      IconComponent = AlertTriangle;
      break;
    case "LOW":
    default:
      colorClasses = "bg-emerald-50 text-emerald-800 border-emerald-200";
      IconComponent = ShieldCheck;
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider font-heading shadow-2xs ${colorClasses} ${className}`}
    >
      {showIcon && <IconComponent className="h-3 w-3 shrink-0" />}
      <span>{normLevel} RISK</span>
      {score !== undefined && score !== null && (
        <span className="font-mono-score text-[9px] opacity-80">({score})</span>
      )}
    </span>
  );
}
