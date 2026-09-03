import React from "react";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  subtitle?: React.ReactNode;
  variant?: "emerald" | "blue" | "purple" | "amber" | "rose" | "slate";
  trend?: string;
  className?: string;
  onClick?: () => void;
}

export function StatCard({
  label,
  value,
  icon: Icon,
  subtitle,
  variant = "slate",
  trend,
  className = "",
  onClick,
}: StatCardProps) {
  let iconBg = "bg-slate-100 text-slate-700 border-slate-200";

  switch (variant) {
    case "emerald":
      iconBg = "bg-emerald-50 text-emerald-800 border-emerald-200";
      break;
    case "blue":
      iconBg = "bg-blue-50 text-blue-800 border-blue-200";
      break;
    case "purple":
      iconBg = "bg-purple-50 text-purple-800 border-purple-200";
      break;
    case "amber":
      iconBg = "bg-amber-50 text-amber-900 border-amber-200";
      break;
    case "rose":
      iconBg = "bg-red-50 text-red-800 border-red-200";
      break;
  }

  return (
    <div
      onClick={onClick}
      className={`card-formal p-5 border border-slate-200 bg-white ${
        onClick ? "cursor-pointer hover:border-slate-300" : ""
      } ${className}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
          {label}
        </span>
        <div className={`flex h-7 w-7 items-center justify-center rounded-lg border ${iconBg}`}>
          <Icon className="h-3.5 w-3.5" />
        </div>
      </div>

      <div className="mt-2 flex items-baseline gap-2">
        <p className="font-mono-score text-2xl sm:text-3xl font-bold text-slate-900">
          {value}
        </p>
        {trend && (
          <span className="text-[11px] font-semibold text-slate-500">
            {trend}
          </span>
        )}
      </div>

      {subtitle && (
        <div className="mt-1 text-xs text-slate-500">
          {subtitle}
        </div>
      )}
    </div>
  );
}
