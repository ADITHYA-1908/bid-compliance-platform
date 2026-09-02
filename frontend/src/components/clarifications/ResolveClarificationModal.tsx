"use client";

import React, { useState } from "react";
import {
  X,
  CheckCircle2,
  RefreshCw,
  AlertTriangle,
  FileCheck,
  ShieldCheck,
} from "lucide-react";
import { ClarificationResolveRequest } from "@/types/clarification";
import { procurementClarificationsApi } from "@/lib/api/clarifications";

interface ResolveClarificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  clarificationId: string;
  subject: string;
  bidderName?: string;
  bidNumber?: string;
  token?: string;
}

export const ResolveClarificationModal: React.FC<ResolveClarificationModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  clarificationId,
  subject,
  bidderName,
  bidNumber,
  token,
}) => {
  const [resolutionNote, setResolutionNote] = useState("");
  const [triggerReevaluation, setTriggerReevaluation] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolutionNote.trim()) {
      setErrorMsg("Please enter an auditable resolution note.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const payload: ClarificationResolveRequest = {
        resolution_note: resolutionNote.trim(),
        trigger_reevaluation: triggerReevaluation,
      };

      await procurementClarificationsApi.resolveClarification(clarificationId, payload, token);

      if (onSuccess) {
        onSuccess();
      }
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to resolve clarification request");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="relative w-full max-w-xl rounded-2xl bg-white shadow-2xl border border-slate-200 overflow-hidden my-6">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 bg-gradient-to-r from-emerald-950 via-slate-900 to-emerald-950 px-6 py-4 text-white">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-emerald-500/20 border border-emerald-400/30 p-2.5 text-emerald-300">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold">Resolve Clarification</h3>
              <p className="text-xs text-emerald-200/80">
                {bidNumber ? `Bid ${bidNumber}` : ""} {bidderName ? `• ${bidderName}` : ""}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMsg && (
            <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="rounded-xl bg-slate-50 border border-slate-200 p-3.5 text-xs text-slate-700">
            <span className="font-semibold text-slate-500">Subject:</span>
            <div className="font-bold text-slate-900 mt-0.5">{subject}</div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Auditable Resolution Finding / Note <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={4}
              value={resolutionNote}
              onChange={(e) => setResolutionNote(e.target.value)}
              placeholder="State the officer findings upon reviewing the bidder's explanation and submitted evidence (e.g., 'Replacement GST certificate verified and matches registration state requirement. Discrepancy resolved.')..."
              className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-emerald-500 focus:outline-hidden focus:ring-2 focus:ring-emerald-500/20 resize-y"
              required
            />
          </div>

          {/* Trigger Re-evaluation Checkbox */}
          <div className="rounded-xl bg-emerald-50/60 border border-emerald-200/60 p-4">
            <label className="relative flex items-start gap-3 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={triggerReevaluation}
                onChange={(e) => setTriggerReevaluation(e.target.checked)}
                className="h-4 w-4 mt-0.5 rounded border-emerald-300 text-emerald-600 focus:ring-emerald-500"
              />
              <div className="text-xs">
                <span className="font-bold text-emerald-950 block">
                  Re-evaluate Compliance & Scoring Engine
                </span>
                <span className="text-emerald-800/80 leading-relaxed block mt-0.5">
                  Runs the deterministic evaluation pipeline using the latest active evidence. (Strict non-self-approval: final human verdict remains independent).
                </span>
              </div>
            </label>
          </div>

          {/* Footer Controls */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-2.5 text-xs font-bold text-white shadow-md hover:from-emerald-700 hover:to-teal-700 transition-all disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Resolving...
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  Confirm & Resolve Clarification
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
