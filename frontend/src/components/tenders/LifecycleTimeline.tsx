"use client";

import React from "react";
import { formatDateTime } from "@/lib/formatters";
import {
  FileText,
  Send,
  Unlock,
  Lock,
  SearchCheck,
  Trophy,
  Archive,
  Check,
  Clock,
} from "lucide-react";

interface LifecycleTimelineProps {
  status: string;
  isActive: boolean;
  publishedAt?: string | null;
  openedAt?: string | null;
  closedAt?: string | null;
  evaluationStartedAt?: string | null;
  awardedAt?: string | null;
  archivedAt?: string | null;
  createdAt?: string | null;
}

interface StepConfig {
  key: string;
  label: string;
  shortLabel: string;
  icon: React.ComponentType<{ className?: string }>;
  timestampKey?: string;
  timestampValue?: string | null;
}

export function LifecycleTimeline({
  status,
  isActive,
  publishedAt,
  openedAt,
  closedAt,
  evaluationStartedAt,
  awardedAt,
  archivedAt,
  createdAt,
}: LifecycleTimelineProps) {
  const normalizedStatus = (status || "DRAFT").toUpperCase();
  const isArchived = !isActive || normalizedStatus === "ARCHIVED";

  const steps: StepConfig[] = [
    {
      key: "DRAFT",
      label: "Draft Preparation",
      shortLabel: "Draft",
      icon: FileText,
      timestampValue: createdAt,
    },
    {
      key: "PUBLISHED",
      label: "Published",
      shortLabel: "Published",
      icon: Send,
      timestampValue: publishedAt,
    },
    {
      key: "OPEN",
      label: "Open for Bidding",
      shortLabel: "Open",
      icon: Unlock,
      timestampValue: openedAt,
    },
    {
      key: "CLOSED",
      label: "Bidding Closed",
      shortLabel: "Closed",
      icon: Lock,
      timestampValue: closedAt,
    },
    {
      key: "UNDER_EVALUATION",
      label: "Under Evaluation",
      shortLabel: "Evaluation",
      icon: SearchCheck,
      timestampValue: evaluationStartedAt,
    },
    {
      key: "AWARDED",
      label: "Contract Awarded",
      shortLabel: "Awarded",
      icon: Trophy,
      timestampValue: awardedAt,
    },
  ];

  const statusOrder = [
    "DRAFT",
    "PUBLISHED",
    "OPEN",
    "CLOSED",
    "UNDER_EVALUATION",
    "AWARDED",
  ];

  const currentIdx = statusOrder.indexOf(normalizedStatus);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-purple-900" />
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            Tender Lifecycle State Progression
          </h3>
        </div>

        {isArchived && (
          <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2.5 py-1 text-[11px] font-bold text-rose-700 border border-rose-200">
            <Archive className="h-3.5 w-3.5" />
            Tender Archived (Immutable)
          </span>
        )}
      </div>

      {/* Stepper Timeline */}
      <div className="overflow-x-auto pb-2">
        <div className="min-w-[600px] flex items-center justify-between relative">
          {/* Connector Line behind steps */}
          <div className="absolute top-4 left-6 right-6 h-0.5 bg-slate-200 -z-0" />

          {steps.map((step, idx) => {
            const isCompleted = currentIdx > idx;
            const isCurrent = currentIdx === idx && !isArchived;
            const isPending = currentIdx < idx;
            const Icon = step.icon;

            let circleClass = "bg-slate-100 text-slate-400 border-slate-300";
            let textClass = "text-slate-400";

            if (isCompleted) {
              circleClass = "bg-emerald-600 text-white border-emerald-600 shadow-xs";
              textClass = "text-slate-800 font-semibold";
            } else if (isCurrent) {
              circleClass =
                "bg-purple-900 text-white border-purple-900 ring-4 ring-purple-100 shadow-xs animate-pulse";
              textClass = "text-purple-950 font-bold";
            }

            return (
              <div
                key={step.key}
                className="flex flex-col items-center text-center relative z-10 w-24 group"
              >
                {/* Step Circle */}
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full border-2 transition-all ${circleClass}`}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4 stroke-[3]" />
                  ) : (
                    <Icon className="h-3.5 w-3.5" />
                  )}
                </div>

                {/* Step Label */}
                <span className={`text-[11px] mt-2 block ${textClass}`}>
                  {step.shortLabel}
                </span>

                {/* Step Timestamp */}
                {step.timestampValue ? (
                  <span className="text-[9px] font-mono text-slate-500 mt-0.5 truncate max-w-[90px]">
                    {formatDateTime(step.timestampValue).split(",")[0]}
                  </span>
                ) : isCurrent ? (
                  <span className="text-[9px] font-bold text-purple-700 mt-0.5">
                    Active Stage
                  </span>
                ) : (
                  <span className="text-[9px] text-slate-300 mt-0.5">—</span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
