"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import {
  BulkEvaluationJobStatusResponse,
  BulkEvaluationJobItem,
} from "@/types/bulk_evaluation";
import {
  triggerBulkEvaluation,
  getBulkEvaluationStatus,
  getBulkEvaluationItems,
  retryFailedBulkItems,
  retrySingleBulkItem,
  cancelBulkEvaluation,
  getActiveTenderBulkEvaluation,
} from "@/lib/api/bulk_evaluation";
import {
  X,
  Play,
  RotateCw,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  Clock,
  Ban,
  Search,
  ShieldCheck,
  ShieldAlert,
  Loader2,
  RefreshCw,
  FileCheck2,
  Activity,
  Layers,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from "lucide-react";

interface BulkEvaluationModalProps {
  tenderId: string;
  tenderNumber?: string;
  tenderTitle?: string;
  isOpen: boolean;
  onClose: () => void;
  onJobCompleted?: () => void;
}

export function BulkEvaluationModal({
  tenderId,
  tenderNumber,
  tenderTitle,
  isOpen,
  onClose,
  onJobCompleted,
}: BulkEvaluationModalProps) {
  const [job, setJob] = useState<BulkEvaluationJobStatusResponse | null>(null);
  const [items, setItems] = useState<BulkEvaluationJobItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [starting, setStarting] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [retryingItemId, setRetryingItemId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalItemsCount, setTotalItemsCount] = useState<number>(0);

  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  const prevJobStatusRef = useRef<string | null>(null);

  const loadJobItems = useCallback(
    async (jobId: string, page = currentPage, status = filterStatus) => {
      try {
        const res = await getBulkEvaluationItems(jobId, status || undefined, page, 10);
        setItems(res.items);
        setTotalPages(res.total_pages);
        setTotalItemsCount(res.total);
      } catch (err: any) {
        console.error("Failed to load job items:", err);
      }
    },
    [currentPage, filterStatus]
  );

  const fetchJobStatus = useCallback(async () => {
    if (!tenderId) return;
    try {
      let currentJob = job;
      if (!currentJob) {
        currentJob = await getActiveTenderBulkEvaluation(tenderId);
        setJob(currentJob);
      } else {
        const updated = await getBulkEvaluationStatus(currentJob.id);
        setJob(updated);
        currentJob = updated;
      }

      if (currentJob) {
        await loadJobItems(currentJob.id);

        // Check if job transitioned to completed/partially completed
        if (
          prevJobStatusRef.current &&
          ["QUEUED", "RUNNING"].includes(prevJobStatusRef.current) &&
          ["COMPLETED", "PARTIALLY_COMPLETED", "FAILED"].includes(currentJob.status)
        ) {
          if (onJobCompleted) {
            onJobCompleted();
          }
        }
        prevJobStatusRef.current = currentJob.status;
      }
    } catch (err: any) {
      console.error("Failed to fetch bulk evaluation status:", err);
      setError(err?.message || "Failed to load bulk job status.");
    } finally {
      setLoading(false);
    }
  }, [tenderId, job, loadJobItems, onJobCompleted]);

  // Initial load
  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      setError(null);
      fetchJobStatus();
    } else {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    }
  }, [isOpen, fetchJobStatus]);

  // Polling while RUNNING or QUEUED
  useEffect(() => {
    if (!isOpen || !job) return;

    if (job.status === "RUNNING" || job.status === "QUEUED") {
      pollTimerRef.current = setInterval(() => {
        fetchJobStatus();
      }, 2000);
    } else {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [isOpen, job?.status, fetchJobStatus]);

  const handleStartBulkEvaluation = async () => {
    setStarting(true);
    setError(null);
    try {
      const res = await triggerBulkEvaluation(tenderId);
      const newJob = await getBulkEvaluationStatus(res.job_id);
      setJob(newJob);
      prevJobStatusRef.current = newJob.status;
      await loadJobItems(newJob.id);
    } catch (err: any) {
      setError(err?.message || "Failed to start bulk evaluation.");
    } finally {
      setStarting(false);
    }
  };

  const handleRetryFailed = async () => {
    if (!job) return;
    setActionLoading(true);
    setError(null);
    try {
      await retryFailedBulkItems(job.id);
      await fetchJobStatus();
    } catch (err: any) {
      setError(err?.message || "Failed to retry failed items.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRetrySingle = async (itemId: string) => {
    if (!job) return;
    setRetryingItemId(itemId);
    try {
      await retrySingleBulkItem(job.id, itemId);
      await fetchJobStatus();
    } catch (err: any) {
      alert(`Failed to retry item: ${err?.message || "Unknown error"}`);
    } finally {
      setRetryingItemId(null);
    }
  };

  const handleCancelJob = async () => {
    if (!job) return;
    if (!confirm("Are you sure you want to cancel the active bulk evaluation? Remaining bids will be skipped.")) {
      return;
    }
    setActionLoading(true);
    try {
      await cancelBulkEvaluation(job.id);
      await fetchJobStatus();
    } catch (err: any) {
      setError(err?.message || "Failed to cancel bulk evaluation.");
    } finally {
      setActionLoading(false);
    }
  };

  if (!isOpen) return null;

  const isRunning = job?.status === "RUNNING" || job?.status === "QUEUED";
  const progressPct = job?.counts?.progress_percentage ?? 0;

  // Filter items by client search query if entered
  const filteredItems = items.filter((it) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (it.bidder_name && it.bidder_name.toLowerCase().includes(q)) ||
      (it.bid_number && it.bid_number.toLowerCase().includes(q)) ||
      (it.current_stage && it.current_stage.toLowerCase().includes(q)) ||
      (it.status && it.status.toLowerCase().includes(q))
    );
  });

  const getStatusBadge = (st: string) => {
    switch (st) {
      case "SUCCESS":
      case "COMPLETED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="h-3 w-3 text-emerald-600" />
            SUCCESS
          </span>
        );
      case "REVIEW_REQUIRED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200">
            <AlertCircle className="h-3 w-3 text-amber-600" />
            REVIEW REQ.
          </span>
        );
      case "RUNNING":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-[10px] font-bold text-blue-800 border border-blue-200 animate-pulse">
            <Loader2 className="h-3 w-3 text-blue-600 animate-spin" />
            RUNNING
          </span>
        );
      case "QUEUED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-semibold text-slate-700 border border-slate-300">
            <Clock className="h-3 w-3 text-slate-500" />
            QUEUED
          </span>
        );
      case "FAILED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-[10px] font-bold text-rose-800 border border-rose-200">
            <AlertTriangle className="h-3 w-3 text-rose-600" />
            FAILED
          </span>
        );
      case "PARTIALLY_COMPLETED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200">
            <AlertCircle className="h-3 w-3 text-amber-600" />
            PARTIAL
          </span>
        );
      case "CANCELLED":
      case "SKIPPED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-semibold text-slate-600 border border-slate-200">
            <Ban className="h-3 w-3 text-slate-400" />
            {st}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-700">
            {st}
          </span>
        );
    }
  };

  const getStageBadge = (stage: string) => {
    switch (stage) {
      case "DOCUMENT_PROCESSING":
        return <span className="text-[11px] font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">Doc AI Ingestion</span>;
      case "VERIFICATION":
        return <span className="text-[11px] font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">Claims Verification</span>;
      case "COMPLIANCE":
        return <span className="text-[11px] font-medium text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-100">Clause Compliance</span>;
      case "SCORING":
        return <span className="text-[11px] font-medium text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-100">Score Engine</span>;
      case "RISK":
        return <span className="text-[11px] font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-100">Risk Assessment</span>;
      case "COMPLETED":
        return <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">Pipeline Complete</span>;
      case "FAILED":
        return <span className="text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-100">Failed</span>;
      default:
        return <span className="text-[11px] text-slate-500">{stage}</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 sm:p-6 overflow-y-auto">
      <div className="relative w-full max-w-5xl rounded-2xl bg-white shadow-2xl border border-slate-200 flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-900 px-6 py-4 text-white shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600/30 border border-purple-400/40 text-purple-200">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Bulk Verification & Batch Evaluation</h3>
                {job && getStatusBadge(job.status)}
              </div>
              <p className="text-xs text-slate-300">
                {tenderNumber ? `${tenderNumber} • ` : ""}
                {tenderTitle || "Tender Batch Processing Pipeline"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchJobStatus()}
              disabled={loading || actionLoading}
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              title="Refresh telemetry"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Error Message */}
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
              <div className="flex-1 text-xs text-red-800">
                <p className="font-bold">Error executing bulk operation</p>
                <p className="mt-0.5">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="text-xs text-red-700 hover:text-red-900 font-bold"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* No Job State */}
          {!job && !loading && (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-8 text-center space-y-4">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-purple-100 text-purple-700">
                <FileCheck2 className="h-7 w-7" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h4 className="text-base font-bold text-slate-900">No Bulk Evaluation Run Yet</h4>
                <p className="text-xs text-slate-500">
                  Process all submitted bids on this tender in one operation through Document AI, Statutory Verification, Clause Compliance, Scoring, and Risk Assessment.
                </p>
              </div>
              <button
                onClick={handleStartBulkEvaluation}
                disabled={starting}
                className="inline-flex items-center gap-2 rounded-xl bg-purple-900 px-5 py-2.5 text-xs font-bold text-white shadow-md hover:bg-purple-800 transition-all disabled:opacity-50"
              >
                {starting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                Run Bulk Evaluation on All Bids
              </button>
            </div>
          )}

          {/* Active / Completed Job Banner */}
          {job && (
            <div className="space-y-6">
              {/* Progress & Live Telemetry Card */}
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Activity className="h-4 w-4 text-purple-900" />
                    <span className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                      {isRunning ? "Batch Processing in Progress" : "Batch Evaluation Summary"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    {isRunning && (
                      <span className="flex items-center gap-1.5 font-bold text-blue-700">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Processing {job.counts.processed} / {job.counts.total} bids
                      </span>
                    )}
                    <span className="font-mono font-bold text-purple-900 text-sm">
                      {progressPct}%
                    </span>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="h-3 w-full rounded-full bg-slate-200 overflow-hidden border border-slate-300 shadow-inner">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      job.status === "COMPLETED"
                        ? "bg-emerald-600"
                        : job.status === "PARTIALLY_COMPLETED"
                        ? "bg-amber-500"
                        : job.status === "FAILED"
                        ? "bg-rose-600"
                        : isRunning
                        ? "bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-600 animate-pulse"
                        : "bg-purple-700"
                    }`}
                    style={{ width: `${progressPct}%` }}
                  />
                </div>

                {/* 5-Stage Pipeline Flow Indicator */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-1 pb-1">
                  <div className="rounded-lg bg-white p-2 border border-slate-200 text-center">
                    <span className="text-[9px] font-extrabold uppercase text-slate-400 block">Stage 1</span>
                    <span className="text-xs font-extrabold text-slate-800">200 Bidders</span>
                  </div>
                  <div className="rounded-lg bg-purple-50 p-2 border border-purple-200 text-center">
                    <span className="text-[9px] font-extrabold uppercase text-purple-600 block">Stage 2</span>
                    <span className="text-xs font-extrabold text-purple-900">Verify All</span>
                  </div>
                  <div className="rounded-lg bg-indigo-50 p-2 border border-indigo-200 text-center">
                    <span className="text-[9px] font-extrabold uppercase text-indigo-600 block">Stage 3</span>
                    <span className="text-xs font-extrabold text-indigo-900">Doc Processing</span>
                  </div>
                  <div className="rounded-lg bg-blue-50 p-2 border border-blue-200 text-center">
                    <span className="text-[9px] font-extrabold uppercase text-blue-600 block">Stage 4</span>
                    <span className="text-xs font-extrabold text-blue-900">Verification</span>
                  </div>
                  <div className="rounded-lg bg-emerald-50 p-2 border border-emerald-200 text-center">
                    <span className="text-[9px] font-extrabold uppercase text-emerald-600 block">Stage 5</span>
                    <span className="text-xs font-extrabold text-emerald-900">Compliance & Results</span>
                  </div>
                </div>

                {/* KPI Breakdown Metrics */}
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
                  <div className="rounded-lg bg-white p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total Bids</p>
                    <p className="mt-1 text-lg font-mono font-extrabold text-slate-800">{job.counts.total}</p>
                  </div>
                  <div className="rounded-lg bg-white p-3 border border-emerald-100">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-600">Successful</p>
                    <p className="mt-1 text-lg font-mono font-extrabold text-emerald-700">{job.counts.successful}</p>
                  </div>
                  <div className="rounded-lg bg-white p-3 border border-amber-100">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-amber-600">Review Req.</p>
                    <p className="mt-1 text-lg font-mono font-extrabold text-amber-700">{job.counts.review_required}</p>
                  </div>
                  <div className="rounded-lg bg-white p-3 border border-rose-100">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-rose-600">Failed / Errors</p>
                    <p className="mt-1 text-lg font-mono font-extrabold text-rose-700">{job.counts.failed}</p>
                  </div>
                  <div className="rounded-lg bg-white p-3 border border-rose-100">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-rose-600">Critical Finds</p>
                    <p className="mt-1 text-lg font-mono font-extrabold text-rose-800">{job.counts.critical_findings}</p>
                  </div>
                  <div className="rounded-lg bg-white p-3 border border-slate-200">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Remaining</p>
                    <p className="mt-1 text-lg font-mono font-extrabold text-slate-600">{job.counts.remaining}</p>
                  </div>
                </div>

                {/* Job Actions Bar */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-200">
                  <div className="text-[11px] text-slate-500">
                    {job.started_at && (
                      <span>
                        Started: <strong>{new Date(job.started_at).toLocaleTimeString()}</strong>
                      </span>
                    )}
                    {job.completed_at && (
                      <span>
                        {" • "}Completed: <strong>{new Date(job.completed_at).toLocaleTimeString()}</strong>
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {job.counts.failed > 0 && !isRunning && (
                      <button
                        onClick={handleRetryFailed}
                        disabled={actionLoading}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-rose-50 border border-rose-200 px-3 py-1.5 text-xs font-bold text-rose-700 hover:bg-rose-100 transition-colors disabled:opacity-50"
                      >
                        {actionLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCw className="h-3.5 w-3.5" />}
                        Retry All Failed ({job.counts.failed})
                      </button>
                    )}

                    {isRunning ? (
                      <button
                        onClick={handleCancelJob}
                        disabled={actionLoading}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-slate-200 px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-300 transition-colors disabled:opacity-50"
                      >
                        <Ban className="h-3.5 w-3.5 text-slate-600" />
                        Cancel Job
                      </button>
                    ) : (
                      <button
                        onClick={handleStartBulkEvaluation}
                        disabled={starting || actionLoading}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-purple-900 px-3 py-1.5 text-xs font-bold text-white hover:bg-purple-800 transition-colors disabled:opacity-50"
                      >
                        {starting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                        Re-run Bulk Evaluation
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Per-Bid Items Table Section */}
              <div className="space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">Per-Bid Batch Telemetry</h4>
                    <p className="text-xs text-slate-500">
                      Isolated stage progression, scoring snapshots, and diagnostics for each submitted bid.
                    </p>
                  </div>

                  {/* Filters & Search */}
                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search bid or vendor..."
                        className="h-8 w-44 rounded-md border border-slate-300 pl-8 pr-2 text-xs text-slate-800 placeholder-slate-400 focus:border-purple-600 focus:outline-hidden"
                      />
                    </div>
                    <select
                      value={filterStatus}
                      onChange={(e) => {
                        setFilterStatus(e.target.value);
                        setCurrentPage(1);
                        if (job) loadJobItems(job.id, 1, e.target.value);
                      }}
                      className="h-8 rounded-md border border-slate-300 bg-white px-2 text-xs text-slate-700 focus:border-purple-600 focus:outline-hidden"
                    >
                      <option value="">All Statuses</option>
                      <option value="SUCCESS">Success</option>
                      <option value="REVIEW_REQUIRED">Review Required</option>
                      <option value="FAILED">Failed</option>
                      <option value="RUNNING">Running</option>
                      <option value="QUEUED">Queued</option>
                    </select>
                  </div>
                </div>

                {/* Table */}
                <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                        <tr>
                          <th className="py-3 px-4">Bidder / Organization</th>
                          <th className="py-3 px-3">Bid #</th>
                          <th className="py-3 px-3">Current Stage</th>
                          <th className="py-3 px-3">Status</th>
                          <th className="py-3 px-3 text-center">Score</th>
                          <th className="py-3 px-3 text-center">Risk</th>
                          <th className="py-3 px-3 text-center">Review</th>
                          <th className="py-3 px-3">Diagnostics / Error</th>
                          <th className="py-3 px-4 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-normal text-slate-700">
                        {filteredItems.length === 0 ? (
                          <tr>
                            <td colSpan={9} className="py-8 text-center text-xs text-slate-400 italic">
                              No bid items match the selected filter.
                            </td>
                          </tr>
                        ) : (
                          filteredItems.map((item) => (
                            <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                              <td className="py-3 px-4 font-bold text-slate-900">
                                {item.bidder_name || "Bidder Entity"}
                              </td>
                              <td className="py-3 px-3 font-mono text-[11px] text-slate-600">
                                {item.bid_number || "—"}
                              </td>
                              <td className="py-3 px-3">
                                {getStageBadge(item.current_stage)}
                              </td>
                              <td className="py-3 px-3">
                                {getStatusBadge(item.status)}
                              </td>
                              <td className="py-3 px-3 text-center font-mono font-bold text-slate-800">
                                {item.final_score !== null && item.final_score !== undefined
                                  ? `${item.final_score}%`
                                  : "—"}
                              </td>
                              <td className="py-3 px-3 text-center">
                                {item.risk_level ? (
                                  <span
                                    className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold ${
                                      item.risk_level === "LOW"
                                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                        : item.risk_level === "MEDIUM"
                                        ? "bg-blue-50 text-blue-700 border border-blue-200"
                                        : item.risk_level === "HIGH"
                                        ? "bg-amber-50 text-amber-700 border border-amber-200"
                                        : "bg-rose-50 text-rose-700 border border-rose-200"
                                    }`}
                                  >
                                    {item.risk_level}
                                  </span>
                                ) : (
                                  <span className="text-slate-400">—</span>
                                )}
                              </td>
                              <td className="py-3 px-3 text-center">
                                {item.review_required ? (
                                  <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-bold text-amber-700 border border-amber-200">
                                    <AlertCircle className="h-3 w-3 text-amber-500" />
                                    YES
                                  </span>
                                ) : (
                                  <span className="text-[10px] text-slate-400">NO</span>
                                )}
                              </td>
                              <td className="py-3 px-3 max-w-[200px] truncate text-[11px]">
                                {item.error_message ? (
                                  <span className="text-rose-600 font-medium" title={item.error_message}>
                                    {item.error_code ? `[${item.error_code}] ` : ""}{item.error_message}
                                  </span>
                                ) : item.critical_findings_count > 0 ? (
                                  <span className="text-rose-700 font-semibold flex items-center gap-1">
                                    <ShieldAlert className="h-3 w-3 text-rose-600" />
                                    {item.critical_findings_count} critical finding(s)
                                  </span>
                                ) : (
                                  <span className="text-slate-400 italic">Clean</span>
                                )}
                              </td>
                              <td className="py-3 px-4 text-right">
                                {item.status === "FAILED" && (
                                  <button
                                    onClick={() => handleRetrySingle(item.id)}
                                    disabled={retryingItemId === item.id || isRunning}
                                    className="inline-flex items-center gap-1 rounded bg-rose-50 border border-rose-200 px-2 py-1 text-[11px] font-bold text-rose-700 hover:bg-rose-100 transition-colors disabled:opacity-50"
                                    title="Retry single failed bid"
                                  >
                                    {retryingItemId === item.id ? (
                                      <Loader2 className="h-3 w-3 animate-spin" />
                                    ) : (
                                      <RotateCw className="h-3 w-3" />
                                    )}
                                    Retry
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination Footer */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-600">
                      <span>
                        Showing Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong> ({totalItemsCount} total items)
                      </span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => {
                            const prev = Math.max(1, currentPage - 1);
                            setCurrentPage(prev);
                            if (job) loadJobItems(job.id, prev);
                          }}
                          disabled={currentPage <= 1}
                          className="rounded border border-slate-300 bg-white p-1 hover:bg-slate-50 disabled:opacity-40"
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => {
                            const next = Math.min(totalPages, currentPage + 1);
                            setCurrentPage(next);
                            if (job) loadJobItems(job.id, next);
                          }}
                          disabled={currentPage >= totalPages}
                          className="rounded border border-slate-300 bg-white p-1 hover:bg-slate-50 disabled:opacity-40"
                        >
                          <ChevronRight className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-6 py-3 shrink-0">
          <p className="text-[11px] text-slate-500">
            BidVerify AI Engine: Idempotent multi-stage batch processing with isolated error boundaries.
          </p>
          <button
            onClick={onClose}
            className="rounded-lg bg-slate-200 px-4 py-2 text-xs font-bold text-slate-700 hover:bg-slate-300 transition-colors"
          >
            Close Workspace
          </button>
        </div>
      </div>
    </div>
  );
}
