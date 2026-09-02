"use client";

import React, { useEffect, useState, useCallback } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { BulkEvaluationModal } from "@/components/procurement/BulkEvaluationModal";
import { getTendersList } from "@/lib/api/tenders";
import { Tender } from "@/types/tender";
import {
  getActiveTenderBulkEvaluation,
  getBulkEvaluationStatus,
  getBulkEvaluationItems,
} from "@/lib/api/bulk_evaluation";
import {
  BulkEvaluationJobStatusResponse,
  BulkEvaluationJobItem,
} from "@/types/bulk_evaluation";
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  Clock,
  Play,
  RotateCw,
  Search,
  Filter,
  FileCheck2,
  Activity,
  Layers,
  ArrowRight,
  Sparkles,
  Zap,
  Building2,
  CheckSquare,
  XCircle,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Eye,
  FileText,
} from "lucide-react";

export default function ProcurementVerificationsPage() {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [selectedTenderId, setSelectedTenderId] = useState<string>("");
  const [activeJob, setActiveJob] = useState<BulkEvaluationJobStatusResponse | null>(null);
  const [items, setItems] = useState<BulkEvaluationJobItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [itemsLoading, setItemsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [bulkModalOpen, setBulkModalOpen] = useState<boolean>(false);

  // Filter & Pagination States
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalItemsCount, setTotalItemsCount] = useState<number>(0);

  // Load list of available tenders
  const loadTenders = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getTendersList({ page: 1, page_size: 50 });
      const tenderItems = res.items || [];
      setTenders(tenderItems);
      if (tenderItems.length > 0) {
        // Prefer benchmark tender if available, else first tender
        const benchTender = tenderItems.find((t: Tender) => t.tender_number === "GEM/2026/B/200000") || tenderItems[0];
        setSelectedTenderId(benchTender.id);
      }
    } catch (err: any) {
      console.error("Failed to fetch tenders:", err);
      setError(err?.message || "Failed to load tenders list.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTenders();
  }, [loadTenders]);

  // Fetch active job status for selected tender
  const fetchTenderJobStatus = useCallback(async (tId: string) => {
    if (!tId) return;
    try {
      setItemsLoading(true);
      const job = await getActiveTenderBulkEvaluation(tId);
      setActiveJob(job);
      if (job) {
        const itemRes = await getBulkEvaluationItems(job.id, statusFilter || undefined, currentPage, 10);
        setItems(itemRes.items);
        setTotalPages(itemRes.total_pages);
        setTotalItemsCount(itemRes.total);
      } else {
        setItems([]);
        setTotalPages(1);
        setTotalItemsCount(0);
      }
    } catch (err: any) {
      console.error("Failed to fetch bulk evaluation job:", err);
      setActiveJob(null);
      setItems([]);
    } finally {
      setItemsLoading(false);
    }
  }, [currentPage, statusFilter]);

  useEffect(() => {
    if (selectedTenderId) {
      fetchTenderJobStatus(selectedTenderId);
    }
  }, [selectedTenderId, fetchTenderJobStatus]);

  const selectedTender = tenders.find((t) => t.id === selectedTenderId);

  const getStatusBadge = (st: string) => {
    switch (st) {
      case "SUCCESS":
      case "COMPLETED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-bold text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            PASS
          </span>
        );
      case "REVIEW_REQUIRED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-bold text-amber-800 border border-amber-200">
            <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
            REVIEW
          </span>
        );
      case "FAILED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-xs font-bold text-rose-800 border border-rose-200">
            <AlertTriangle className="h-3.5 w-3.5 text-rose-600" />
            FAIL
          </span>
        );
      case "RUNNING":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-bold text-blue-800 border border-blue-200 animate-pulse">
            <Loader2 className="h-3.5 w-3.5 text-blue-600 animate-spin" />
            RUNNING
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700 border border-slate-300">
            {st}
          </span>
        );
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Batch Verification & Bulk Processing Center"
      description="Process hundreds of bidders or documents in a single unified operation with full multi-stage AI verification and compliance analytics."
      breadcrumbs={[
        { label: "Procurement", href: "/procurement" },
        { label: "Verifications & Batch Processing" },
      ]}
    >
      <div className="space-y-6">
        {/* Tender Selection Header & Action Bar */}
        <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-6 text-white shadow-xl border border-slate-800">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2 max-w-2xl">
              <div className="inline-flex items-center gap-2 rounded-full bg-purple-500/20 border border-purple-400/30 px-3 py-1 text-xs font-bold text-purple-300">
                <Zap className="h-3.5 w-3.5 text-purple-400" />
                Scalable Bulk Verification Engine
              </div>
              <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                High-Volume Tender Processing
              </h2>
              <p className="text-xs sm:text-sm text-slate-300">
                Execute single-operation verification for large tenders. Automates document text extraction, statutory registry checks, compliance rules, scoring, and critical anomaly detection.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
              {/* Select Tender Dropdown */}
              <div className="flex flex-col">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                  Active Tender
                </label>
                <select
                  value={selectedTenderId}
                  onChange={(e) => setSelectedTenderId(e.target.value)}
                  className="rounded-xl border border-slate-700 bg-slate-800 text-xs font-bold text-white px-3 py-2.5 focus:ring-2 focus:ring-purple-500 focus:outline-hidden"
                >
                  {tenders.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.tender_number} • {t.title.substring(0, 35)}...
                    </option>
                  ))}
                </select>
              </div>

              {/* Verify All Button */}
              <div className="flex flex-col justify-end">
                <button
                  onClick={() => setBulkModalOpen(true)}
                  disabled={!selectedTenderId}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs px-5 py-2.5 shadow-lg shadow-purple-600/30 transition-all hover:scale-102 active:scale-98 disabled:opacity-50"
                >
                  <Play className="h-4 w-4" />
                  Verify All Bids
                </button>
              </div>
            </div>
          </div>

          {/* 5-Stage Multi-Stage Flow Diagram */}
          <div className="mt-8 pt-6 border-t border-slate-800/80">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3">
              Automated Batch Pipeline Flow
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="rounded-xl bg-slate-800/70 border border-slate-700 p-3 text-center space-y-1">
                <div className="mx-auto flex h-7 w-7 items-center justify-center rounded-lg bg-blue-500/20 text-blue-400 font-bold text-xs">
                  1
                </div>
                <p className="text-xs font-extrabold text-white">200 Bidders</p>
                <p className="text-[10px] text-slate-400">Batch Scope</p>
              </div>

              <div className="rounded-xl bg-slate-800/70 border border-purple-500/40 p-3 text-center space-y-1">
                <div className="mx-auto flex h-7 w-7 items-center justify-center rounded-lg bg-purple-500/20 text-purple-400 font-bold text-xs">
                  2
                </div>
                <p className="text-xs font-extrabold text-purple-200">Verify All</p>
                <p className="text-[10px] text-slate-400">1-Click Trigger</p>
              </div>

              <div className="rounded-xl bg-slate-800/70 border border-indigo-500/40 p-3 text-center space-y-1">
                <div className="mx-auto flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-400 font-bold text-xs">
                  3
                </div>
                <p className="text-xs font-extrabold text-indigo-200">Doc Processing</p>
                <p className="text-[10px] text-slate-400">PDF Text & OCR</p>
              </div>

              <div className="rounded-xl bg-slate-800/70 border border-sky-500/40 p-3 text-center space-y-1">
                <div className="mx-auto flex h-7 w-7 items-center justify-center rounded-lg bg-sky-500/20 text-sky-400 font-bold text-xs">
                  4
                </div>
                <p className="text-xs font-extrabold text-sky-200">Verification</p>
                <p className="text-[10px] text-slate-400">GST / PAN / MCA</p>
              </div>

              <div className="rounded-xl bg-slate-800/70 border border-violet-500/40 p-3 text-center space-y-1">
                <div className="mx-auto flex h-7 w-7 items-center justify-center rounded-lg bg-violet-500/20 text-violet-400 font-bold text-xs">
                  5
                </div>
                <p className="text-xs font-extrabold text-violet-200">Compliance</p>
                <p className="text-[10px] text-slate-400">Rule Evaluation</p>
              </div>

              <div className="rounded-xl bg-purple-950/60 border border-purple-500/60 p-3 text-center space-y-1">
                <div className="mx-auto flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400 font-bold text-xs">
                  ✓
                </div>
                <p className="text-xs font-extrabold text-emerald-300">Results</p>
                <p className="text-[10px] text-purple-200 font-medium">Categorized Telemetry</p>
              </div>
            </div>
          </div>
        </div>

        {/* Results Metrics Cards (128 PASS, 47 REVIEW, 20 FAIL, 5 CRITICAL) */}
        {activeJob && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* PASS Card */}
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-extrabold uppercase tracking-wider text-emerald-800">
                  Fully Compliant (PASS)
                </span>
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700 font-bold">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-mono font-black text-emerald-900">
                  {activeJob.counts.successful}
                </span>
                <span className="text-xs font-bold text-emerald-700">
                  bids ({activeJob.counts.total > 0 ? Math.round((activeJob.counts.successful / activeJob.counts.total) * 100) : 0}%)
                </span>
              </div>
              <p className="text-[11px] text-emerald-700 font-medium">
                Verified against all statutory, financial & technical rules.
              </p>
            </div>

            {/* REVIEW Card */}
            <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-extrabold uppercase tracking-wider text-amber-800">
                  Human Review Required
                </span>
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-100 text-amber-700 font-bold">
                  <AlertCircle className="h-5 w-5" />
                </div>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-mono font-black text-amber-900">
                  {activeJob.counts.review_required}
                </span>
                <span className="text-xs font-bold text-amber-700">
                  bids ({activeJob.counts.total > 0 ? Math.round((activeJob.counts.review_required / activeJob.counts.total) * 100) : 0}%)
                </span>
              </div>
              <p className="text-[11px] text-amber-700 font-medium">
                Flagged for minor document ambiguity or officer sign-off.
              </p>
            </div>

            {/* FAIL Card */}
            <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-extrabold uppercase tracking-wider text-rose-800">
                  Non-Compliant (FAIL)
                </span>
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-rose-100 text-rose-700 font-bold">
                  <AlertTriangle className="h-5 w-5" />
                </div>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-mono font-black text-rose-900">
                  {activeJob.counts.failed}
                </span>
                <span className="text-xs font-bold text-rose-700">
                  bids ({activeJob.counts.total > 0 ? Math.round((activeJob.counts.failed / activeJob.counts.total) * 100) : 0}%)
                </span>
              </div>
              <p className="text-[11px] text-rose-700 font-medium">
                Failed mandatory criteria (e.g. minimum turnover threshold).
              </p>
            </div>

            {/* CRITICAL Card */}
            <div className="rounded-2xl border border-red-300 bg-red-950/90 text-white p-5 shadow-md space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-extrabold uppercase tracking-wider text-red-300">
                  Critical Violations
                </span>
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-red-900 text-red-200 font-bold">
                  <ShieldAlert className="h-5 w-5" />
                </div>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-mono font-black text-white">
                  {activeJob.counts.critical_findings}
                </span>
                <span className="text-xs font-bold text-red-200">
                  bids ({activeJob.counts.total > 0 ? Math.round((activeJob.counts.critical_findings / activeJob.counts.total) * 100) : 0}%)
                </span>
              </div>
              <p className="text-[11px] text-red-200 font-medium">
                Severe anomalies, debarment matches, or CVC blacklist flags.
              </p>
            </div>
          </div>
        )}

        {/* Detailed Item Breakdown Table */}
        <div className="rounded-2xl bg-white border border-slate-200 shadow-sm overflow-hidden space-y-4">
          <div className="p-6 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Batch Verification Item Directory ({totalItemsCount} Bids)
              </h3>
              <p className="text-xs text-slate-500">
                Inspect per-bid verification stages, failure reasons, and critical risk findings.
              </p>
            </div>

            {/* Filter and Search Bar */}
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search bidder or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="rounded-xl border border-slate-300 pl-9 pr-4 py-2 text-xs focus:ring-2 focus:ring-purple-500 focus:outline-hidden"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 focus:ring-2 focus:ring-purple-500 focus:outline-hidden"
              >
                <option value="">All Statuses</option>
                <option value="SUCCESS">SUCCESS (PASS)</option>
                <option value="REVIEW_REQUIRED">REVIEW REQUIRED</option>
                <option value="FAILED">FAILED</option>
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-500 border-y border-slate-200">
                <tr>
                  <th className="px-6 py-3">Bid Number & Vendor</th>
                  <th className="px-6 py-3">Doc Processing</th>
                  <th className="px-6 py-3">Verification</th>
                  <th className="px-6 py-3">Compliance</th>
                  <th className="px-6 py-3">Overall Outcome</th>
                  <th className="px-6 py-3">Critical Findings</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {itemsLoading ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-400">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto text-purple-600 mb-2" />
                      Loading batch items...
                    </td>
                  </tr>
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-400">
                      No batch evaluation items found for this tender. Click <strong>"Verify All Bids"</strong> to run the pipeline.
                    </td>
                  </tr>
                ) : (
                  items
                    .filter((it) => {
                      if (!searchQuery) return true;
                      const q = searchQuery.toLowerCase();
                      return (
                        (it.bidder_name && it.bidder_name.toLowerCase().includes(q)) ||
                        (it.bid_number && it.bid_number.toLowerCase().includes(q))
                      );
                    })
                    .map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-6 py-4">
                          <p className="font-mono font-bold text-slate-900">{item.bid_number}</p>
                          <p className="text-slate-500 font-medium">{item.bidder_name || "Participating Vendor"}</p>
                        </td>

                        <td className="px-6 py-4">
                          <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                            {item.document_processing_status}
                          </span>
                        </td>

                        <td className="px-6 py-4">
                          <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                            {item.verification_status}
                          </span>
                        </td>

                        <td className="px-6 py-4">
                          <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                            {item.compliance_status}
                          </span>
                        </td>

                        <td className="px-6 py-4">{getStatusBadge(item.status)}</td>

                        <td className="px-6 py-4">
                          {item.critical_findings_count > 0 ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-[10px] font-extrabold text-red-800 border border-red-300">
                              <ShieldAlert className="h-3 w-3 text-red-600" />
                              {item.critical_findings_count} CRITICAL
                            </span>
                          ) : (
                            <span className="text-[11px] text-slate-400 font-medium">None</span>
                          )}
                        </td>

                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={() => setBulkModalOpen(true)}
                            className="inline-flex items-center gap-1 text-purple-700 hover:text-purple-900 font-bold text-xs"
                          >
                            <Eye className="h-3.5 w-3.5" />
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          {totalPages > 1 && (
            <div className="p-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
              <span>
                Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong> ({totalItemsCount} total bids)
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                  className="rounded-lg border border-slate-300 px-3 py-1 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                  className="rounded-lg border border-slate-300 px-3 py-1 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bulk Verification Modal */}
      {selectedTenderId && (
        <BulkEvaluationModal
          tenderId={selectedTenderId}
          tenderNumber={selectedTender?.tender_number}
          tenderTitle={selectedTender?.title}
          isOpen={bulkModalOpen}
          onClose={() => setBulkModalOpen(false)}
          onJobCompleted={() => {
            if (selectedTenderId) fetchTenderJobStatus(selectedTenderId);
          }}
        />
      )}
    </DashboardLayout>
  );
}
