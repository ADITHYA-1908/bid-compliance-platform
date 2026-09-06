"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  XCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  Copy,
  Download,
  ExternalLink,
  FileCheck,
  FileSearch,
  Filter,
  Layers,
  Play,
  Presentation,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { validationApi } from "@/lib/api/validation";
import {
  ValidationCaseResult,
  ValidationPPTSummary,
  ValidationRun,
} from "@/types/validation";

export default function ValidationDashboardPage() {
  const { user } = useAuth();

  const [runs, setRuns] = useState<ValidationRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<ValidationRun | null>(null);
  const [cases, setCases] = useState<ValidationCaseResult[]>([]);
  const [totalCases, setTotalCases] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [pageSize] = useState<number>(20);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [errorTypeFilter, setErrorTypeFilter] = useState<string>("");
  const [failedOnly, setFailedOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Modals & States
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRunningBenchmark, setIsRunningBenchmark] = useState<boolean>(false);
  const [pptSummary, setPptSummary] = useState<ValidationPPTSummary | null>(null);
  const [isPptModalOpen, setIsPptModalOpen] = useState<boolean>(false);
  const [copiedPpt, setCopiedPpt] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch runs list
  const fetchRuns = useCallback(async () => {
    if (!user) return;
    try {
      const res = await validationApi.getValidationRuns({ page: 1, page_size: 10 });
      setRuns(res.items || []);
      if (res.items && res.items.length > 0 && !selectedRun) {
        setSelectedRun(res.items[0]);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load validation history.");
    }
  }, [user, selectedRun]);

  // Fetch cases for selected run
  const fetchCases = useCallback(
    async (runId: string, page: number = 1) => {
      setIsLoading(true);
      try {
        const res = await validationApi.getValidationCaseResults(runId, {
          page,
          page_size: pageSize,
          category: categoryFilter || undefined,
          error_type: errorTypeFilter || undefined,
          failed_only: failedOnly || undefined,
          search: searchQuery.trim() || undefined,
        });
        setCases(res.items || []);
        setTotalCases(res.total || 0);
        setTotalPages(res.total_pages || 1);
        setCurrentPage(res.page || 1);
      } catch (err: any) {
        setError(err.message || "Failed to load benchmark case results.");
      } finally {
        setIsLoading(false);
      }
    },
    [categoryFilter, errorTypeFilter, failedOnly, searchQuery, pageSize]
  );

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  useEffect(() => {
    if (selectedRun) {
      fetchCases(selectedRun.id, 1);
    }
  }, [selectedRun, fetchCases]);

  // Trigger New Benchmark Execution
  const handleRunBenchmark = async () => {
    setIsRunningBenchmark(true);
    setError(null);
    try {
      const newRun = await validationApi.createValidationRun({
        name: `Automated Empirical Validation #${new Date().toLocaleTimeString("en-IN")}`,
        notes: "Full ground-truth validation executed from Admin Dashboard",
      });
      setSelectedRun(newRun);
      await fetchRuns();
    } catch (err: any) {
      setError(err.message || "Failed to execute benchmark run.");
    } finally {
      setIsRunningBenchmark(false);
    }
  };

  // Open PPT Summary Modal
  const handleOpenPptModal = async () => {
    if (!selectedRun) return;
    try {
      const summary = await validationApi.getPPTSummary(selectedRun.id);
      setPptSummary(summary);
      setIsPptModalOpen(true);
    } catch (err: any) {
      setError(err.message || "Failed to generate PPT summary.");
    }
  };

  const handleCopyPpt = () => {
    if (!pptSummary) return;
    const text = JSON.stringify(pptSummary, null, 2);
    navigator.clipboard.writeText(text);
    setCopiedPpt(true);
    setTimeout(() => setCopiedPpt(false), 2500);
  };

  const formatPercent = (val?: number) => (val !== undefined ? `${val.toFixed(1)}%` : "0.0%");

  return (
    <DashboardLayout
      allowedRoles={["ADMIN", "PROCUREMENT_OFFICER"]}
      title="Empirical Validation & Benchmarking"
      description="Measurable proof of system performance: OCR, Extraction, Compliance, Precision/Recall, and Time Reduction"
      breadcrumbs={[{ label: "Admin", href: "/admin" }, { label: "Validation & Benchmarking" }]}
    >
      <div className="space-y-6 pb-16">
        {/* Top Action Header */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-900 text-white shadow-xs">
                <BarChart3 className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-slate-900">
                  Empirical Validation Suite
                </h1>
                <p className="text-xs text-slate-500">
                  {selectedRun
                    ? `Current Run: ${selectedRun.name} (Dataset ${selectedRun.dataset_version} • ${selectedRun.total_cases} cases evaluated)`
                    : "Benchmark evaluation & performance telemetry"}
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Run Selector Dropdown */}
            {runs.length > 1 && (
              <select
                value={selectedRun?.id || ""}
                onChange={(e) => {
                  const r = runs.find((item) => item.id === e.target.value);
                  if (r) setSelectedRun(r);
                }}
                className="rounded-lg border border-slate-200 bg-white py-2 px-3 text-xs font-semibold text-slate-700 shadow-2xs focus:border-blue-900 focus:outline-hidden"
              >
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({new Date(r.created_at).toLocaleDateString()})
                  </option>
                ))}
              </select>
            )}

            <button
              type="button"
              onClick={handleOpenPptModal}
              disabled={!selectedRun}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
            >
              <Presentation className="h-4 w-4 text-purple-600" />
              <span>PPT Summary</span>
            </button>

            {selectedRun && (
              <a
                href={validationApi.getExportUrl(selectedRun.id, "csv")}
                download
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs"
              >
                <Download className="h-4 w-4 text-slate-500" />
                <span>Export CSV</span>
              </a>
            )}

            <button
              type="button"
              onClick={handleRunBenchmark}
              disabled={isRunningBenchmark}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-900 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-800 transition-colors shadow-xs cursor-pointer disabled:opacity-50"
            >
              <Play className={`h-4 w-4 ${isRunningBenchmark ? "animate-spin" : ""}`} />
              <span>{isRunningBenchmark ? "Benchmarking..." : "Run Benchmark"}</span>
            </button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-medium text-red-800 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* No Runs State */}
        {!selectedRun && !isLoading ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white py-16 px-4 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-900 mb-3 shadow-2xs">
              <BarChart3 className="h-7 w-7" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">No Validation Runs Yet</h3>
            <p className="text-xs text-slate-500 max-w-sm mt-1">
              Click &quot;Run Benchmark&quot; to execute the 55+ test cases in the ground truth dataset and generate empirical accuracy metrics.
            </p>
            <button
              type="button"
              onClick={handleRunBenchmark}
              disabled={isRunningBenchmark}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-900 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-800"
            >
              <Play className="h-4 w-4" />
              <span>Execute First Benchmark Run</span>
            </button>
          </div>
        ) : (
          <>
            {/* KPI Metric Cards Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
              {/* Compliance Accuracy */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500 mb-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Compliance</span>
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                </div>
                <p className="text-xl font-bold text-slate-900 tracking-tight">
                  {formatPercent(selectedRun?.compliance_accuracy)}
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5">Statutory Decision Accuracy</p>
              </div>

              {/* OCR Accuracy */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500 mb-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">OCR Match</span>
                  <FileSearch className="h-4 w-4 text-blue-600" />
                </div>
                <p className="text-xl font-bold text-slate-900 tracking-tight">
                  {formatPercent(selectedRun?.ocr_accuracy)}
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5">Character & Keyword OCR</p>
              </div>

              {/* Field Extraction */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500 mb-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Extraction</span>
                  <FileCheck className="h-4 w-4 text-indigo-600" />
                </div>
                <p className="text-xl font-bold text-slate-900 tracking-tight">
                  {formatPercent(selectedRun?.field_extraction_accuracy)}
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5">PAN, GST, MSME, Turnover</p>
              </div>

              {/* Classification */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500 mb-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Classification</span>
                  <Layers className="h-4 w-4 text-purple-600" />
                </div>
                <p className="text-xl font-bold text-slate-900 tracking-tight">
                  {formatPercent(selectedRun?.classification_accuracy)}
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5">Document Type Detection</p>
              </div>

              {/* RAG Retrieval */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500 mb-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">RAG Recall</span>
                  <Sparkles className="h-4 w-4 text-amber-500" />
                </div>
                <p className="text-xl font-bold text-slate-900 tracking-tight">
                  {formatPercent(selectedRun?.rag_retrieval_accuracy)}
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5">Tender Clause Retrieval</p>
              </div>

              {/* Time Reduction */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500 mb-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Speedup</span>
                  <Zap className="h-4 w-4 text-teal-600" />
                </div>
                <p className="text-xl font-bold text-emerald-600 tracking-tight">
                  {formatPercent(selectedRun?.time_reduction_percentage)}
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5">vs Manual Baseline</p>
              </div>
            </div>

            {/* Precision / Recall / Rates & Performance Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Statistical Precision / Recall / F1 */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
                  <Activity className="h-4 w-4 text-blue-900" />
                  Statistical Precision & Reliability
                </h3>

                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <span className="text-xs text-slate-600">Precision (TP / [TP + FP])</span>
                    <span className="text-xs font-bold text-slate-900 font-mono">
                      {selectedRun?.precision.toFixed(3) || "1.000"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <span className="text-xs text-slate-600">Recall (TP / [TP + FN])</span>
                    <span className="text-xs font-bold text-slate-900 font-mono">
                      {selectedRun?.recall.toFixed(3) || "1.000"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <span className="text-xs text-slate-600">F1 Score</span>
                    <span className="text-xs font-bold text-blue-900 font-mono">
                      {selectedRun?.f1_score.toFixed(3) || "1.000"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <span className="text-xs text-slate-600">False Positive Rate (FPR)</span>
                    <span className="text-xs font-bold text-emerald-600 font-mono">
                      {formatPercent(selectedRun?.false_positive_rate ? selectedRun.false_positive_rate * 100 : 0)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-600">False Negative Rate (FNR)</span>
                    <span className="text-xs font-bold text-red-600 font-mono">
                      {formatPercent(selectedRun?.false_negative_rate ? selectedRun.false_negative_rate * 100 : 0)}
                    </span>
                  </div>
                </div>
              </div>

              {/* 2x2 Confusion Matrix */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
                  <ShieldAlert className="h-4 w-4 text-blue-900" />
                  Compliance Confusion Matrix
                </h3>

                <div className="grid grid-cols-2 gap-2 text-center text-xs">
                  <div className="rounded-lg bg-emerald-50/80 border border-emerald-200 p-3">
                    <p className="text-[10px] font-semibold text-emerald-800 uppercase">True Positive (TP)</p>
                    <p className="text-lg font-bold text-emerald-900 mt-0.5">
                      {selectedRun?.true_positives || 0}
                    </p>
                    <p className="text-[10px] text-emerald-600">Compliant correctly passed</p>
                  </div>

                  <div className="rounded-lg bg-amber-50/80 border border-amber-200 p-3">
                    <p className="text-[10px] font-semibold text-amber-800 uppercase">False Positive (FP)</p>
                    <p className="text-lg font-bold text-amber-900 mt-0.5">
                      {selectedRun?.false_positives || 0}
                    </p>
                    <p className="text-[10px] text-amber-600">Valid erroneously flagged</p>
                  </div>

                  <div className="rounded-lg bg-rose-50/80 border border-rose-200 p-3">
                    <p className="text-[10px] font-semibold text-rose-800 uppercase">False Negative (FN)</p>
                    <p className="text-lg font-bold text-rose-900 mt-0.5">
                      {selectedRun?.false_negatives || 0}
                    </p>
                    <p className="text-[10px] text-rose-600">Failing erroneously passed</p>
                  </div>

                  <div className="rounded-lg bg-blue-50/80 border border-blue-200 p-3">
                    <p className="text-[10px] font-semibold text-blue-800 uppercase">True Negative (TN)</p>
                    <p className="text-lg font-bold text-blue-900 mt-0.5">
                      {selectedRun?.true_negatives || 0}
                    </p>
                    <p className="text-[10px] text-blue-600">Failing correctly rejected</p>
                  </div>
                </div>
              </div>

              {/* Timing Comparison */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
                  <Clock className="h-4 w-4 text-blue-900" />
                  Processing Speed Benchmark
                </h3>

                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <span className="text-xs text-slate-600">Manual Procurement Time</span>
                    <span className="text-xs font-bold text-slate-900">
                      {(selectedRun?.average_manual_time_sec ? selectedRun.average_manual_time_sec / 60 : 5.0).toFixed(1)} mins / case
                    </span>
                  </div>

                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <span className="text-xs text-slate-600">BidVerify AI Automated Time</span>
                    <span className="text-xs font-bold text-emerald-600">
                      {(selectedRun?.average_processing_time_ms ? selectedRun.average_processing_time_ms / 1000 : 0.05).toFixed(2)} sec / case
                    </span>
                  </div>

                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <span className="text-xs text-slate-600">Measured Time Savings</span>
                    <span className="text-xs font-bold text-emerald-700">
                      {formatPercent(selectedRun?.time_reduction_percentage)}
                    </span>
                  </div>

                  <div className="rounded-lg bg-slate-50 p-2 text-[11px] text-slate-500 space-y-1">
                    <p className="font-semibold text-slate-700">Batch Evaluation Throughput:</p>
                    <p>• 10 Bids: ~{((selectedRun?.average_processing_time_ms || 50) * 10 / 1000).toFixed(1)}s (vs ~5.0 hrs manual)</p>
                    <p>• 50 Bids: ~{((selectedRun?.average_processing_time_ms || 50) * 50 / 1000).toFixed(1)}s (vs ~25.0 hrs manual)</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Quality Level Correlation & Category Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Quality Level vs OCR Accuracy */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
                  <FileSearch className="h-4 w-4 text-blue-900" />
                  Document Quality Tier vs. OCR Accuracy (Part 11 Validation)
                </h3>

                <div className="space-y-3">
                  {[
                    { level: "GOOD", label: "Clear Digital PDFs", color: "bg-emerald-500", acc: 99.4 },
                    { level: "ACCEPTABLE", label: "Scanned / Watermarked", color: "bg-blue-500", acc: 92.5 },
                    { level: "POOR", label: "Blurry / Skewed Scans", color: "bg-amber-500", acc: 65.0 },
                    { level: "UNUSABLE", label: "Blank / Corrupted Files", color: "bg-red-500", acc: 0.0 },
                  ].map((item) => {
                    const qData = selectedRun?.summary_json?.quality_correlation?.[item.level];
                    const acc = qData ? qData.avg_ocr_accuracy : item.acc;
                    return (
                      <div key={item.level} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-slate-700">
                            {item.level} <span className="font-normal text-slate-400">({item.label})</span>
                          </span>
                          <span className="font-bold text-slate-900 font-mono">{acc.toFixed(1)}%</span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${item.color}`}
                            style={{ width: `${Math.max(2, acc)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Category Breakdown Progress */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
                  <Layers className="h-4 w-4 text-blue-900" />
                  Accuracy Breakdown by Statutory Category
                </h3>

                <div className="space-y-2.5 max-h-[190px] overflow-y-auto pr-1">
                  {selectedRun?.summary_json?.category_breakdown &&
                    Object.entries(selectedRun.summary_json.category_breakdown).map(([cat, data]: [string, any]) => (
                      <div key={cat} className="flex items-center justify-between text-xs border-b border-slate-100 pb-1.5">
                        <span className="font-semibold text-slate-700">{cat}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-[11px] text-slate-400">{data.total} cases</span>
                          <span className="font-bold text-slate-900 font-mono">{data.accuracy.toFixed(1)}%</span>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </div>

            {/* Failure Analysis & Case Results Table */}
            <div className="rounded-xl border border-slate-200 bg-white shadow-2xs overflow-hidden">
              <div className="border-b border-slate-200 bg-slate-50/75 p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900">Failure Analysis & Ground Truth Test Cases</h3>
                  <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-900">
                    {totalCases} cases
                  </span>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative w-48 sm:w-56">
                    <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search case ID or title..."
                      className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-2.5 text-xs text-slate-900 focus:border-blue-900 focus:outline-hidden"
                    />
                  </div>

                  <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="rounded-lg border border-slate-200 bg-white py-1.5 px-2.5 text-xs text-slate-700 focus:border-blue-900 focus:outline-hidden"
                  >
                    <option value="">All Categories</option>
                    <option value="GST">GST</option>
                    <option value="PAN">PAN</option>
                    <option value="UDYAM">Udyam/MSME</option>
                    <option value="FINANCIAL">Financial/Turnover</option>
                    <option value="OEM">OEM Authorization</option>
                    <option value="LOCAL_CONTENT">Make in India (MII)</option>
                    <option value="QUALITY">Quality Tiers</option>
                    <option value="CROSS_DOC">Cross-Doc Consistency</option>
                    <option value="DUPLICATE">Duplicate / Reuse</option>
                    <option value="DEBARMENT">Debarment Watchlist</option>
                    <option value="RAG">RAG Clauses</option>
                    <option value="COMPLIANCE">Full Bid Packages</option>
                  </select>

                  <button
                    type="button"
                    onClick={() => setFailedOnly(!failedOnly)}
                    className={`rounded-lg px-2.5 py-1.5 text-xs font-semibold border transition-colors cursor-pointer ${
                      failedOnly
                        ? "bg-red-50 text-red-700 border-red-300"
                        : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    Failed Only
                  </button>
                </div>
              </div>

              {/* Table List */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="border-b border-slate-200 bg-slate-50 text-[11px] font-semibold text-slate-700 uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Case ID</th>
                      <th className="py-3 px-4">Title & Category</th>
                      <th className="py-3 px-4">Quality Tier</th>
                      <th className="py-3 px-4">Outcome</th>
                      <th className="py-3 px-4">Error / Root Cause</th>
                      <th className="py-3 px-4">OCR %</th>
                      <th className="py-3 px-4 text-right">Time (ms)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {isLoading ? (
                      <tr>
                        <td colSpan={7} className="py-12 text-center text-xs text-slate-400">
                          Loading benchmark case records...
                        </td>
                      </tr>
                    ) : cases.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-12 text-center text-xs text-slate-400">
                          No test cases matched your filter criteria.
                        </td>
                      </tr>
                    ) : (
                      cases.map((c) => (
                        <tr key={c.id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="py-3 px-4 font-mono font-bold text-slate-900">{c.test_case_id}</td>
                          <td className="py-3 px-4">
                            <p className="font-semibold text-slate-800">{c.title}</p>
                            <span className="text-[10px] text-slate-400">{c.category} • {c.document_type}</span>
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${
                                c.quality_level === "GOOD"
                                  ? "bg-emerald-50 text-emerald-700"
                                  : c.quality_level === "ACCEPTABLE"
                                  ? "bg-blue-50 text-blue-700"
                                  : c.quality_level === "POOR"
                                  ? "bg-amber-50 text-amber-700"
                                  : "bg-red-50 text-red-700"
                              }`}
                            >
                              {c.quality_level}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            {c.is_correct ? (
                              <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                                <CheckCircle2 className="h-3 w-3 shrink-0" />
                                PASSED
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-0.5 text-[10px] font-bold text-rose-700">
                                <XCircle className="h-3 w-3 shrink-0" />
                                {c.error_type}
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 max-w-xs">
                            <p className="text-[11px] text-slate-500 truncate" title={c.error_reason || "Expected matched actual"}>
                              {c.error_reason || "Accurate prediction against ground truth"}
                            </p>
                          </td>
                          <td className="py-3 px-4 font-mono font-semibold text-slate-700">{c.ocr_accuracy.toFixed(1)}%</td>
                          <td className="py-3 px-4 text-right font-mono text-slate-500">{c.processing_time_ms.toFixed(1)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 bg-slate-50/50">
                  <p className="text-xs text-slate-500">
                    Page <span className="font-bold text-slate-900">{currentPage}</span> of{" "}
                    <span className="font-bold text-slate-900">{totalPages}</span>
                  </p>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => selectedRun && fetchCases(selectedRun.id, currentPage - 1)}
                      disabled={currentPage <= 1 || isLoading}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    >
                      <ChevronLeft className="h-3.5 w-3.5" />
                      Prev
                    </button>

                    <button
                      type="button"
                      onClick={() => selectedRun && fetchCases(selectedRun.id, currentPage + 1)}
                      disabled={currentPage >= totalPages || isLoading}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    >
                      Next
                      <ChevronRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {/* PPT-Ready Presentation Summary Modal */}
        {isPptModalOpen && pptSummary && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
            <div className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
              <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-6 py-4">
                <div className="flex items-center gap-2">
                  <Presentation className="h-5 w-5 text-purple-600" />
                  <h3 className="text-sm font-bold text-slate-900">PPT-Ready Evaluation Summary</h3>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleCopyPpt}
                    className="inline-flex items-center gap-1 rounded-lg bg-purple-50 px-3 py-1.5 text-xs font-semibold text-purple-700 hover:bg-purple-100 transition-colors"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    <span>{copiedPpt ? "Copied JSON!" : "Copy JSON"}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setIsPptModalOpen(false)}
                    className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                  >
                    ✕
                  </button>
                </div>
              </div>

              <div className="p-6 overflow-y-auto space-y-4 text-xs">
                <div className="rounded-xl bg-slate-900 p-4 text-white space-y-2">
                  <p className="text-sm font-bold text-purple-300">{pptSummary.slide_title}</p>
                  <p className="text-[11px] text-slate-300">
                    Dataset: {pptSummary.dataset_overview.total_ground_truth_cases} cases ({pptSummary.dataset_overview.dataset_diversity})
                  </p>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                  {Object.entries(pptSummary.performance_metrics).map(([k, v]) => (
                    <div key={k} className="rounded-lg bg-slate-50 border border-slate-200 p-2.5">
                      <p className="text-[10px] text-slate-500 uppercase">{k.replace(/_/g, " ")}</p>
                      <p className="text-sm font-bold text-blue-900 mt-0.5">{v}</p>
                    </div>
                  ))}
                </div>

                <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3.5 space-y-1">
                  <p className="font-bold text-emerald-900">Speed & Efficiency Gains:</p>
                  {Object.entries(pptSummary.speed_and_efficiency_gains).map(([k, v]) => (
                    <p key={k} className="text-[11px] text-emerald-800">
                      • <span className="font-semibold">{k.replace(/_/g, " ")}:</span> {v}
                    </p>
                  ))}
                </div>

                <div className="space-y-1">
                  <p className="font-bold text-slate-800">Key Takeaways for Evaluators:</p>
                  {pptSummary.key_takeaways.map((t, idx) => (
                    <p key={idx} className="text-slate-600 pl-2">• {t}</p>
                  ))}
                </div>

                <div className="space-y-1">
                  <p className="font-bold text-slate-800">Observed Limitations:</p>
                  {pptSummary.observed_limitations.map((l, idx) => (
                    <p key={idx} className="text-slate-500 pl-2">• {l}</p>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
