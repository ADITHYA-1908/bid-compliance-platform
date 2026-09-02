"use client";

import React, { useEffect, useState } from "react";
import {
  TenderRequirementFieldDiff,
  TenderRequirementVersionCompareResponse,
  TenderRequirementVersionResponse,
} from "@/types/rule_versions";
import { ruleVersionsApi } from "@/lib/api/rule_versions";
import {
  GitCompare,
  X,
  AlertCircle,
  CheckCircle2,
  Clock,
  User,
  FileText,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Info,
} from "lucide-react";

interface RuleVersionCompareModalProps {
  isOpen: boolean;
  onClose: () => void;
  tenderId: string;
  requirementId: string;
  initialV1?: number;
  initialV2?: number;
  availableVersions: TenderRequirementVersionResponse[];
}

export function RuleVersionCompareModal({
  isOpen,
  onClose,
  tenderId,
  requirementId,
  initialV1,
  initialV2,
  availableVersions,
}: RuleVersionCompareModalProps) {
  const [v1, setV1] = useState<number>(initialV1 || 1);
  const [v2, setV2] = useState<number>(initialV2 || 2);
  const [comparison, setComparison] = useState<TenderRequirementVersionCompareResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialV1 !== undefined) setV1(initialV1);
    if (initialV2 !== undefined) setV2(initialV2);
  }, [initialV1, initialV2]);

  useEffect(() => {
    if (!isOpen) return;
    if (v1 === v2) {
      setComparison(null);
      return;
    }

    const fetchComparison = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await ruleVersionsApi.compareRequirementVersions(tenderId, requirementId, v1, v2);
        setComparison(res);
      } catch (err: any) {
        setError(err?.message || "Failed to compare versions.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchComparison();
  }, [isOpen, tenderId, requirementId, v1, v2]);

  if (!isOpen) return null;

  const getImpactBadge = (level: string) => {
    switch (level) {
      case "CRITICAL":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
            <ShieldAlert className="w-3 h-3" /> Critical
          </span>
        );
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3" /> High
          </span>
        );
      case "MEDIUM":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
            <Info className="w-3 h-3" /> Medium
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-slate-50 text-slate-600 border border-slate-200">
            Info
          </span>
        );
    }
  };

  const formatValue = (val: any) => {
    if (val === null || val === undefined) return <span className="text-slate-400 italic">None</span>;
    if (typeof val === "boolean") {
      return val ? (
        <span className="text-emerald-700 font-semibold">Yes / True</span>
      ) : (
        <span className="text-slate-600">No / False</span>
      );
    }
    if (typeof val === "object") {
      return <pre className="font-mono text-[11px] bg-slate-100 p-1.5 rounded">{JSON.stringify(val, null, 2)}</pre>;
    }
    return String(val);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-100 text-indigo-700">
              <GitCompare className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                Rule Version Comparison
                {comparison && (
                  <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                    {comparison.code}
                  </span>
                )}
              </h3>
              <p className="text-xs text-slate-500">
                Detailed field-by-field differences and qualification impact analysis
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

        {/* Version Pickers Bar */}
        <div className="px-6 py-3 bg-slate-100/75 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <label className="text-xs font-semibold text-slate-700">Baseline (V1):</label>
            <select
              value={v1}
              onChange={(e) => setV1(Number(e.target.value))}
              className="px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-medium text-slate-800 shadow-2xs focus:ring-2 focus:ring-indigo-500"
            >
              {availableVersions.map((ver) => (
                <option key={ver.id} value={ver.version_number}>
                  Version {ver.version_number} ({new Date(ver.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 text-slate-400">
            <ArrowRight className="w-4 h-4" />
          </div>

          <div className="flex items-center gap-3">
            <label className="text-xs font-semibold text-slate-700">Compared (V2):</label>
            <select
              value={v2}
              onChange={(e) => setV2(Number(e.target.value))}
              className="px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-medium text-slate-800 shadow-2xs focus:ring-2 focus:ring-indigo-500"
            >
              {availableVersions.map((ver) => (
                <option key={ver.id} value={ver.version_number}>
                  Version {ver.version_number} ({new Date(ver.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading ? (
            <div className="py-12 text-center text-slate-500 text-sm">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-3" />
              <p>Computing field-level differences...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : v1 === v2 ? (
            <div className="py-12 text-center text-slate-500">
              <p className="text-sm font-medium">Select two different versions above to compare.</p>
            </div>
          ) : comparison ? (
            <>
              {/* Summary Banner */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Version A Card */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-700 px-2 py-0.5 rounded bg-slate-200">
                      Version {comparison.v1_number}
                    </span>
                    <span className="text-[11px] text-slate-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(comparison.v1_created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-xs text-slate-600">
                    <span className="font-semibold text-slate-800">Author:</span> {comparison.v1_author || "System"}
                  </div>
                  <div className="text-xs text-slate-600">
                    <span className="font-semibold text-slate-800">Reason:</span>{" "}
                    {comparison.v1_reason || "Initial baseline"}
                  </div>
                </div>

                {/* Version B Card */}
                <div className="p-4 rounded-xl bg-indigo-50/50 border border-indigo-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-indigo-700 px-2 py-0.5 rounded bg-indigo-100">
                      Version {comparison.v2_number} (Target)
                    </span>
                    <span className="text-[11px] text-indigo-600 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(comparison.v2_created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-xs text-slate-600">
                    <span className="font-semibold text-slate-800">Author:</span> {comparison.v2_author || "System"}
                  </div>
                  <div className="text-xs text-slate-600">
                    <span className="font-semibold text-slate-800">Reason:</span>{" "}
                    {comparison.v2_reason || "Rule modification"}
                  </div>
                </div>
              </div>

              {/* Diff Stats */}
              <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-100 text-xs font-medium text-slate-700">
                <span>
                  Differences Detected:{" "}
                  <strong className="text-indigo-900">{comparison.differences_count} fields modified</strong>
                </span>
                {comparison.has_differences ? (
                  <span className="text-amber-700 font-semibold flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> Re-evaluation Recommended
                  </span>
                ) : (
                  <span className="text-emerald-700 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Identical Parameters
                  </span>
                )}
              </div>

              {/* Diffs Table */}
              <div className="border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3 w-1/4">Requirement Field</th>
                      <th className="px-4 py-3 w-1/3">Version {comparison.v1_number}</th>
                      <th className="px-4 py-3 w-1/3">Version {comparison.v2_number}</th>
                      <th className="px-4 py-3 w-28 text-right">Impact</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {comparison.diffs.map((diff: TenderRequirementFieldDiff) => (
                      <tr
                        key={diff.field_name}
                        className={diff.is_different ? "bg-amber-50/30 hover:bg-amber-50/60" : "hover:bg-slate-50"}
                      >
                        <td className="px-4 py-3">
                          <div className="font-semibold text-slate-900">{diff.field_label}</div>
                          <span className="font-mono text-[10px] text-slate-400">{diff.field_name}</span>
                          {diff.impact_summary && (
                            <p className="text-[11px] text-indigo-700 mt-0.5">{diff.impact_summary}</p>
                          )}
                        </td>
                        <td
                          className={`px-4 py-3 text-slate-600 ${
                            diff.is_different ? "bg-rose-50/40 text-rose-900 line-through opacity-80" : ""
                          }`}
                        >
                          {formatValue(diff.old_value)}
                        </td>
                        <td
                          className={`px-4 py-3 font-medium ${
                            diff.is_different ? "bg-emerald-50/50 text-emerald-900" : "text-slate-800"
                          }`}
                        >
                          {formatValue(diff.new_value)}
                        </td>
                        <td className="px-4 py-3 text-right">{getImpactBadge(diff.impact_level)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-3 border-t border-slate-200 bg-slate-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-100 shadow-2xs transition-colors"
          >
            Close Comparison
          </button>
        </div>
      </div>
    </div>
  );
}
