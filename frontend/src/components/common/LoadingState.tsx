import React from "react";
import { Loader2 } from "lucide-react";

interface LoadingStateProps {
  label?: string;
  className?: string;
}

export function LoadingState({
  label = "Loading data...",
  className = "",
}: LoadingStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-12 px-4 ${className}`}>
      <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 border border-emerald-200 shadow-2xs mb-3">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
      <p className="font-heading text-xs font-bold text-slate-700 tracking-wide">
        {label}
      </p>
    </div>
  );
}
