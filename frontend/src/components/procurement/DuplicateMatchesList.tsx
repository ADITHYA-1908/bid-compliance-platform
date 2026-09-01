"use client";

import React, { useState, useEffect } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  ShieldAlert,
  Search,
  RefreshCw,
  Eye,
  FileText,
  Filter,
  Loader2,
  Sparkles,
} from "lucide-react";
import {
  DuplicateMatchListItem,
  DuplicateMatchListResponse,
  DuplicateMatchSummaryCounts,
} from "@/types/duplicate_detection";
import {
  getTenderDuplicateMatches,
  triggerTenderDuplicateScan,
} from "@/lib/api/duplicate_detection";
import { DuplicateMatchDetailModal } from "./DuplicateMatchDetailModal";

interface DuplicateMatchesListProps {
  tenderId: string;
  tenderNumber?: string;
}

export function DuplicateMatchesList({
  tenderId,
  tenderNumber,
}: DuplicateMatchesListProps) {
  const [data, setData] = useState<DuplicateMatchListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filter State
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [matchTypeFilter, setMatchTypeFilter] = useState<string>("");
  const [selectedMatchId, setSelectedMatchId] = useState<string | null>(null);

  useEffect(() => {
    loadMatches();
  }, [tenderId, statusFilter, matchTypeFilter]);

  async function loadMatches() {
    setLoading(true);
    setError(null);
    try {
      const res = await getTenderDuplicateMatches(
        tenderId,
        statusFilter || undefined,
        matchTypeFilter || undefined
      );
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load duplicate match alerts.");
    } finally {
      setLoading(false);
    }
  }

  async function handleTriggerScan() {
    setScanning(true);
    setScanMessage(null);
    setError(null);
    try {
      const res = await triggerTenderDuplicateScan(tenderId);
      setScanMessage(res.summary);
      await loadMatches();
    } catch (err: any) {
      setError(err?.message || "Failed to execute duplicate scan.");
    } finally {
      setScanning(false);
    }
  }

  const counts: DuplicateMatchSummaryCounts = data?.counts || {
    total: 0,
    detected: 0,
    review_required: 0,
    confirmed_reuse: 0,
    confirmed_benign: 0,
    dismissed: 0,
    exact_file_duplicates: 0,
    content_duplicates: 0,
    structured_matches: 0,
    high_similarity: 0,
  };

  return (
    <div className="space-y-6">
      {/* Header & Scan Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-indigo-950/40 border border-slate-800 shadow-lg">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h2 className="text-base font-bold text-slate-100">
              Duplicate & Reuse Document Alerts
            </h2>
            {counts.review_required > 0 && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">
                {counts.review_required} Action Required
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400">
            Multi-signal cross-bidder document reuse detection (File hash, normalized text, structured fields & semantic similarity).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleTriggerScan}
            disabled={scanning}
            className="px-4 py-2.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 transition-all flex items-center gap-2 shadow-lg shadow-indigo-600/25"
          >
            {scanning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Scanning Submissions...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-indigo-200" />
                Run Duplicate Scan
              </>
            )}
          </button>
        </div>
      </div>

      {/* Scan Outcome Toast */}
      {scanMessage && (
        <div className="p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-indigo-200 text-xs flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-indigo-400" />
            <span>{scanMessage}</span>
          </div>
          <button onClick={() => setScanMessage(null)} className="text-slate-400 hover:text-slate-200">
            Dismiss
          </button>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Summary Counter Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Total Alerts</div>
          <div className="text-2xl font-black text-slate-100">{counts.total}</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider">Review Required</div>
          <div className="text-2xl font-black text-amber-300">{counts.review_required}</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider">Confirmed Reuse</div>
          <div className="text-2xl font-black text-rose-300">{counts.confirmed_reuse}</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider">Confirmed Benign</div>
          <div className="text-2xl font-black text-emerald-300">{counts.confirmed_benign}</div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-slate-900/40 border border-slate-800/80">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5 mr-1">
            <Filter className="w-3.5 h-3.5" /> Status:
          </span>
          {[
            { label: "All Statuses", val: "" },
            { label: "Review Required", val: "REVIEW_REQUIRED" },
            { label: "Confirmed Reuse", val: "CONFIRMED_REUSE" },
            { label: "Confirmed Benign", val: "CONFIRMED_BENIGN" },
            { label: "Dismissed", val: "DISMISSED" },
          ].map((f) => (
            <button
              key={f.val}
              onClick={() => setStatusFilter(f.val)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                statusFilter === f.val
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "bg-slate-800/60 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Match Type Dropdown */}
        <select
          value={matchTypeFilter}
          onChange={(e) => setMatchTypeFilter(e.target.value)}
          className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Match Signals</option>
          <option value="EXACT_FILE_DUPLICATE">Exact File Duplicate (SHA-256)</option>
          <option value="CONTENT_DUPLICATE">Content Duplicate (Normalized)</option>
          <option value="STRUCTURED_DATA_MATCH">Structured Data Match (Cert/ID)</option>
          <option value="HIGH_SIMILARITY">High Text Similarity (&gt;90%)</option>
          <option value="POSSIBLE_REUSE">Possible Document Reuse</option>
        </select>
      </div>

      {/* Matches List Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-xl">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 space-y-3">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
            <p className="text-xs text-slate-400">Loading cross-bidder duplicate match alerts...</p>
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 px-4 text-center space-y-3">
            <div className="p-3 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <ShieldCheck className="w-8 h-8" />
            </div>
            <h3 className="text-sm font-bold text-slate-200">No Duplicate Anomalies Found</h3>
            <p className="text-xs text-slate-400 max-w-md">
              No cross-bidder document reuse signals detected matching current filters. Run a scan anytime to re-evaluate newly submitted documents.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-3 px-4">Competing Bidders</th>
                  <th className="py-3 px-4">Document Type</th>
                  <th className="py-3 px-4">Match Signal</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Matched Attributes</th>
                  <th className="py-3 px-4">Review Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {data.items.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/30 transition-colors">
                    {/* Bidders Column */}
                    <td className="py-3.5 px-4">
                      <div className="space-y-0.5">
                        <div className="font-semibold text-slate-200 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-indigo-400 flex-shrink-0" />
                          {item.bidder_a_name}
                        </div>
                        <div className="text-slate-400 flex items-center gap-1.5 pl-3.5 text-[11px]">
                          <span className="text-slate-500">↔</span>
                          {item.bidder_b_name}
                        </div>
                      </div>
                    </td>

                    {/* Document Type */}
                    <td className="py-3.5 px-4 font-medium text-slate-300">
                      {item.document_type}
                    </td>

                    {/* Match Signal Badge */}
                    <td className="py-3.5 px-4">
                      <span className={`inline-flex px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        item.match_type === "EXACT_FILE_DUPLICATE"
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                          : item.match_type === "CONTENT_DUPLICATE"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                          : item.match_type === "STRUCTURED_DATA_MATCH"
                          ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                          : "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                      }`}>
                        {item.match_type.replace(/_/g, " ")}
                      </span>
                    </td>

                    {/* Overall Confidence */}
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-200">
                        {Math.round(item.overall_confidence * 100)}%
                      </div>
                    </td>

                    {/* Matched Attributes Pills */}
                    <td className="py-3.5 px-4">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {item.matched_fields_summary.length > 0 ? (
                          item.matched_fields_summary.map((key) => (
                            <span key={key} className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 font-mono">
                              {key}
                            </span>
                          ))
                        ) : item.file_hash_match ? (
                          <span className="px-1.5 py-0.5 rounded bg-rose-950/40 text-[10px] text-rose-300 border border-rose-800/40">
                            Identical Binary SHA-256
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400">
                            Text Semantics
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Status Badge */}
                    <td className="py-3.5 px-4">
                      <span className={`inline-flex px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        item.status === "CONFIRMED_REUSE"
                          ? "bg-rose-600/20 text-rose-400 border border-rose-600/40"
                          : item.status === "CONFIRMED_BENIGN"
                          ? "bg-emerald-600/20 text-emerald-400 border border-emerald-600/40"
                          : item.status === "DISMISSED"
                          ? "bg-slate-700 text-slate-300"
                          : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                      }`}>
                        {item.status.replace(/_/g, " ")}
                      </span>
                    </td>

                    {/* Inspect & Review Action */}
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => setSelectedMatchId(item.id)}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-all flex items-center gap-1.5 ml-auto border border-slate-700/60"
                      >
                        <Eye className="w-3.5 h-3.5 text-indigo-400" />
                        Inspect & Review
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Side-by-Side Modal */}
      {selectedMatchId && (
        <DuplicateMatchDetailModal
          matchId={selectedMatchId}
          isOpen={!!selectedMatchId}
          onClose={() => setSelectedMatchId(null)}
          onReviewed={loadMatches}
        />
      )}
    </div>
  );
}
