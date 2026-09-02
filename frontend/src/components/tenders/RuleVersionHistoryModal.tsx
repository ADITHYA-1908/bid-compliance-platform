"use client";

import React, { useEffect, useState } from "react";
import {
  TenderRequirementVersionListResponse,
  TenderRequirementVersionResponse,
} from "@/types/rule_versions";
import { ruleVersionsApi } from "@/lib/api/rule_versions";
import { RuleVersionCompareModal } from "./RuleVersionCompareModal";
import { RuleReevaluationModal } from "./RuleReevaluationModal";
import {
  History,
  X,
  Clock,
  User,
  GitCompare,
  FileText,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  Calendar,
  Layers,
  FileCheck,
  ShieldCheck,
} from "lucide-react";

interface RuleVersionHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  tenderId: string;
  tenderNumber: string;
  requirementId: string;
  requirementCode: string;
  requirementName: string;
  onRefreshParent?: () => void;
}

export function RuleVersionHistoryModal({
  isOpen,
  onClose,
  tenderId,
  tenderNumber,
  requirementId,
  requirementCode,
  requirementName,
  onRefreshParent,
}: RuleVersionHistoryModalProps) {
  const [historyData, setHistoryData] = useState<TenderRequirementVersionListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Compare modal state
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareV1, setCompareV1] = useState<number>(1);
  const [compareV2, setCompareV2] = useState<number>(2);

  // Reevaluate modal state
  const [reevalOpen, setReevalOpen] = useState(false);

  const fetchVersions = async () => {
    if (!isOpen) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await ruleVersionsApi.getRequirementVersions(tenderId, requirementId);
      setHistoryData(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load version history.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchVersions();
    }
  }, [isOpen, tenderId, requirementId]);

  if (!isOpen) return null;

  const handleLaunchCompare = (v1: number, v2: number) => {
    setCompareV1(v1);
    setCompareV2(v2);
    setCompareOpen(true);
  };

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
        <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-indigo-100 text-indigo-700">
                <History className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  Compliance Rule Version History
                  <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                    {requirementCode}
                  </span>
                </h3>
                <p className="text-xs text-slate-500 line-clamp-1">{requirementName}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setReevalOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-100 hover:bg-purple-200 text-purple-800 text-xs font-semibold transition-colors cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Re-evaluate Bids
              </button>
              <button
                onClick={onClose}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {isLoading ? (
              <div className="py-12 text-center text-slate-500 text-sm">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-3" />
                <p>Loading immutable version history timeline...</p>
              </div>
            ) : error ? (
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            ) : historyData && historyData.versions.length > 0 ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between text-xs text-slate-500 pb-2 border-b border-slate-100">
                  <span>
                    Total Revisions: <strong>{historyData.total_versions}</strong>
                  </span>
                  <span>
                    Active Benchmark: <strong>v{historyData.current_version_number}</strong>
                  </span>
                </div>

                {/* Timeline */}
                <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
                  {historyData.versions.map((ver, idx) => {
                    const isCurrent = ver.version_number === historyData.current_version_number;
                    const prevVer = historyData.versions[idx + 1];

                    return (
                      <div key={ver.id} className="relative group">
                        {/* Timeline Node */}
                        <div
                          className={`absolute -left-6 top-1.5 w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                            isCurrent
                              ? "bg-indigo-600 border-white shadow-xs"
                              : "bg-white border-slate-300"
                          }`}
                        >
                          {isCurrent ? (
                            <div className="w-2 h-2 rounded-full bg-white" />
                          ) : (
                            <div className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                          )}
                        </div>

                        {/* Version Card */}
                        <div
                          className={`p-4 rounded-xl border transition-all ${
                            isCurrent
                              ? "bg-indigo-50/40 border-indigo-200 shadow-xs"
                              : "bg-white border-slate-200 hover:border-slate-300"
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
                                  isCurrent
                                    ? "bg-indigo-600 text-white"
                                    : "bg-slate-100 text-slate-700 border border-slate-200"
                                }`}
                              >
                                v{ver.version_number}
                              </span>
                              {isCurrent && (
                                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700 bg-indigo-100/70 px-2 py-0.5 rounded-full">
                                  Current Benchmark
                                </span>
                              )}
                              {ver.corrigendum_number && (
                                <span className="text-[11px] font-semibold text-amber-800 bg-amber-100 px-2 py-0.5 rounded">
                                  Corrigendum: {ver.corrigendum_number}
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-3">
                              {prevVer && (
                                <button
                                  type="button"
                                  onClick={() => handleLaunchCompare(prevVer.version_number, ver.version_number)}
                                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-700 hover:text-indigo-900 hover:underline cursor-pointer"
                                >
                                  <GitCompare className="w-3.5 h-3.5" />
                                  Diff vs v{prevVer.version_number}
                                </button>
                              )}
                              <span className="text-[11px] text-slate-400 flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {new Date(ver.created_at).toLocaleString()}
                              </span>
                            </div>
                          </div>

                          {/* Rule Snapshot Content */}
                          <div className="space-y-2 text-xs">
                            <div className="font-semibold text-slate-900">{ver.name}</div>
                            {ver.description && (
                              <p className="text-slate-600 text-[11px]">{ver.description}</p>
                            )}

                            {/* Details Grid */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-100 text-[11px]">
                              <div>
                                <span className="text-slate-400 block">Operator & Expected</span>
                                <span className="font-mono font-medium text-slate-800">
                                  {ver.operator}{" "}
                                  {typeof ver.expected_value === "object"
                                    ? JSON.stringify(ver.expected_value)
                                    : String(ver.expected_value ?? "—")}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block">Mandatory / Critical</span>
                                <span className="font-medium text-slate-800">
                                  {ver.is_mandatory ? "Mandatory" : "Optional"} •{" "}
                                  {ver.is_critical ? "Critical" : "Standard"}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block">Score Weight</span>
                                <span className="font-mono font-medium text-slate-800">
                                  {ver.weight ? `${ver.weight} pts` : "—"}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block">Source Ref</span>
                                <span className="font-medium text-slate-800 truncate block">
                                  {ver.source_clause ? `Clause ${ver.source_clause}` : "—"}
                                  {ver.source_page ? ` (p.${ver.source_page})` : ""}
                                </span>
                              </div>
                            </div>

                            {/* Change Rationale & Author Provenance */}
                            <div className="mt-2 pt-2 bg-slate-50/75 p-2 rounded-lg text-[11px] space-y-1">
                              <div className="text-slate-700">
                                <strong className="text-slate-900">Change Reason:</strong>{" "}
                                {ver.change_reason || "Initial baseline definition"}
                              </div>
                              <div className="text-slate-500 flex items-center gap-1">
                                <User className="w-3 h-3 text-slate-400" />
                                <span>Modified by: {ver.changed_by_name || "System"}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500 text-xs">
                No historical versions found for this requirement.
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-3 border-t border-slate-200 bg-slate-50">
            <div className="text-[11px] text-slate-500">
              Deterministic rule provenance compliant with public procurement audit standards.
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-100 shadow-2xs transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>

      {/* Compare Modal */}
      {historyData && (
        <RuleVersionCompareModal
          isOpen={compareOpen}
          onClose={() => setCompareOpen(false)}
          tenderId={tenderId}
          requirementId={requirementId}
          initialV1={compareV1}
          initialV2={compareV2}
          availableVersions={historyData.versions}
        />
      )}

      {/* Re-evaluation Modal */}
      <RuleReevaluationModal
        isOpen={reevalOpen}
        onClose={() => setReevalOpen(false)}
        tenderId={tenderId}
        tenderNumber={tenderNumber}
        requirementId={requirementId}
        requirementCode={requirementCode}
        onSuccess={() => {
          if (onRefreshParent) onRefreshParent();
        }}
      />
    </>
  );
}
