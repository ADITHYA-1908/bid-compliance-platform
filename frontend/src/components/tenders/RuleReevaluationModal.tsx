"use client";

import React, { useState } from "react";
import { ReevaluationResultResponse } from "@/types/rule_versions";
import { ruleVersionsApi } from "@/lib/api/rule_versions";
import {
  RefreshCw,
  X,
  AlertCircle,
  CheckCircle2,
  ShieldCheck,
  AlertTriangle,
  UserCheck,
  ArrowRight,
} from "lucide-react";

interface RuleReevaluationModalProps {
  isOpen: boolean;
  onClose: () => void;
  tenderId: string;
  tenderNumber: string;
  requirementId?: string;
  requirementCode?: string;
  onSuccess?: () => void;
}

export function RuleReevaluationModal({
  isOpen,
  onClose,
  tenderId,
  tenderNumber,
  requirementId,
  requirementCode,
  onSuccess,
}: RuleReevaluationModalProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<ReevaluationResultResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleTriggerReevaluation = async () => {
    setIsProcessing(true);
    setError(null);
    try {
      let res: ReevaluationResultResponse;
      if (requirementId) {
        res = await ruleVersionsApi.reevaluateRequirementBids(tenderId, requirementId);
      } else {
        res = await ruleVersionsApi.reevaluateAllTenderRules(tenderId);
      }
      setResult(res);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err?.message || "Failed to trigger re-evaluation.");
    } finally {
      setIsProcessing(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PASS":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">PASS</span>;
      case "FAIL":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">FAIL</span>;
      case "REVIEW":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">REVIEW</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700">{status}</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl max-h-[90vh] flex flex-col bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-100 text-purple-700">
              <RefreshCw className={`w-5 h-5 ${isProcessing ? "animate-spin" : ""}`} />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                {requirementCode
                  ? `Re-evaluate Bids for Rule [${requirementCode}]`
                  : "Re-evaluate All Tender Compliance Rules"}
              </h3>
              <p className="text-xs text-slate-500">
                Tender: <strong className="text-slate-700 font-mono">{tenderNumber}</strong>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!result ? (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-purple-50/50 border border-purple-200 text-xs text-purple-900 space-y-2">
                <h4 className="font-bold flex items-center gap-1.5 text-purple-950">
                  <ShieldCheck className="w-4 h-4 text-purple-700" />
                  Deterministic Re-evaluation Safeguards
                </h4>
                <ul className="list-disc list-inside space-y-1 text-purple-800">
                  <li>Runs compliance engine against latest active rule versions.</li>
                  <li>Recomputes weighted score snapshots and deterministic risk assessments.</li>
                  <li>
                    <strong>Human Decisions are strictly protected:</strong> Any manual QUALIFIED or DISQUALIFIED
                    verdicts remain intact and marked for human verification.
                  </li>
                  <li>Full immutable audit history is preserved with provenance tracking.</li>
                </ul>
              </div>

              <div className="text-center py-6">
                <button
                  type="button"
                  onClick={handleTriggerReevaluation}
                  disabled={isProcessing}
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-purple-900 hover:bg-purple-800 text-white font-semibold text-xs shadow-md transition-all disabled:opacity-50 cursor-pointer"
                >
                  <RefreshCw className={`w-4 h-4 ${isProcessing ? "animate-spin" : ""}`} />
                  {isProcessing ? "Re-evaluating Submitted Bids..." : "Start Batch Re-evaluation"}
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-6 animate-in fade-in duration-200">
              {/* Stats Summary */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-center">
                  <span className="text-[11px] text-slate-500 font-medium block">Total Bids</span>
                  <span className="text-lg font-bold text-slate-900 font-mono">
                    {result.total_bids_evaluated}
                  </span>
                </div>
                <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-center">
                  <span className="text-[11px] text-amber-700 font-medium block">Status Changes</span>
                  <span className="text-lg font-bold text-amber-900 font-mono">
                    {result.status_changes_count}
                  </span>
                </div>
                <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-center">
                  <span className="text-[11px] text-emerald-700 font-medium block">Decisions Preserved</span>
                  <span className="text-lg font-bold text-emerald-900 font-mono">
                    {result.human_decisions_preserved}
                  </span>
                </div>
              </div>

              {/* Bids List */}
              <div className="border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-2.5">Bid Number</th>
                      <th className="px-4 py-2.5">Bidder</th>
                      <th className="px-4 py-2.5 text-center">Evaluation Transition</th>
                      <th className="px-4 py-2.5 text-right">Score</th>
                      <th className="px-4 py-2.5 text-right">Risk</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {result.bids.map((bid) => (
                      <tr key={bid.bid_id} className="hover:bg-slate-50/75">
                        <td className="px-4 py-3 font-mono font-semibold text-slate-900">{bid.bid_number}</td>
                        <td className="px-4 py-3 text-slate-700">{bid.bidder_name || "—"}</td>
                        <td className="px-4 py-3 text-center">
                          <div className="inline-flex items-center gap-1.5">
                            {bid.previous_compliance_status ? getStatusBadge(bid.previous_compliance_status) : "—"}
                            <ArrowRight className="w-3 h-3 text-slate-400" />
                            {getStatusBadge(bid.new_compliance_status)}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right font-mono font-bold text-slate-900">
                          {bid.score !== null && bid.score !== undefined ? `${bid.score}%` : "—"}
                        </td>
                        <td className="px-4 py-3 text-right font-semibold text-slate-800">
                          {bid.risk_level || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-3 border-t border-slate-200 bg-slate-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-100 shadow-2xs transition-colors"
          >
            {result ? "Done" : "Cancel"}
          </button>
        </div>
      </div>
    </div>
  );
}
