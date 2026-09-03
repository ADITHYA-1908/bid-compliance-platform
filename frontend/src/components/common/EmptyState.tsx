import React from "react";
import { LucideIcon, Inbox } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div className={`text-center py-12 px-4 rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 ${className}`}>
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-white border border-slate-200 text-slate-400 shadow-xs mb-3">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="font-heading text-sm font-bold text-slate-900 tracking-tight">
        {title}
      </h3>
      <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
        {description}
      </p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
