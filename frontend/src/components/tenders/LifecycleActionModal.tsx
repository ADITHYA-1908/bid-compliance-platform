"use client";

import React, { useState } from "react";
import {
  Send,
  Unlock,
  Lock,
  SearchCheck,
  Trophy,
  Archive,
  AlertTriangle,
  Info,
} from "lucide-react";

export type LifecycleAction =
  | "PUBLISHED"
  | "OPEN"
  | "CLOSED"
  | "UNDER_EVALUATION"
  | "AWARDED"
  | "ARCHIVED";

interface LifecycleActionModalProps {
  isOpen: boolean;
  targetStatus: LifecycleAction | null;
  tenderNumber: string;
  tenderTitle: string;
  isSubmitting: boolean;
  serverError: string | null;
  onConfirm: (targetStatus: LifecycleAction, remarks?: string) => Promise<void>;
  onClose: () => void;
}

export function LifecycleActionModal({
  isOpen,
  targetStatus,
  tenderNumber,
  tenderTitle,
  isSubmitting,
  serverError,
  onConfirm,
  onClose,
}: LifecycleActionModalProps) {
  const [remarks, setRemarks] = useState("");

  if (!isOpen || !targetStatus) return null;

  let title = "Confirm Status Change";
  let description = "Are you sure you want to transition this tender?";
  let warning = "";
  let confirmLabel = "Confirm Transition";
  let confirmStyle = "bg-purple-900 hover:bg-purple-800 text-white";
  let Icon = Info;
  let iconStyle = "bg-purple-100 text-purple-900";

  switch (targetStatus) {
    case "PUBLISHED":
      title = "Publish Tender Opportunity?";
      description = `Publishing will make tender "${tenderNumber}" visible and prepare it for open bidding.`;
      warning =
        "Important: Ensure all eligibility and technical criteria are configured. Requirements cannot be altered once bidding begins.";
      confirmLabel = isSubmitting ? "Publishing..." : "Publish Tender";
      confirmStyle = "bg-blue-700 hover:bg-blue-800 text-white";
      Icon = Send;
      iconStyle = "bg-blue-100 text-blue-800";
      break;

    case "OPEN":
      title = "Open Tender for Public Bidding?";
      description = `This will open tender "${tenderNumber}" for active bidder submissions.`;
      warning =
        "Notice: Once opened, eligibility rules and core tender parameters are permanently locked.";
      confirmLabel = isSubmitting ? "Opening..." : "Open for Bidding";
      confirmStyle = "bg-emerald-700 hover:bg-emerald-800 text-white";
      Icon = Unlock;
      iconStyle = "bg-emerald-100 text-emerald-800";
      break;

    case "CLOSED":
      title = "Close Bid Submission Window?";
      description = `This will officially close tender "${tenderNumber}" to all future bid submissions.`;
      warning = "Notice: Bidders will no longer be able to upload or modify bids.";
      confirmLabel = isSubmitting ? "Closing..." : "Close Tender";
      confirmStyle = "bg-amber-700 hover:bg-amber-800 text-white";
      Icon = Lock;
      iconStyle = "bg-amber-100 text-amber-800";
      break;

    case "UNDER_EVALUATION":
      title = "Start Compliance Evaluation?";
      description = `This will move tender "${tenderNumber}" into the bid evaluation stage.`;
      warning =
        "Procurement officers and the AI compliance engine will begin inspecting submitted tender bids.";
      confirmLabel = isSubmitting ? "Starting Evaluation..." : "Start Evaluation";
      confirmStyle = "bg-purple-800 hover:bg-purple-900 text-white";
      Icon = SearchCheck;
      iconStyle = "bg-purple-100 text-purple-900";
      break;

    case "AWARDED":
      title = "Award Procurement Contract?";
      description = `This will mark tender "${tenderNumber}" as officially awarded.`;
      warning =
        "Awarding finalizes the procurement decision for this opportunity.";
      confirmLabel = isSubmitting ? "Awarding..." : "Award Tender";
      confirmStyle = "bg-indigo-700 hover:bg-indigo-800 text-white";
      Icon = Trophy;
      iconStyle = "bg-indigo-100 text-indigo-800";
      break;

    case "ARCHIVED":
      title = "Archive Tender Opportunity?";
      description = `Archiving tender "${tenderNumber}" will soft-delete it and make it strictly read-only.`;
      warning =
        "Caution: Archived tenders cannot be restored to active lifecycle states.";
      confirmLabel = isSubmitting ? "Archiving..." : "Archive Tender";
      confirmStyle = "bg-rose-700 hover:bg-rose-800 text-white";
      Icon = Archive;
      iconStyle = "bg-rose-100 text-rose-800";
      break;
  }

  const handleConfirm = async () => {
    await onConfirm(targetStatus, remarks.trim() || undefined);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-0">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
        onClick={() => !isSubmitting && onClose()}
      />

      {/* Modal Dialog */}
      <div className="relative transform overflow-hidden rounded-xl bg-white text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-lg border border-slate-200">
        <div className="p-6 space-y-4">
          <div className="flex items-start gap-3.5">
            <div
              className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${iconStyle}`}
            >
              <Icon className="h-5 w-5" />
            </div>

            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-900">{title}</h3>
              <p className="text-xs text-slate-600 leading-relaxed">{description}</p>
            </div>
          </div>

          <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 text-xs">
            <span className="text-[11px] font-semibold text-slate-500 block">Tender Details:</span>
            <span className="font-mono font-bold text-slate-900 mr-2">{tenderNumber}</span>
            <span className="text-slate-700">{tenderTitle}</span>
          </div>

          {warning && (
            <div className="flex items-start gap-2 rounded-lg bg-amber-50/80 p-3 border border-amber-200 text-xs text-amber-900">
              <AlertTriangle className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" />
              <span>{warning}</span>
            </div>
          )}

          {serverError && (
            <div className="rounded-lg bg-rose-50 p-3 border border-rose-200 text-xs text-rose-800 font-medium">
              {serverError}
            </div>
          )}

          {/* Optional remarks */}
          <div className="space-y-1.5 pt-1">
            <label
              htmlFor="transition-remarks"
              className="text-xs font-semibold text-slate-700 block"
            >
              Officer Remarks / Notes <span className="text-slate-400 font-normal">(Optional)</span>
            </label>
            <input
              id="transition-remarks"
              type="text"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="e.g. Approved by Procurement Committee..."
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs text-slate-900 shadow-2xs focus:border-purple-600 focus:ring-1 focus:ring-purple-600 outline-none"
              disabled={isSubmitting}
            />
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-2.5 border-t border-slate-100 bg-slate-50/75 px-6 py-3.5">
          <button
            type="button"
            disabled={isSubmitting}
            onClick={onClose}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 disabled:opacity-50 transition-colors cursor-pointer"
          >
            Cancel
          </button>

          <button
            type="button"
            disabled={isSubmitting}
            onClick={handleConfirm}
            className={`rounded-lg px-4 py-2 text-xs font-semibold shadow-xs disabled:opacity-50 transition-colors cursor-pointer ${confirmStyle}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
