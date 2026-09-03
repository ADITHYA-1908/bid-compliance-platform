import React from "react";
import { LucideIcon } from "lucide-react";

interface SectionCardProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  badge?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  headerClassName?: string;
}

export function SectionCard({
  title,
  description,
  icon: Icon,
  badge,
  action,
  children,
  className = "",
  headerClassName = "",
}: SectionCardProps) {
  return (
    <div className={`card-formal overflow-hidden bg-white border border-slate-200 ${className}`}>
      {/* Header */}
      <div className={`border-b border-slate-200 p-4 sm:px-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50 ${headerClassName}`}>
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white border border-slate-200 text-slate-800 shadow-2xs">
              <Icon className="h-4 w-4 text-slate-700" />
            </div>
          )}
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm sm:text-base font-bold text-slate-900 tracking-tight">
                {title}
              </h3>
              {badge}
            </div>
            {description && (
              <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                {description}
              </p>
            )}
          </div>
        </div>

        {action && <div className="shrink-0 flex items-center gap-2">{action}</div>}
      </div>

      {/* Body */}
      <div className="p-4 sm:p-6">{children}</div>
    </div>
  );
}
