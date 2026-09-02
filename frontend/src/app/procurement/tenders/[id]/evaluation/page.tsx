"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  getTenderBidEvaluations,
} from "@/lib/api/procurement_dashboard";
import {
  BidEvaluationListItem,
  TenderBidEvaluationsListResponse,
  TenderBidEvaluationsQueryParams,
} from "@/types/procurement_dashboard";
import {
  FileText,
  Building2,
  CheckCircle2,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  AlertCircle,
  Clock,
  Search,
  RefreshCw,
  ArrowUpDown,
  Filter,
  Eye,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Bot,
  Layers,
  Activity,
  SlidersHorizontal,
  DollarSign,
  AlertOctagon,
  BookmarkCheck,
  CheckSquare,
  Square,
  X,
  XCircle,
  MinusCircle,
  Play,
} from "lucide-react";
import { BulkEvaluationModal } from "@/components/procurement/BulkEvaluationModal";

export default function TenderEvaluationWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const tenderId = params?.id as string;

  const [data, setData] = useState<TenderBidEvaluationsListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [bulkModalOpen, setBulkModalOpen] = useState<boolean>(false);

  // Selection states for side-by-side comparison
  const [selectedBidIds, setSelectedBidIds] = useState<string[]>([]);

  // Filter & Search states
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [riskLevelFilter, setRiskLevelFilter] = useState<string>("");
  const [reviewRequiredFilter, setReviewRequiredFilter] = useState<boolean | undefined>(undefined);
  const [criticalOnlyFilter, setCriticalOnlyFilter] = useState<boolean>(false);
  const [recommendationFilter, setRecommendationFilter] = useState<string>("");
  const [shortlistedOnlyFilter, setShortlistedOnlyFilter] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<"submitted_at" | "score" | "risk" | "review_count" | "critical_count">("submitted_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  const toggleBidSelection = (bidId: string) => {
    if (selectedBidIds.includes(bidId)) {
      setSelectedBidIds(selectedBidIds.filter((id) => id !== bidId));
    } else {
      if (selectedBidIds.length >= 5) {
        alert("A maximum of 5 bids can be selected for comparison simultaneously.");
        return;
      }
      setSelectedBidIds([...selectedBidIds, bidId]);
    }
  };

  const loadEvaluations = async (page = currentPage) => {
    if (!tenderId) return;
    setLoading(true);
    setError(null);
    try {
      const queryParams: TenderBidEvaluationsQueryParams = {
        search: searchTerm || undefined,
        status: statusFilter || undefined,
        risk_level: riskLevelFilter || undefined,
        review_required: reviewRequiredFilter,
        critical_only: criticalOnlyFilter || undefined,
        recommendation: recommendationFilter || undefined,
        shortlisted_only: shortlistedOnlyFilter || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
        page: page,
        page_size: pageSize,
      };

      const resp = await getTenderBidEvaluations(tenderId, queryParams);
      setData(resp);
      setCurrentPage(resp.page);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err.message ||
          "Failed to load tender bid evaluation matrix."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvaluations(1);
  }, [
    tenderId,
    statusFilter,
    riskLevelFilter,
    reviewRequiredFilter,
    criticalOnlyFilter,
    recommendationFilter,
    shortlistedOnlyFilter,
    sortBy,
    sortDir,
    pageSize,
  ]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadEvaluations(1);
  };

  const getRiskBadge = (level?: string | null, score?: number | null, isProv?: boolean) => {
    if (!level) {
      return (
        <span className="inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-[11px] font-mono text-slate-500">
          NOT_CALCULATED
        </span>
      );
    }
    const scoreStr = score !== null && score !== undefined ? ` (${score.toFixed(1)})` : "";
    switch (level.toUpperCase()) {
      case "LOW":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-800 border border-emerald-200">
            <ShieldCheck className="h-3 w-3 text-emerald-600" />
            LOW{scoreStr}
            {isProv && <span className="text-[9px] font-normal text-emerald-700">(Prov.)</span>}
          </span>
        );
      case "MEDIUM":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-800 border border-blue-200">
            <ShieldCheck className="h-3 w-3 text-blue-600" />
            MEDIUM{scoreStr}
            {isProv && <span className="text-[9px] font-normal text-blue-700">(Prov.)</span>}
          </span>
        );
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-800 border border-amber-200">
            <AlertTriangle className="h-3 w-3 text-amber-600" />
            HIGH{scoreStr}
            {isProv && <span className="text-[9px] font-normal text-amber-700">(Prov.)</span>}
          </span>
        );
      case "CRITICAL":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-0.5 text-[11px] font-bold text-rose-800 border border-rose-200">
            <ShieldAlert className="h-3 w-3 text-rose-600" />
            CRITICAL{scoreStr}
            {isProv && <span className="text-[9px] font-normal text-rose-700">(Prov.)</span>}
          </span>
        );
      default:
        return <span className="text-slate-600 text-xs font-mono">{level}</span>;
    }
  };

  const getEvaluationStatusBadge = (status: string) => {
    switch (status) {
      case "EVALUATION_COMPLETE":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="h-2.5 w-2.5 text-emerald-600" />
            COMPLETE
          </span>
        );
      case "REVIEW_REQUIRED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200">
            <AlertCircle className="h-2.5 w-2.5 text-amber-600" />
            REVIEW REQ.
          </span>
        );
      case "PROVISIONAL":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-800 border border-indigo-200">
            <Clock className="h-2.5 w-2.5 text-indigo-600" />
            PROVISIONAL
          </span>
        );
      case "AI_STALE":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-purple-50 px-2 py-0.5 text-[10px] font-semibold text-purple-800 border border-purple-200">
            <Sparkles className="h-2.5 w-2.5 text-purple-600" />
            AI STALE
          </span>
        );
      case "NOT_STARTED":
      case "PROCESSING":
      default:
        return (
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600 border border-slate-200">
            {status}
          </span>
        );
    }
  };

  const getAIRecBadge = (rec?: string | null, aiStatus?: string) => {
    if (aiStatus === "STALE") {
      return (
        <span className="inline-flex items-center gap-1 rounded bg-purple-50 px-2 py-0.5 text-[10px] font-medium text-purple-800 border border-purple-200" title="Recommendation is stale relative to upstream scores">
          <Sparkles className="h-2.5 w-2.5 text-purple-600" />
          AI Stale
        </span>
      );
    }
    if (!rec || aiStatus === "NOT_GENERATED" || aiStatus === "UNAVAILABLE") {
      return (
        <span className="text-[11px] text-slate-400 italic">
          {aiStatus === "UNAVAILABLE" ? "AI Unavailable" : "Not Generated"}
        </span>
      );
    }

    switch (rec.toUpperCase()) {
      case "PROCEED":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="h-2.5 w-2.5 text-emerald-600" />
            PROCEED
          </span>
        );
      case "PROCEED_WITH_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-800 border border-blue-200">
            PROCEED W/ REV.
          </span>
        );
      case "REVIEW_REQUIRED":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200">
            REVIEW REQ.
          </span>
        );
      case "DO_NOT_PROCEED_WITHOUT_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-rose-50 px-2 py-0.5 text-[10px] font-bold text-rose-800 border border-rose-200">
            DO NOT PROCEED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-700">
            {rec}
          </span>
        );
    }
  };

  const getDecisionBadge = (status?: string | null) => {
    switch (status) {
      case "QUALIFIED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="h-2.5 w-2.5 text-emerald-600" />
            QUALIFIED
          </span>
        );
      case "DISQUALIFIED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-[10px] font-bold text-rose-800 border border-rose-200">
            <XCircle className="h-2.5 w-2.5 text-rose-600" />
            DISQUALIFIED
          </span>
        );
      case "UNDER_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200">
            <Clock className="h-2.5 w-2.5 text-amber-600" />
            UNDER REVIEW
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-medium text-slate-600 border border-slate-200">
            <MinusCircle className="h-2.5 w-2.5 text-slate-400" />
            NOT DECIDED
          </span>
        );
    }
  };

  const progressPercentage =
    data && data.total_submitted_bids > 0
      ? Math.round((data.evaluated_bids / data.total_submitted_bids) * 100)
      : 0;

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Tender Bid Evaluation Matrix"
      description="Inspect submitted bids, evaluate clause compliance contributions, and verify deterministic risk scores."
      breadcrumbs={[
        { label: "Procurement Portal", href: "/procurement" },
        { label: "Tenders", href: "/procurement/tenders" },
        { label: data?.tender_number || "Tender", href: `/procurement/tenders/${tenderId}` },
        { label: "Evaluations" },
      ]}
    >
      <div className="space-y-6">
        {/* Tender Header Banner */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs font-bold text-purple-900 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                  {data?.tender_number || "TENDER"}
                </span>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border ${
                    data?.tender_status === "OPEN"
                      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                      : "bg-indigo-50 text-indigo-800 border-indigo-200"
                  }`}
                >
                  {data?.tender_status || "ACTIVE"}
                </span>
                <span className="text-xs text-slate-500">
                  • {data?.procurement_organization_name}
                </span>
              </div>

              <h2 className="text-xl font-bold text-slate-900">
                {data?.tender_title || "Loading Tender Details..."}
              </h2>

              <p className="text-xs text-slate-500">
                Total Submitted Bids:{" "}
                <span className="font-bold text-slate-800 font-mono">
                  {data?.total_submitted_bids ?? 0}
                </span>{" "}
                • Evaluated:{" "}
                <span className="font-bold text-purple-900 font-mono">
                  {data?.evaluated_bids ?? 0}
                </span>{" "}
                {data?.submission_end_date && (
                  <span>
                    • Deadline:{" "}
                    <span className="font-medium text-slate-700">
                      {new Date(data.submission_end_date).toLocaleDateString()}
                    </span>
                  </span>
                )}
              </p>
            </div>

            {/* Header Right Actions */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
              {/* Duplicate Detection Alerts Button */}
              <Link
                href={`/procurement/tenders/${tenderId}/duplicates`}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-amber-500/10 px-4 py-3 text-xs font-bold text-amber-700 hover:bg-amber-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] border border-amber-300 shadow-xs"
              >
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                <span>Duplicate / Reuse Alerts</span>
              </Link>

              {/* Process Submitted Bids Button */}
              <button
                type="button"
                onClick={() => setBulkModalOpen(true)}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-purple-900 px-4 py-3 text-xs font-bold text-white shadow-md shadow-purple-950/20 hover:bg-purple-800 transition-all hover:scale-[1.02] active:scale-[0.98] border border-purple-800"
              >
                <Layers className="h-4 w-4 text-purple-200" />
                <span>Process Submitted Bids</span>
              </button>

              {/* Evaluation Progress Card */}
              <div
                onClick={() => setBulkModalOpen(true)}
                className="w-full sm:w-64 rounded-xl border border-slate-200 bg-slate-50/90 p-3.5 cursor-pointer hover:bg-purple-50/50 hover:border-purple-200 transition-all group"
                title="Click to view bulk verification workspace"
              >
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-semibold text-slate-700 flex items-center gap-1.5 group-hover:text-purple-900 transition-colors">
                    <Activity className="h-3.5 w-3.5 text-purple-900" />
                    Evaluation Progress
                  </span>
                  <span className="font-mono font-bold text-purple-900">
                    {progressPercentage}%
                  </span>
                </div>
                <div className="h-2.5 w-full rounded-full bg-slate-200 overflow-hidden border border-slate-300">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      progressPercentage === 100
                        ? "bg-emerald-600"
                        : progressPercentage > 0
                        ? "bg-purple-700"
                        : "bg-slate-300"
                    }`}
                    style={{ width: `${progressPercentage}%` }}
                  />
                </div>
                <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-500">
                  <span>
                    <strong className="text-slate-800">{data?.evaluated_bids ?? 0}</strong> of{" "}
                    <strong className="text-slate-800">{data?.total_submitted_bids ?? 0}</strong> complete
                  </span>
                  <span className="text-purple-900 font-semibold group-hover:underline flex items-center gap-0.5">
                    Batch →
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
            <div className="flex-1 text-xs text-red-800">
              <p className="font-bold">Failed to load bid evaluations</p>
              <p className="mt-0.5">{error}</p>
            </div>
            <button
              onClick={() => loadEvaluations(currentPage)}
              className="text-xs font-semibold text-red-700 underline hover:text-red-900"
            >
              Retry
            </button>
          </div>
        )}

        {/* Filters, Search & Sorting Bar */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs space-y-3">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            {/* Search Input */}
            <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search Bidder name, Bid #, PAN, GSTIN..."
                className="h-9 w-full rounded-md border border-slate-300 bg-white pl-9 pr-20 text-xs text-slate-800 placeholder-slate-400 focus:border-purple-600 focus:outline-hidden focus:ring-1 focus:ring-purple-600"
              />
              <button
                type="submit"
                className="absolute right-1.5 top-1.5 h-6 rounded bg-slate-100 px-2 text-[10px] font-semibold text-slate-700 hover:bg-slate-200 transition-colors"
              >
                Search
              </button>
            </form>

            {/* Quick Actions / Reset */}
            <div className="flex items-center gap-2 self-end md:self-center">
              <button
                onClick={() => {
                  setSearchTerm("");
                  setStatusFilter("");
                  setRiskLevelFilter("");
                  setReviewRequiredFilter(undefined);
                  setCriticalOnlyFilter(false);
                  setRecommendationFilter("");
                  setSortBy("submitted_at");
                  setSortDir("desc");
                }}
                className="h-9 rounded-md border border-slate-300 bg-white px-3 text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors"
              >
                Reset Filters
              </button>
              <button
                onClick={() => loadEvaluations(currentPage)}
                disabled={loading}
                className="h-9 inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-purple-600" : ""}`} />
                Refresh
              </button>
            </div>
          </div>

          {/* Filter Dropdowns Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 pt-2 border-t border-slate-100 text-xs">
            {/* Status Filter */}
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Evaluation Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-8 w-full rounded border border-slate-300 bg-white px-2 text-xs text-slate-700 focus:border-purple-600 focus:outline-hidden"
              >
                <option value="">All Statuses</option>
                <option value="EVALUATION_COMPLETE">Complete</option>
                <option value="REVIEW_REQUIRED">Review Required</option>
                <option value="PROVISIONAL">Provisional</option>
                <option value="AI_STALE">AI Stale</option>
                <option value="NOT_STARTED">Not Started</option>
              </select>
            </div>

            {/* Risk Level Filter */}
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Adjusted Risk
              </label>
              <select
                value={riskLevelFilter}
                onChange={(e) => setRiskLevelFilter(e.target.value)}
                className="h-8 w-full rounded border border-slate-300 bg-white px-2 text-xs text-slate-700 focus:border-purple-600 focus:outline-hidden"
              >
                <option value="">All Risk Levels</option>
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </div>

            {/* Human Review Filter */}
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Human Review
              </label>
              <select
                value={reviewRequiredFilter === undefined ? "" : String(reviewRequiredFilter)}
                onChange={(e) => {
                  const val = e.target.value;
                  setReviewRequiredFilter(val === "" ? undefined : val === "true");
                }}
                className="h-8 w-full rounded border border-slate-300 bg-white px-2 text-xs text-slate-700 focus:border-purple-600 focus:outline-hidden"
              >
                <option value="">All Bids</option>
                <option value="true">Review Required Only</option>
                <option value="false">Clear Bids Only</option>
              </select>
            </div>

            {/* Critical Findings Filter */}
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Critical Findings
              </label>
              <select
                value={criticalOnlyFilter ? "true" : "false"}
                onChange={(e) => setCriticalOnlyFilter(e.target.value === "true")}
                className="h-8 w-full rounded border border-slate-300 bg-white px-2 text-xs text-slate-700 focus:border-purple-600 focus:outline-hidden"
              >
                <option value="false">All Bids</option>
                <option value="true">Critical Findings Only</option>
              </select>
            </div>

            {/* Shortlist Filter */}
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Shortlist Status
              </label>
              <select
                value={shortlistedOnlyFilter ? "true" : "false"}
                onChange={(e) => setShortlistedOnlyFilter(e.target.value === "true")}
                className="h-8 w-full rounded border border-slate-300 bg-white px-2 text-xs text-slate-700 focus:border-purple-600 focus:outline-hidden"
              >
                <option value="false">All Bids</option>
                <option value="true">Shortlisted Only</option>
              </select>
            </div>

            {/* AI Recommendation Filter */}
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                AI Recommendation
              </label>
              <select
                value={recommendationFilter}
                onChange={(e) => setRecommendationFilter(e.target.value)}
                className="h-8 w-full rounded border border-slate-300 bg-white px-2 text-xs text-slate-700 focus:border-purple-600 focus:outline-hidden"
              >
                <option value="">All Recommendations</option>
                <option value="PROCEED">Proceed</option>
                <option value="PROCEED_WITH_REVIEW">Proceed w/ Review</option>
                <option value="REVIEW_REQUIRED">Review Required</option>
                <option value="DO_NOT_PROCEED_WITHOUT_REVIEW">Do Not Proceed</option>
              </select>
            </div>

            {/* Sort Dropdown */}
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Sort By
              </label>
              <div className="flex items-center gap-1">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="h-8 w-full rounded border border-slate-300 bg-white px-2 text-xs text-slate-700 focus:border-purple-600 focus:outline-hidden"
                >
                  <option value="submitted_at">Submission Date</option>
                  <option value="score">Compliance Score</option>
                  <option value="risk">Adjusted Risk</option>
                  <option value="review_count">Review Count</option>
                  <option value="critical_count">Critical Defects</option>
                </select>
                <button
                  type="button"
                  onClick={() => setSortDir(sortDir === "asc" ? "desc" : "asc")}
                  className="h-8 w-8 shrink-0 flex items-center justify-center rounded border border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-600"
                  title={`Toggle sort order (${sortDir.toUpperCase()})`}
                >
                  <ArrowUpDown className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Bid Evaluations Main Table */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
          <div className="border-b border-slate-200 p-4 flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Layers className="h-4 w-4 text-purple-900" />
              Submitted Bids Evaluation Matrix ({data?.total_count ?? 0})
            </h3>
            <div className="flex items-center gap-3">
              {selectedBidIds.length >= 2 && (
                <Link
                  href={`/procurement/tenders/${tenderId}/compare?bids=${selectedBidIds.join(",")}`}
                  className="inline-flex items-center gap-1.5 rounded-md bg-purple-900 px-2.5 py-1 text-xs font-bold text-white hover:bg-purple-800 transition-colors shadow-xs"
                >
                  <SlidersHorizontal className="h-3.5 w-3.5" />
                  Compare {selectedBidIds.length} Bids
                </Link>
              )}
              <span className="text-xs text-slate-500 font-mono">
                Page {data?.page ?? 1} of {data?.total_pages ?? 1}
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-600">
                  <th className="py-3.5 px-3 text-center w-10">
                    <input
                      type="checkbox"
                      checked={
                        Boolean(data?.bids.length) &&
                        data?.bids.every((b) => selectedBidIds.includes(b.bid_id))
                      }
                      onChange={(e) => {
                        if (e.target.checked && data) {
                          const pageIds = data.bids.map((b) => b.bid_id);
                          const combined = Array.from(
                            new Set([...selectedBidIds, ...pageIds])
                          ).slice(0, 5);
                          setSelectedBidIds(combined);
                        } else if (data) {
                          const pageIds = new Set(data.bids.map((b) => b.bid_id));
                          setSelectedBidIds(
                            selectedBidIds.filter((id) => !pageIds.has(id))
                          );
                        }
                      }}
                      className="rounded border-slate-300 text-purple-600 focus:ring-purple-500 h-4 w-4 cursor-pointer"
                      title="Select all on this page (up to 5)"
                    />
                  </th>
                  <th className="py-3.5 px-4">Bidder / Org</th>
                  <th className="py-3.5 px-4">Quoted Value</th>
                  <th className="py-3.5 px-4 text-center">Compliance Score</th>
                  <th className="py-3.5 px-4 text-center">Adjusted Risk</th>
                  <th className="py-3.5 px-4 text-center">Defects (Mand / Crit)</th>
                  <th className="py-3.5 px-4 text-center">Review Items</th>
                  <th className="py-3.5 px-4">AI Advisory</th>
                  <th className="py-3.5 px-4 text-center">Eval Status</th>
                  <th className="py-3.5 px-4 text-center">Human Decision</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={10} className="py-12 text-center text-slate-400">
                      <RefreshCw className="h-6 w-6 animate-spin mx-auto text-purple-600 mb-2" />
                      <p className="text-xs font-medium text-slate-600">Loading bid evaluations...</p>
                    </td>
                  </tr>
                ) : !data || data.bids.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="py-12 text-center text-slate-500">
                      <Building2 className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                      <p className="text-sm font-semibold text-slate-700">No submitted bids found</p>
                      <p className="text-xs text-slate-400 mt-1">
                        {searchTerm || statusFilter || riskLevelFilter || criticalOnlyFilter || shortlistedOnlyFilter
                          ? "No bids match the applied filter criteria."
                          : "No bids have been submitted for this tender yet."}
                      </p>
                    </td>
                  </tr>
                ) : (
                  data.bids.map((bid: BidEvaluationListItem) => {
                    const hasCritDefect = bid.has_critical_findings;
                    const isReviewReq = bid.human_review_required;
                    const isSelected = selectedBidIds.includes(bid.bid_id);

                    return (
                      <tr
                        key={bid.bid_id}
                        className={`hover:bg-slate-50/80 transition-colors group ${
                          isSelected
                            ? "bg-purple-50/40 border-l-2 border-l-purple-600"
                            : hasCritDefect
                            ? "bg-rose-50/20"
                            : isReviewReq
                            ? "bg-amber-50/10"
                            : ""
                        }`}
                      >
                        {/* Row Selection Checkbox */}
                        <td className="py-3.5 px-3 text-center">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleBidSelection(bid.bid_id)}
                            className="rounded border-slate-300 text-purple-600 focus:ring-purple-500 h-4 w-4 cursor-pointer"
                            title="Select for comparison"
                          />
                        </td>

                        {/* Bidder / Org */}
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-2">
                            <Link
                              href={`/procurement/tenders/${tenderId}/bids/${bid.bid_id}/evaluation`}
                              className="font-bold text-slate-900 hover:text-purple-900 transition-colors flex items-center gap-1"
                            >
                              <span>{bid.bidder_legal_name}</span>
                            </Link>
                            {bid.is_shortlisted && (
                              <span className="inline-flex items-center gap-0.5 rounded bg-indigo-50 px-1.5 py-0.5 text-[9px] font-bold text-indigo-700 border border-indigo-200">
                                <BookmarkCheck className="h-2.5 w-2.5 text-indigo-600" />
                                SHORTLISTED
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                            <span className="font-mono font-medium text-purple-900 bg-purple-50 px-1.5 py-0.2 rounded border border-purple-100">
                              {bid.bid_number}
                            </span>
                            {bid.trade_name && (
                              <span className="text-slate-600">({bid.trade_name})</span>
                            )}
                            {bid.submitted_at && (
                              <span className="hidden sm:inline text-slate-400">
                                • {new Date(bid.submitted_at).toLocaleDateString()}
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Quoted Value */}
                        <td className="py-3.5 px-4 font-mono font-medium text-slate-800">
                          {bid.quoted_amount ? (
                            <span>
                              ₹{Number(bid.quoted_amount).toLocaleString("en-IN", {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })}
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>

                        {/* Compliance Score */}
                        <td className="py-3.5 px-4 text-center">
                          {bid.compliance_score !== null && bid.compliance_score !== undefined ? (
                            <div className="inline-flex flex-col items-center">
                              <span
                                className={`font-mono text-sm font-bold ${
                                  bid.compliance_score >= 80
                                    ? "text-emerald-700"
                                    : bid.compliance_score >= 50
                                    ? "text-blue-700"
                                    : "text-rose-700"
                                }`}
                              >
                                {bid.compliance_score.toFixed(1)}%
                              </span>
                              {bid.is_score_provisional && (
                                <span className="text-[9px] font-mono text-amber-600 font-semibold">
                                  Provisional
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="font-mono text-slate-400 text-xs">N/A</span>
                          )}
                        </td>

                        {/* Adjusted Risk */}
                        <td className="py-3.5 px-4 text-center">
                          {getRiskBadge(
                            bid.adjusted_risk_level || bid.base_risk_level,
                            bid.adjusted_risk_score ?? bid.base_risk_score,
                            bid.is_risk_provisional
                          )}
                        </td>

                        {/* Defects */}
                        <td className="py-3.5 px-4 text-center">
                          <div className="flex items-center justify-center gap-1 text-xs font-mono font-semibold">
                            <span
                              className={`px-1.5 py-0.5 rounded ${
                                bid.mandatory_failures_count > 0
                                  ? "bg-rose-100 text-rose-800"
                                  : "text-slate-500"
                              }`}
                              title="Mandatory Rule Failures"
                            >
                              M: {bid.mandatory_failures_count}
                            </span>
                            <span className="text-slate-300">/</span>
                            <span
                              className={`px-1.5 py-0.5 rounded ${
                                bid.critical_findings_count > 0 || bid.has_critical_findings
                                  ? "bg-rose-100 text-rose-800"
                                  : "text-slate-500"
                              }`}
                              title="Critical Findings & Overrides"
                            >
                              C: {bid.critical_findings_count}
                            </span>
                          </div>
                        </td>

                        {/* Review Items */}
                        <td className="py-3.5 px-4 text-center">
                          {bid.review_items_count > 0 ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-800 border border-amber-200">
                              <AlertCircle className="h-3 w-3 text-amber-600" />
                              {bid.review_items_count}
                            </span>
                          ) : (
                            <span className="text-slate-400 font-mono text-xs">0</span>
                          )}
                        </td>

                        {/* AI Advisory */}
                        <td className="py-3.5 px-4">
                          {getAIRecBadge(bid.ai_recommendation, bid.ai_status)}
                        </td>

                        {/* Eval Status */}
                        <td className="py-3.5 px-4 text-center">
                          {getEvaluationStatusBadge(bid.evaluation_status)}
                        </td>

                        {/* Human Decision (Part 8D) */}
                        <td className="py-3.5 px-4 text-center">
                          {getDecisionBadge(bid.human_decision_status)}
                        </td>

                        {/* Actions */}
                        <td className="py-3.5 px-4 text-right">
                          <Link
                            href={`/procurement/tenders/${tenderId}/bids/${bid.bid_id}/evaluation`}
                            className="inline-flex items-center gap-1.5 rounded-md bg-purple-900 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-purple-800 transition-colors shadow-xs"
                          >
                            <Eye className="h-3 w-3" />
                            Inspect
                          </Link>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {data && data.total_pages > 1 && (
            <div className="border-t border-slate-200 px-4 py-3 flex items-center justify-between text-xs bg-slate-50/50">
              <span className="text-slate-500">
                Showing{" "}
                <span className="font-semibold text-slate-800">
                  {(data.page - 1) * data.page_size + 1}
                </span>{" "}
                to{" "}
                <span className="font-semibold text-slate-800">
                  {Math.min(data.page * data.page_size, data.total_count)}
                </span>{" "}
                of <span className="font-semibold text-slate-800">{data.total_count}</span> bids
              </span>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  disabled={currentPage <= 1 || loading}
                  onClick={() => loadEvaluations(currentPage - 1)}
                  className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2.5 py-1 text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  Prev
                </button>
                <span className="px-2 font-mono text-slate-700">
                  {data.page} / {data.total_pages}
                </span>
                <button
                  type="button"
                  disabled={currentPage >= data.total_pages || loading}
                  onClick={() => loadEvaluations(currentPage + 1)}
                  className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2.5 py-1 text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none"
                >
                  Next
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Floating Bottom Action Banner for Multi-Bid Comparison */}
        {selectedBidIds.length > 0 && (
          <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-xl bg-slate-900/95 px-5 py-3 text-white shadow-2xl backdrop-blur-md border border-slate-700 animate-in slide-in-from-bottom-4 duration-200">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-purple-600 text-xs font-bold text-white">
                {selectedBidIds.length}
              </span>
              <span className="text-xs font-medium text-slate-200">
                {selectedBidIds.length === 1
                  ? "1 bid selected (Select min. 2 to compare)"
                  : `${selectedBidIds.length} / 5 bids selected for comparison`}
              </span>
            </div>
            <div className="h-4 w-px bg-slate-700 mx-1" />
            <button
              type="button"
              onClick={() => setSelectedBidIds([])}
              className="text-xs font-medium text-slate-400 hover:text-white transition-colors"
            >
              Clear
            </button>
            <Link
              href={`/procurement/tenders/${tenderId}/compare?bids=${selectedBidIds.join(",")}`}
              className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-bold transition-all ${
                selectedBidIds.length >= 2
                  ? "bg-purple-600 hover:bg-purple-500 text-white shadow-md shadow-purple-600/30"
                  : "bg-slate-800 text-slate-500 cursor-not-allowed pointer-events-none"
              }`}
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Compare Bids {selectedBidIds.length >= 2 ? `(${selectedBidIds.length})` : "(Select 2)"}
            </Link>
          </div>
        )}

        {/* Advisory Operational Notice */}
        <div className="rounded-xl border border-purple-200 bg-purple-50/40 p-5">
          <div className="flex items-start gap-3">
            <ShieldCheck className="h-5 w-5 text-purple-900 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-700 space-y-1">
              <p className="font-bold text-purple-900">
                Procurement Officer Evaluation Notice & Disclaimer
              </p>
              <p>
                Compliance scores and risk levels are generated from deterministic rules and verified registry evidence.
                AI recommendations are advisory insights designed to assist procurement scrutiny. The final qualification, disqualification, or award decision remains strictly reserved for the authorized Procurement Officer.
              </p>
            </div>
          </div>
        </div>

        {/* Part 9: Bulk Verification & Batch Evaluation Modal */}
        <BulkEvaluationModal
          tenderId={tenderId}
          tenderNumber={data?.tender_number}
          tenderTitle={data?.tender_title}
          isOpen={bulkModalOpen}
          onClose={() => setBulkModalOpen(false)}
          onJobCompleted={() => loadEvaluations(currentPage)}
        />
      </div>
    </DashboardLayout>
  );
}
