"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  compareTenderBids,
  addBidToShortlist,
  removeBidFromShortlist,
} from "@/lib/api/bid_comparison";
import {
  BidComparisonItem,
  BidComparisonResponse,
  CategoryComparisonRow,
  CriticalFindingComparisonItem,
  RequirementBidResultItem,
  RequirementComparisonRow,
  RequirementFilterMode,
} from "@/types/bid_comparison";
import {
  ArrowLeft,
  Building2,
  CheckCircle2,
  XCircle,
  MinusCircle,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  AlertCircle,
  Clock,
  RefreshCw,
  Eye,
  Sparkles,
  Bot,
  Layers,
  Activity,
  SlidersHorizontal,
  DollarSign,
  AlertOctagon,
  BookmarkCheck,
  Bookmark,
  ChevronDown,
  ChevronUp,
  Filter,
  Check,
  X,
  FileText,
  HelpCircle,
  ExternalLink,
  Tag,
  Scale,
} from "lucide-react";

export default function BidComparisonPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const tenderId = params?.id as string;

  // Read bid IDs from query parameters
  const bidIdsParam = searchParams.get("bids");
  const bidIds = useMemo(() => {
    if (!bidIdsParam) return [];
    return bidIdsParam
      .split(",")
      .map((id) => id.trim())
      .filter(Boolean);
  }, [bidIdsParam]);

  const [data, setData] = useState<BidComparisonResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // View Controls
  const [showDifferencesOnly, setShowDifferencesOnly] = useState<boolean>(false);
  const [showCriticalOnly, setShowCriticalOnly] = useState<boolean>(false);
  const [requirementFilter, setRequirementFilter] = useState<RequirementFilterMode>("ALL");
  const [columnSortBy, setColumnSortBy] = useState<"default" | "score" | "risk" | "price">("default");

  // Section Accordion States
  const [expandSummary, setExpandSummary] = useState<boolean>(true);
  const [expandCategories, setExpandCategories] = useState<boolean>(true);
  const [expandDefects, setExpandDefects] = useState<boolean>(true);
  const [expandRequirements, setExpandRequirements] = useState<boolean>(true);

  // Shortlist Modal State
  const [shortlistModalBid, setShortlistModalBid] = useState<BidComparisonItem | null>(null);
  const [shortlistReason, setShortlistReason] = useState<string>("");
  const [shortlistSubmitting, setShortlistSubmitting] = useState<boolean>(false);
  const [shortlistActionType, setShortlistActionType] = useState<"add" | "remove">("add");

  // Evidence Drilldown Modal State
  const [drilldownModal, setDrilldownModal] = useState<{
    requirement: RequirementComparisonRow;
    bidResult: RequirementBidResultItem;
    bid: BidComparisonItem;
  } | null>(null);

  const loadComparison = async () => {
    if (!tenderId || bidIds.length < 2) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const resp = await compareTenderBids(tenderId, bidIds);
      setData(resp);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err.message ||
          "Failed to load comparative bid evaluation matrix."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadComparison();
  }, [tenderId, bidIdsParam]);

  // Handle Shortlisting Toggle
  const handleOpenShortlistModal = (bid: BidComparisonItem, action: "add" | "remove") => {
    setShortlistModalBid(bid);
    setShortlistActionType(action);
    setShortlistReason(bid.shortlist_reason || "");
  };

  const handleConfirmShortlist = async () => {
    if (!shortlistModalBid) return;
    setShortlistSubmitting(true);
    try {
      if (shortlistActionType === "add") {
        await addBidToShortlist(tenderId, shortlistModalBid.bid_id, shortlistReason);
      } else {
        await removeBidFromShortlist(tenderId, shortlistModalBid.bid_id, shortlistReason);
      }

      // Optimistically update local data
      setData((prev) => {
        if (!prev) return prev;
        const updatedBids = prev.bids.map((b) => {
          if (b.bid_id === shortlistModalBid.bid_id) {
            return {
              ...b,
              is_shortlisted: shortlistActionType === "add",
              shortlist_reason: shortlistReason || null,
              shortlisted_at: new Date().toISOString(),
            };
          }
          return b;
        });
        return { ...prev, bids: updatedBids };
      });

      setShortlistModalBid(null);
    } catch (err: any) {
      alert(
        err?.response?.data?.detail ||
          err.message ||
          "Failed to update shortlist status."
      );
    } finally {
      setShortlistSubmitting(false);
    }
  };

  // Ordered Bids based on column sort
  const sortedBids = useMemo(() => {
    if (!data) return [];
    const bidsCopy = [...data.bids];
    if (columnSortBy === "score") {
      bidsCopy.sort((a, b) => (b.overall_score ?? -1) - (a.overall_score ?? -1));
    } else if (columnSortBy === "risk") {
      bidsCopy.sort(
        (a, b) =>
          (a.adjusted_risk_score ?? 999) - (b.adjusted_risk_score ?? 999)
      );
    } else if (columnSortBy === "price") {
      bidsCopy.sort(
        (a, b) => (Number(a.quoted_amount) || 999999999) - (Number(b.quoted_amount) || 999999999)
      );
    }
    return bidsCopy;
  }, [data, columnSortBy]);

  // Filtered Requirements
  const filteredRequirements = useMemo(() => {
    if (!data) return [];
    return data.requirements.filter((req) => {
      // 1. Differences-only filter
      if (showDifferencesOnly && req.all_match) {
        return false;
      }
      // 2. Critical/Failed only filter
      if (showCriticalOnly && !req.has_failure && !req.has_review && !req.is_critical) {
        return false;
      }
      // 3. Dropdown status filter
      if (requirementFilter === "FAILURES_ONLY" && !req.has_failure) {
        return false;
      }
      if (requirementFilter === "REVIEW_ONLY" && !req.has_review) {
        return false;
      }
      if (requirementFilter === "CRITICAL_ONLY" && !req.is_critical) {
        return false;
      }
      if (requirementFilter === "MANDATORY_ONLY" && !req.is_mandatory) {
        return false;
      }
      return true;
    });
  }, [data, showDifferencesOnly, showCriticalOnly, requirementFilter]);

  // Helpers for Badges
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
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-800 border border-emerald-200">
            <ShieldCheck className="h-3 w-3 text-emerald-600" />
            LOW{scoreStr}
            {isProv && <span className="text-[9px] font-normal text-emerald-700">(Prov.)</span>}
          </span>
        );
      case "MEDIUM":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-0.5 text-xs font-bold text-blue-800 border border-blue-200">
            <ShieldCheck className="h-3 w-3 text-blue-600" />
            MEDIUM{scoreStr}
            {isProv && <span className="text-[9px] font-normal text-blue-700">(Prov.)</span>}
          </span>
        );
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-800 border border-amber-200">
            <AlertTriangle className="h-3 w-3 text-amber-600" />
            HIGH{scoreStr}
            {isProv && <span className="text-[9px] font-normal text-amber-700">(Prov.)</span>}
          </span>
        );
      case "CRITICAL":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-0.5 text-xs font-bold text-rose-800 border border-rose-200">
            <ShieldAlert className="h-3 w-3 text-rose-600" />
            CRITICAL{scoreStr}
            {isProv && <span className="text-[9px] font-normal text-rose-700">(Prov.)</span>}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-xs font-bold text-slate-700">
            {level}
          </span>
        );
    }
  };

  const getComplianceStatusBadge = (status: string) => {
    switch (status) {
      case "PASS":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="h-3 w-3 text-emerald-600 shrink-0" />
            PASS
          </span>
        );
      case "FAIL":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-0.5 text-[11px] font-bold text-rose-700 border border-rose-200">
            <XCircle className="h-3 w-3 text-rose-600 shrink-0" />
            FAIL
          </span>
        );
      case "REVIEW":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-700 border border-amber-200">
            <AlertTriangle className="h-3 w-3 text-amber-600 shrink-0" />
            REVIEW
          </span>
        );
      case "PENDING":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-700 border border-blue-200">
            <Clock className="h-3 w-3 text-blue-600 shrink-0" />
            PENDING
          </span>
        );
      case "NOT_APPLICABLE":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[11px] font-mono text-slate-600 border border-slate-200">
            <MinusCircle className="h-3 w-3 text-slate-500 shrink-0" />
            N/A
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[11px] font-mono text-slate-500 border border-slate-200">
            <Clock className="h-3 w-3 text-slate-400 shrink-0" />
            NOT_EVALUATED
          </span>
        );
    }
  };

  const getAIRecBadge = (rec?: string | null, aiStatus?: string) => {
    if (aiStatus === "STALE") {
      return (
        <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-700 border border-amber-200">
          <AlertTriangle className="h-3 w-3 text-amber-600" />
          AI Stale
        </span>
      );
    }
    if (!rec || aiStatus === "NOT_GENERATED" || aiStatus === "UNAVAILABLE") {
      return (
        <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[11px] font-mono text-slate-400">
          <Bot className="h-3 w-3" />
          Unavailable
        </span>
      );
    }
    switch (rec) {
      case "PROCEED":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-800 border border-emerald-200">
            <Sparkles className="h-3 w-3 text-emerald-600" />
            PROCEED
          </span>
        );
      case "PROCEED_WITH_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-[11px] font-bold text-blue-800 border border-blue-200">
            <Sparkles className="h-3 w-3 text-blue-600" />
            PROCEED W/ REVIEW
          </span>
        );
      case "REVIEW_REQUIRED":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-800 border border-amber-200">
            <AlertTriangle className="h-3 w-3 text-amber-600" />
            REVIEW REQUIRED
          </span>
        );
      case "DO_NOT_PROCEED_WITHOUT_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-rose-50 px-2 py-0.5 text-[11px] font-bold text-rose-800 border border-rose-200">
            <ShieldAlert className="h-3 w-3 text-rose-600" />
            DO NOT PROCEED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
            {rec}
          </span>
        );
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Side-by-Side Bid Comparison"
      description="Compare submitted bidder proposals, category performance, deterministic risk floors, and clause-by-clause determinations."
      breadcrumbs={[
        { label: "Procurement Portal", href: "/procurement" },
        { label: "Tenders", href: "/procurement/tenders" },
        { label: data?.tender_number || "Tender", href: `/procurement/tenders/${tenderId}` },
        { label: "Evaluation", href: `/procurement/tenders/${tenderId}/evaluation` },
        { label: "Comparison" },
      ]}
    >
      <div className="space-y-6 pb-16">
        {/* Top Breadcrumb & Actions Bar */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Link
              href={`/procurement/tenders/${tenderId}/evaluation`}
              className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white p-2 text-slate-600 hover:bg-slate-50 transition-colors shadow-xs"
              title="Return to Tender Evaluation Matrix"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
                  <SlidersHorizontal className="h-5 w-5 text-purple-900" />
                  Side-by-Side Bid Comparison
                </h1>
                <span className="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-bold text-purple-900">
                  {data?.total_compared_bids ?? bidIds.length} Bids Selected
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {data ? `${data.tender_title} (${data.tender_number})` : "Loading tender..."}
              </p>
            </div>
          </div>

          {/* Refresh Action */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadComparison}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-xs disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-purple-600" : ""}`} />
              Refresh
            </button>
            <Link
              href={`/procurement/tenders/${tenderId}/evaluation`}
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-700 transition-colors shadow-xs"
            >
              <Layers className="h-3.5 w-3.5" />
              All Tender Bids
            </Link>
          </div>
        </div>

        {/* Error / Empty Bids State */}
        {bidIds.length < 2 && (
          <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-8 text-center">
            <AlertTriangle className="h-10 w-10 text-amber-600 mx-auto mb-3" />
            <h3 className="text-base font-bold text-slate-900">
              At least 2 bids are required for comparison
            </h3>
            <p className="text-xs text-slate-600 max-w-md mx-auto mt-1">
              Please return to the tender evaluation matrix and select between 2 and 5 submitted proposals to perform a side-by-side comparative analysis.
            </p>
            <Link
              href={`/procurement/tenders/${tenderId}/evaluation`}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-purple-900 px-4 py-2 text-xs font-bold text-white hover:bg-purple-800 shadow-md"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to Evaluation Matrix
            </Link>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50/80 p-4 text-xs text-rose-800 flex items-start gap-3">
            <AlertOctagon className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Comparative Evaluation Request Error</p>
              <p className="mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {loading && (
          <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-xs">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto text-purple-600 mb-3" />
            <p className="text-sm font-bold text-slate-800">Generating Side-by-Side Comparison...</p>
            <p className="text-xs text-slate-500 mt-1">
              Aggregating deterministic compliance scores, adjusted risk levels, overrides, and clause determinations.
            </p>
          </div>
        )}

        {data && !loading && (
          <div className="space-y-6">
            {/* View Controls Toolbar */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-wrap items-center gap-3">
                  {/* Differences Only Toggle */}
                  <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700 select-none">
                    <input
                      type="checkbox"
                      checked={showDifferencesOnly}
                      onChange={(e) => setShowDifferencesOnly(e.target.checked)}
                      className="rounded border-slate-300 text-purple-600 focus:ring-purple-500 h-4 w-4 cursor-pointer"
                    />
                    <span>Show Differences Only</span>
                  </label>

                  <div className="h-4 w-px bg-slate-200 hidden sm:block" />

                  {/* Critical / Failed Only Toggle */}
                  <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700 select-none">
                    <input
                      type="checkbox"
                      checked={showCriticalOnly}
                      onChange={(e) => setShowCriticalOnly(e.target.checked)}
                      className="rounded border-slate-300 text-purple-600 focus:ring-purple-500 h-4 w-4 cursor-pointer"
                    />
                    <span>Critical / Failed Items Only</span>
                  </label>

                  <div className="h-4 w-px bg-slate-200 hidden sm:block" />

                  {/* Requirement Filter Mode */}
                  <div className="flex items-center gap-1.5">
                    <Filter className="h-3.5 w-3.5 text-slate-400" />
                    <select
                      value={requirementFilter}
                      onChange={(e) => setRequirementFilter(e.target.value as RequirementFilterMode)}
                      className="h-8 rounded border border-slate-300 bg-white px-2 text-xs text-slate-700 focus:border-purple-600 focus:outline-hidden"
                    >
                      <option value="ALL">All Requirements</option>
                      <option value="FAILURES_ONLY">Failures Only</option>
                      <option value="REVIEW_ONLY">Review Items</option>
                      <option value="CRITICAL_ONLY">Critical Items</option>
                      <option value="MANDATORY_ONLY">Mandatory Items</option>
                    </select>
                  </div>
                </div>

                {/* Column Ordering */}
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    Sort Columns:
                  </span>
                  <select
                    value={columnSortBy}
                    onChange={(e) => setColumnSortBy(e.target.value as any)}
                    className="h-8 rounded border border-slate-300 bg-white px-2 text-xs font-medium text-slate-700 focus:border-purple-600 focus:outline-hidden"
                  >
                    <option value="default">Default (Selection Order)</option>
                    <option value="score">Highest Score First</option>
                    <option value="risk">Lowest Risk First</option>
                    <option value="price">Lowest Quoted Value</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Comparison Matrix Container */}
            <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <div className="min-w-[900px]">
                  {/* Sticky Bidder Headers */}
                  <div className="sticky top-0 z-30 grid bg-slate-900 text-white shadow-md"
                       style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                    {/* First Column Header */}
                    <div className="p-4 border-r border-slate-800 flex flex-col justify-between">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-widest text-purple-400">
                          Comparison Matrix
                        </span>
                        <h2 className="text-sm font-bold text-white mt-0.5">Evaluation Metric</h2>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-2">
                        Comparing {sortedBids.length} submitted proposals
                      </p>
                    </div>

                    {/* Bidder Header Columns */}
                    {sortedBids.map((bid) => (
                      <div
                        key={bid.bid_id}
                        className="p-4 border-r border-slate-800 last:border-r-0 flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-start justify-between gap-1">
                            <Link
                              href={`/procurement/tenders/${tenderId}/bids/${bid.bid_id}/evaluation`}
                              className="text-sm font-bold text-white hover:text-purple-300 transition-colors line-clamp-1"
                              title={bid.bidder_legal_name}
                            >
                              {bid.bidder_legal_name}
                            </Link>
                          </div>

                          <div className="flex items-center gap-1.5 mt-1 text-[11px]">
                            <span className="font-mono text-purple-300 bg-purple-950/80 px-1.5 py-0.5 rounded border border-purple-800">
                              {bid.bid_number}
                            </span>
                            {bid.trade_name && (
                              <span className="text-slate-400 truncate max-w-[120px]">
                                ({bid.trade_name})
                              </span>
                            )}
                          </div>

                          {/* Quoted Price */}
                          <div className="mt-2.5 flex items-baseline gap-1 text-xs">
                            <span className="text-slate-400">Quoted:</span>
                            <span className="font-mono font-bold text-emerald-400">
                              {bid.quoted_amount ? (
                                `₹${Number(bid.quoted_amount).toLocaleString("en-IN", {
                                  minimumFractionDigits: 2,
                                  maximumFractionDigits: 2,
                                })}`
                              ) : (
                                "—"
                              )}
                            </span>
                          </div>

                          {/* Commercial Ranking Badge */}
                          <div className="mt-2 flex flex-wrap items-center gap-1">
                            {bid.eligibility_status === "INELIGIBLE_MANDATORY_FAILED" ? (
                              <span className="inline-flex items-center gap-1 rounded bg-rose-950 px-2 py-0.5 text-[10px] font-bold text-rose-300 border border-rose-800">
                                <AlertOctagon className="h-2.5 w-2.5 text-rose-400" />
                                INELIGIBLE
                              </span>
                            ) : bid.is_tie ? (
                              <span className="inline-flex items-center gap-1 rounded bg-amber-950 px-2 py-0.5 text-[10px] font-bold text-amber-300 border border-amber-800">
                                <Scale className="h-2.5 w-2.5 text-amber-400" />
                                {bid.rank_label || "COMMERCIAL TIE"}
                              </span>
                            ) : bid.is_l1 ? (
                              <span className="inline-flex items-center gap-1 rounded bg-emerald-950 px-2 py-0.5 text-[10px] font-extrabold text-emerald-300 border border-emerald-600">
                                <CheckCircle2 className="h-2.5 w-2.5 text-emerald-400" />
                                {bid.rank_label || "L1"} (LOWEST COMPLIANT)
                              </span>
                            ) : bid.rank_label ? (
                              <span className="inline-flex items-center rounded bg-slate-800 px-2 py-0.5 text-[10px] font-bold text-slate-200 border border-slate-700">
                                {bid.rank_label}
                              </span>
                            ) : null}

                            {bid.has_critical_blocker && (
                              <span className="inline-flex items-center gap-1 rounded bg-amber-950 px-2 py-0.5 text-[9px] font-bold text-amber-300 border border-amber-700" title={bid.blocker_reason || "Safety review blocker active"}>
                                <AlertTriangle className="h-2.5 w-2.5 text-amber-400" />
                                REVIEW REQ.
                              </span>
                            )}
                          </div>

                          {/* Human Decision Pill (Part 8D) */}
                          <div className="mt-2 flex items-center gap-1">
                            {bid.human_decision_status === "QUALIFIED" ? (
                              <span className="inline-flex items-center gap-1 rounded bg-emerald-950 px-2 py-0.5 text-[10px] font-bold text-emerald-300 border border-emerald-700">
                                <CheckCircle2 className="h-2.5 w-2.5 text-emerald-400" />
                                QUALIFIED
                              </span>
                            ) : bid.human_decision_status === "DISQUALIFIED" ? (
                              <span className="inline-flex items-center gap-1 rounded bg-rose-950 px-2 py-0.5 text-[10px] font-bold text-rose-300 border border-rose-700">
                                <X className="h-2.5 w-2.5 text-rose-400" />
                                DISQUALIFIED
                              </span>
                            ) : bid.human_decision_status === "UNDER_REVIEW" ? (
                              <span className="inline-flex items-center gap-1 rounded bg-amber-950 px-2 py-0.5 text-[10px] font-bold text-amber-300 border border-amber-700">
                                <Clock className="h-2.5 w-2.5 text-amber-400" />
                                UNDER REVIEW
                              </span>
                            ) : (
                              <span className="inline-flex items-center rounded bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-400 border border-slate-700">
                                NOT DECIDED
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Shortlist Action Button */}
                        <div className="mt-3 pt-2.5 border-t border-slate-800 flex items-center justify-between">
                          {bid.is_shortlisted ? (
                            <button
                              type="button"
                              onClick={() => handleOpenShortlistModal(bid, "remove")}
                              className="inline-flex items-center gap-1 rounded bg-indigo-950 px-2 py-1 text-[11px] font-bold text-indigo-300 hover:bg-indigo-900 border border-indigo-700 transition-colors"
                              title="Click to remove from shortlist"
                            >
                              <BookmarkCheck className="h-3 w-3 text-indigo-400" />
                              Shortlisted
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => handleOpenShortlistModal(bid, "add")}
                              className="inline-flex items-center gap-1 rounded bg-slate-800 px-2 py-1 text-[11px] font-semibold text-slate-300 hover:bg-slate-700 border border-slate-700 transition-colors"
                              title="Add proposal to shortlist for further review"
                            >
                              <Bookmark className="h-3 w-3 text-slate-400" />
                              Add to Shortlist
                            </button>
                          )}

                          <Link
                            href={`/procurement/tenders/${tenderId}/bids/${bid.bid_id}/evaluation`}
                            className="text-[11px] text-purple-400 hover:text-purple-300 font-semibold flex items-center gap-0.5"
                          >
                            <span>Inspect</span>
                            <ExternalLink className="h-2.5 w-2.5" />
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* ========================================================================= */}
                  {/* SECTION 0: COMMERCIAL EVALUATION & DETERMINISTIC RANKING */}
                  {/* ========================================================================= */}
                  <div className="border-b border-slate-200 bg-slate-50/20">
                    <div className="bg-navy-900/5 px-4 py-2.5 text-left text-xs font-bold uppercase tracking-wider text-navy-900 flex items-center justify-between border-b border-slate-200">
                      <span className="flex items-center gap-2 font-heading">
                        <Scale className="h-4 w-4 text-navy-900" />
                        Commercial Evaluation & Deterministic Ranking ({data.evaluation_method || "L1_LOWEST_COMPLIANT_BID"})
                      </span>
                    </div>

                    <div className="divide-y divide-slate-100 text-xs">
                      {/* Commercial Rank Row */}
                      <div className="grid hover:bg-slate-50/50"
                           style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                        <div className="p-3.5 font-bold text-slate-900 border-r border-slate-100 bg-slate-50/50">
                          Commercial Rank
                        </div>
                        {sortedBids.map((bid) => (
                          <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0">
                            {bid.eligibility_status === "INELIGIBLE_MANDATORY_FAILED" ? (
                              <span className="font-bold text-rose-700 bg-rose-50 px-2 py-1 rounded border border-rose-200">
                                Excluded (Ineligible)
                              </span>
                            ) : bid.rank_label ? (
                              <div className="flex items-center gap-2">
                                <span className={`font-mono text-sm font-extrabold px-2.5 py-1 rounded ${
                                  bid.is_l1 || bid.commercial_rank === 1
                                    ? "bg-emerald-100 text-emerald-900 border border-emerald-300"
                                    : "bg-slate-100 text-slate-800"
                                }`}>
                                  {bid.rank_label}
                                </span>
                                {bid.is_tie && (
                                  <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                                    Tie
                                  </span>
                                )}
                              </div>
                            ) : (
                              <span className="text-slate-400 font-mono">—</span>
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Quoted Price Row */}
                      <div className="grid hover:bg-slate-50/50"
                           style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                        <div className="p-3.5 font-semibold text-slate-800 border-r border-slate-100 bg-slate-50/30">
                          Quoted Commercial Bid
                        </div>
                        {sortedBids.map((bid) => (
                          <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0 font-mono font-bold text-slate-900">
                            {bid.quoted_amount ? `₹${Number(bid.quoted_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "—"}
                          </div>
                        ))}
                      </div>

                      {/* QCBS Financial & Final Score Row (if QCBS) */}
                      {data.evaluation_method === "QCBS_TECHNICAL_FINANCIAL" && (
                        <>
                          <div className="grid hover:bg-slate-50/50"
                               style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                            <div className="p-3.5 font-semibold text-slate-800 border-r border-slate-100 bg-slate-50/30">
                              Financial Score ({data.financial_weight || 30}%)
                            </div>
                            {sortedBids.map((bid) => (
                              <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0 font-mono font-semibold text-slate-800">
                                {bid.financial_score !== undefined && bid.financial_score !== null ? `${bid.financial_score.toFixed(2)} pts` : "—"}
                              </div>
                            ))}
                          </div>

                          <div className="grid hover:bg-slate-50/50 bg-blue-50/20"
                               style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                            <div className="p-3.5 font-bold text-navy-900 border-r border-slate-100 bg-navy-50/40">
                              Combined Final QCBS Score
                            </div>
                            {sortedBids.map((bid) => (
                              <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0">
                                {bid.final_score !== undefined && bid.final_score !== null ? (
                                  <span className="font-mono text-sm font-extrabold text-navy-900 bg-white px-2 py-0.5 rounded border border-navy-200">
                                    {bid.final_score.toFixed(2)} / 100
                                  </span>
                                ) : (
                                  <span className="text-slate-400 font-mono">—</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </>
                      )}

                      {/* Transparent Justification ("Explain Why") */}
                      <div className="grid hover:bg-slate-50/50"
                           style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                        <div className="p-3.5 font-semibold text-slate-800 border-r border-slate-100 bg-slate-50/30">
                          Evaluation Justification
                        </div>
                        {sortedBids.map((bid) => (
                          <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0 text-[11px] text-slate-600 leading-relaxed">
                            {bid.commercial_explanation || (bid.eligibility_status === "INELIGIBLE_MANDATORY_FAILED" ? "Disqualified due to mandatory compliance failures." : "Evaluation pending.")}
                            {bid.has_critical_blocker && bid.blocker_reason && (
                              <div className="mt-1.5 p-2 rounded bg-amber-50 border border-amber-200 text-amber-900 font-semibold text-[10px] flex items-start gap-1.5">
                                <AlertTriangle className="h-3.5 w-3.5 text-amber-600 shrink-0 mt-0.5" />
                                <span>Safety Blocker: {bid.blocker_reason}</span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* ========================================================================= */}
                  {/* SECTION 1: SUMMARY PERFORMANCE METRICS */}
                  {/* ========================================================================= */}
                  <div className="border-b border-slate-200">
                    <button
                      type="button"
                      onClick={() => setExpandSummary(!expandSummary)}
                      className="w-full bg-slate-50 px-4 py-2.5 text-left text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center justify-between hover:bg-slate-100 transition-colors"
                    >
                      <span className="flex items-center gap-2">
                        <Activity className="h-4 w-4 text-purple-900" />
                        1. Core Evaluation & Risk Summary
                      </span>
                      {expandSummary ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>

                    {expandSummary && (
                      <div className="divide-y divide-slate-100 text-xs">
                        {/* Overall Compliance Score Row */}
                        <div className="grid hover:bg-slate-50/50"
                             style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                          <div className="p-3.5 font-semibold text-slate-800 border-r border-slate-100 bg-slate-50/30">
                            Overall Compliance Score
                          </div>
                          {sortedBids.map((bid) => (
                            <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0">
                              {bid.overall_score !== null && bid.overall_score !== undefined ? (
                                <div className="flex items-baseline gap-2">
                                  <span
                                    className={`font-mono text-base font-bold ${
                                      bid.overall_score >= 80
                                        ? "text-emerald-700"
                                        : bid.overall_score >= 50
                                        ? "text-blue-700"
                                        : "text-rose-700"
                                    }`}
                                  >
                                    {bid.overall_score.toFixed(1)}%
                                  </span>
                                  {bid.is_score_provisional && (
                                    <span className="text-[10px] font-semibold text-amber-600 bg-amber-50 px-1 rounded border border-amber-200">
                                      Provisional
                                    </span>
                                  )}
                                </div>
                              ) : (
                                <span className="font-mono text-slate-400">N/A</span>
                              )}
                            </div>
                          ))}
                        </div>

                        {/* Adjusted Risk Level Row */}
                        <div className="grid hover:bg-slate-50/50"
                             style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                          <div className="p-3.5 font-semibold text-slate-800 border-r border-slate-100 bg-slate-50/30">
                            Adjusted Risk Assessment
                          </div>
                          {sortedBids.map((bid) => (
                            <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0">
                              <div className="flex flex-col items-start gap-1">
                                {getRiskBadge(
                                  bid.adjusted_risk_level,
                                  bid.adjusted_risk_score,
                                  bid.is_risk_provisional
                                )}
                                {bid.override_applied && (
                                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200 mt-0.5">
                                    <AlertTriangle className="h-2.5 w-2.5 text-rose-600" />
                                    Critical Floor Applied
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>

                        {/* Mandatory Failures Row */}
                        <div className="grid hover:bg-slate-50/50"
                             style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                          <div className="p-3.5 font-semibold text-slate-800 border-r border-slate-100 bg-slate-50/30">
                            Mandatory Failures
                          </div>
                          {sortedBids.map((bid) => (
                            <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0">
                              <span
                                className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${
                                  bid.mandatory_failure_count > 0
                                    ? "bg-rose-100 text-rose-800"
                                    : "bg-emerald-50 text-emerald-700"
                                }`}
                              >
                                {bid.mandatory_failure_count} {bid.mandatory_failure_count === 1 ? "Failure" : "Failures"}
                              </span>
                            </div>
                          ))}
                        </div>

                        {/* Critical Findings Row */}
                        <div className="grid hover:bg-slate-50/50"
                             style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                          <div className="p-3.5 font-semibold text-slate-800 border-r border-slate-100 bg-slate-50/30">
                            Critical Findings
                          </div>
                          {sortedBids.map((bid) => (
                            <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0">
                              <span
                                className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${
                                  bid.critical_failure_count > 0
                                    ? "bg-rose-100 text-rose-800"
                                    : "bg-slate-100 text-slate-600"
                                }`}
                              >
                                {bid.critical_failure_count} {bid.critical_failure_count === 1 ? "Finding" : "Findings"}
                              </span>
                            </div>
                          ))}
                        </div>

                        {/* Review Items Row */}
                        <div className="grid hover:bg-slate-50/50"
                             style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                          <div className="p-3.5 font-semibold text-slate-800 border-r border-slate-100 bg-slate-50/30">
                            Human Review Items
                          </div>
                          {sortedBids.map((bid) => (
                            <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0">
                              {bid.review_count > 0 ? (
                                <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-800 border border-amber-200">
                                  <AlertCircle className="h-3 w-3 text-amber-600" />
                                  {bid.review_count} {bid.review_count === 1 ? "Item" : "Items"}
                                </span>
                              ) : (
                                <span className="text-slate-400 font-mono text-xs">0 items</span>
                              )}
                            </div>
                          ))}
                        </div>

                        {/* AI Recommendation Row */}
                        <div className="grid hover:bg-slate-50/50"
                             style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                          <div className="p-3.5 font-semibold text-slate-800 border-r border-slate-100 bg-slate-50/30">
                            AI Recommendation
                          </div>
                          {sortedBids.map((bid) => (
                            <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0">
                              {getAIRecBadge(bid.ai_recommendation, bid.ai_status)}
                              {bid.ai_summary && (
                                <p className="text-[11px] text-slate-500 mt-1 line-clamp-2 italic">
                                  "{bid.ai_summary}"
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* ========================================================================= */}
                  {/* SECTION 2: CATEGORY PERFORMANCE MATRIX */}
                  {/* ========================================================================= */}
                  <div className="border-b border-slate-200">
                    <button
                      type="button"
                      onClick={() => setExpandCategories(!expandCategories)}
                      className="w-full bg-slate-50 px-4 py-2.5 text-left text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center justify-between hover:bg-slate-100 transition-colors"
                    >
                      <span className="flex items-center gap-2">
                        <Layers className="h-4 w-4 text-purple-900" />
                        2. Category Performance Matrix
                      </span>
                      {expandCategories ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>

                    {expandCategories && (
                      <div className="divide-y divide-slate-100 text-xs">
                        {data.categories.map((catRow) => (
                          <div
                            key={catRow.category_code}
                            className="grid hover:bg-slate-50/50"
                            style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}
                          >
                            <div className="p-3.5 border-r border-slate-100 bg-slate-50/30 flex flex-col justify-center">
                              <span className="font-semibold text-slate-800">{catRow.display_name}</span>
                              <span className="text-[10px] font-mono text-slate-400">[{catRow.category_code}]</span>
                            </div>

                            {sortedBids.map((bid) => {
                              const catVal = catRow.bid_scores[String(bid.bid_id)];
                              if (!catVal || catVal.is_na) {
                                return (
                                  <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0 flex items-center">
                                    <span className="font-mono text-slate-400 text-xs bg-slate-100 px-2 py-0.5 rounded">
                                      N/A
                                    </span>
                                  </div>
                                );
                              }

                              const scoreNum = catVal.score ?? 0;
                              return (
                                <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0 flex flex-col justify-center gap-1">
                                  <div className="flex items-center justify-between">
                                    <span
                                      className={`font-mono font-bold text-xs ${
                                        scoreNum >= 80
                                          ? "text-emerald-700"
                                          : scoreNum >= 50
                                          ? "text-blue-700"
                                          : "text-rose-700"
                                      }`}
                                    >
                                      {scoreNum.toFixed(1)}%
                                    </span>
                                    <span className="text-[10px] text-slate-400 font-mono">
                                      {catVal.passed_rules}/{catVal.total_rules} Passed
                                    </span>
                                  </div>
                                  {/* Progress bar */}
                                  <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                    <div
                                      className={`h-full rounded-full ${
                                        scoreNum >= 80 ? "bg-emerald-500" : scoreNum >= 50 ? "bg-blue-500" : "bg-rose-500"
                                      }`}
                                      style={{ width: `${Math.min(100, Math.max(0, scoreNum))}%` }}
                                    />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* ========================================================================= */}
                  {/* SECTION 3: DEFECTS & ALERTS BREAKDOWN */}
                  {/* ========================================================================= */}
                  <div className="border-b border-slate-200">
                    <button
                      type="button"
                      onClick={() => setExpandDefects(!expandDefects)}
                      className="w-full bg-slate-50 px-4 py-2.5 text-left text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center justify-between hover:bg-slate-100 transition-colors"
                    >
                      <span className="flex items-center gap-2">
                        <ShieldAlert className="h-4 w-4 text-purple-900" />
                        3. Defects, Critical Findings & Review Alerts
                      </span>
                      {expandDefects ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>

                    {expandDefects && (
                      <div className="divide-y divide-slate-100 text-xs">
                        {/* Critical Findings Itemized List */}
                        <div className="grid hover:bg-slate-50/50"
                             style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                          <div className="p-3.5 border-r border-slate-100 bg-slate-50/30 font-semibold text-slate-800">
                            Critical Findings Detail
                          </div>
                          {sortedBids.map((bid) => (
                            <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0 space-y-2">
                              {bid.critical_findings.length === 0 ? (
                                <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 font-medium">
                                  <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                                  No critical findings
                                </span>
                              ) : (
                                bid.critical_findings.map((cf, idx) => (
                                  <div
                                    key={idx}
                                    className="rounded bg-rose-50 p-2 text-[11px] border border-rose-200 space-y-0.5"
                                  >
                                    <div className="font-bold text-rose-900 flex items-center justify-between">
                                      <span>[{cf.requirement_code}] {cf.requirement_name}</span>
                                    </div>
                                    <p className="text-rose-700 leading-snug">{cf.finding_reason}</p>
                                    {cf.risk_override && (
                                      <span className="inline-block text-[9px] font-mono font-bold text-rose-800 bg-rose-100/70 px-1 rounded">
                                        {cf.risk_override}
                                      </span>
                                    )}
                                  </div>
                                ))
                              )}
                            </div>
                          ))}
                        </div>

                        {/* Mandatory Failures Itemized List */}
                        <div className="grid hover:bg-slate-50/50"
                             style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                          <div className="p-3.5 border-r border-slate-100 bg-slate-50/30 font-semibold text-slate-800">
                            Mandatory Failures Detail
                          </div>
                          {sortedBids.map((bid) => (
                            <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0 space-y-1.5">
                              {bid.mandatory_failures.length === 0 ? (
                                <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 font-medium">
                                  <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                                  Zero mandatory failures
                                </span>
                              ) : (
                                bid.mandatory_failures.map((mf, idx) => (
                                  <div
                                    key={idx}
                                    className="rounded bg-rose-50/80 px-2 py-1 text-[11px] text-rose-800 font-medium border border-rose-200"
                                  >
                                    {mf}
                                  </div>
                                ))
                              )}
                            </div>
                          ))}
                        </div>

                        {/* Human Review Items Detail */}
                        <div className="grid hover:bg-slate-50/50"
                             style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}>
                          <div className="p-3.5 border-r border-slate-100 bg-slate-50/30 font-semibold text-slate-800">
                            Review Items Detail
                          </div>
                          {sortedBids.map((bid) => (
                            <div key={bid.bid_id} className="p-3.5 border-r border-slate-100 last:border-r-0 space-y-1.5">
                              {bid.review_items.length === 0 ? (
                                <span className="text-[11px] text-slate-400">None</span>
                              ) : (
                                bid.review_items.map((ri, idx) => (
                                  <div
                                    key={idx}
                                    className="rounded bg-amber-50 px-2 py-1 text-[11px] text-amber-800 border border-amber-200 font-medium"
                                  >
                                    {ri}
                                  </div>
                                ))
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* ========================================================================= */}
                  {/* SECTION 4: DETAILED REQUIREMENT COMPARISON */}
                  {/* ========================================================================= */}
                  <div>
                    <button
                      type="button"
                      onClick={() => setExpandRequirements(!expandRequirements)}
                      className="w-full bg-slate-50 px-4 py-2.5 text-left text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center justify-between hover:bg-slate-100 transition-colors"
                    >
                      <span className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-purple-900" />
                        4. Detailed Requirement-by-Requirement Comparison ({filteredRequirements.length} Clauses)
                      </span>
                      {expandRequirements ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>

                    {expandRequirements && (
                      <div className="divide-y divide-slate-100 text-xs">
                        {filteredRequirements.length === 0 ? (
                          <div className="p-8 text-center text-slate-400">
                            <p className="font-semibold text-slate-600">No requirements match the filter criteria</p>
                            <p className="text-xs mt-1">Try disabling "Show Differences Only" or changing the filter dropdown.</p>
                          </div>
                        ) : (
                          filteredRequirements.map((req) => (
                            <div
                              key={req.requirement_id}
                              className={`grid hover:bg-slate-50/60 transition-colors ${
                                req.has_failure
                                  ? "bg-rose-50/15"
                                  : req.has_review
                                  ? "bg-amber-50/10"
                                  : ""
                              }`}
                              style={{ gridTemplateColumns: `260px repeat(${sortedBids.length}, minmax(220px, 1fr))` }}
                            >
                              {/* Requirement Metadata Column */}
                              <div className="p-3.5 border-r border-slate-100 bg-slate-50/30 flex flex-col justify-between">
                                <div>
                                  <div className="flex items-center gap-1.5">
                                    <span className="font-mono font-bold text-purple-900 bg-purple-50 px-1 py-0.2 rounded border border-purple-100 text-[10px]">
                                      {req.code}
                                    </span>
                                    {req.is_mandatory && (
                                      <span className="text-[9px] font-bold text-rose-700 bg-rose-50 px-1 py-0.2 rounded border border-rose-200">
                                        Mandatory
                                      </span>
                                    )}
                                    {req.is_critical && (
                                      <span className="text-[9px] font-bold text-purple-700 bg-purple-50 px-1 py-0.2 rounded border border-purple-200">
                                        Critical
                                      </span>
                                    )}
                                  </div>
                                  <p className="font-semibold text-slate-900 mt-1 line-clamp-2" title={req.name}>
                                    {req.name}
                                  </p>
                                </div>
                                <div className="mt-2 text-[10px] text-slate-400 flex items-center justify-between">
                                  <span>{req.category}</span>
                                  <span>Weight: {req.weight}</span>
                                </div>
                              </div>

                              {/* Per-Bid Result Columns */}
                              {sortedBids.map((bid) => {
                                const bRes = req.bid_results[String(bid.bid_id)];
                                const statusVal = bRes?.compliance_status || "NOT_EVALUATED";

                                return (
                                  <div
                                    key={bid.bid_id}
                                    className="p-3.5 border-r border-slate-100 last:border-r-0 flex flex-col justify-between"
                                  >
                                    <div>
                                      <div className="flex items-center justify-between">
                                        {getComplianceStatusBadge(statusVal)}
                                      </div>

                                      {/* Reason / Summary */}
                                      {bRes?.reason && (
                                        <p className="text-[11px] text-slate-600 mt-1.5 line-clamp-2 leading-relaxed">
                                          {bRes.reason}
                                        </p>
                                      )}
                                    </div>

                                    {/* Drilldown modal button */}
                                    <div className="mt-2 pt-1 flex items-center justify-end">
                                      <button
                                        type="button"
                                        onClick={() => {
                                          if (bRes) {
                                            setDrilldownModal({
                                              requirement: req,
                                              bidResult: bRes,
                                              bid: bid,
                                            });
                                          }
                                        }}
                                        className="text-[11px] text-purple-700 hover:text-purple-900 font-semibold inline-flex items-center gap-1 transition-colors"
                                      >
                                        <Eye className="h-3 w-3" />
                                        <span>Details</span>
                                      </button>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Shortlist Action Modal */}
        {shortlistModalBid && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl border border-slate-200">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <BookmarkCheck className="h-5 w-5 text-purple-900" />
                  {shortlistActionType === "add" ? "Shortlist Bidder for Further Review" : "Remove from Shortlist"}
                </h3>
                <button
                  type="button"
                  onClick={() => setShortlistModalBid(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="mt-4 space-y-3 text-xs">
                <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                  <p className="font-bold text-slate-800">{shortlistModalBid.bidder_legal_name}</p>
                  <p className="text-slate-500 font-mono mt-0.5">Bid: {shortlistModalBid.bid_number}</p>
                </div>

                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">
                    Procurement Officer Rationale / Remarks (Optional)
                  </label>
                  <textarea
                    rows={3}
                    value={shortlistReason}
                    onChange={(e) => setShortlistReason(e.target.value)}
                    placeholder="e.g. Strong technical compliance and competitive quote; selected for detailed committee review."
                    className="w-full rounded-lg border border-slate-300 p-2.5 text-xs text-slate-800 placeholder-slate-400 focus:border-purple-600 focus:outline-hidden"
                  />
                </div>

                <p className="text-[11px] text-slate-500 italic">
                  Note: Shortlisting is a human-controlled intermediate review step. It does not qualify, award, or finalize tender results.
                </p>
              </div>

              <div className="mt-5 flex items-center justify-end gap-2 border-t border-slate-100 pt-3">
                <button
                  type="button"
                  onClick={() => setShortlistModalBid(null)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={shortlistSubmitting}
                  onClick={handleConfirmShortlist}
                  className={`rounded-lg px-4 py-1.5 text-xs font-bold text-white transition-colors ${
                    shortlistActionType === "add"
                      ? "bg-purple-900 hover:bg-purple-800"
                      : "bg-rose-700 hover:bg-rose-600"
                  }`}
                >
                  {shortlistSubmitting
                    ? "Updating..."
                    : shortlistActionType === "add"
                    ? "Confirm Shortlist"
                    : "Remove Shortlist"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Evidence & Determination Drilldown Modal */}
        {drilldownModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
            <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-purple-900 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-100">
                    Clause: {drilldownModal.requirement.code}
                  </span>
                  <h3 className="text-sm font-bold text-slate-900 mt-1">
                    {drilldownModal.requirement.name}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setDrilldownModal(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="mt-4 space-y-3 text-xs">
                {/* Bidder Info */}
                <div className="flex items-center justify-between bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase font-bold">Bidder</span>
                    <p className="font-bold text-slate-800">{drilldownModal.bid.bidder_legal_name}</p>
                  </div>
                  <div>{getComplianceStatusBadge(drilldownModal.bidResult.compliance_status)}</div>
                </div>

                {/* Expected vs Actual */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                      Tender Requirement Expected
                    </span>
                    <p className="font-mono text-xs font-semibold text-slate-800 mt-1">
                      {drilldownModal.requirement.operator
                        ? `${drilldownModal.requirement.operator} `
                        : ""}
                      {String(drilldownModal.requirement.expected_value ?? "Specified in RFP")}
                    </p>
                  </div>

                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                      Verified Actual Value
                    </span>
                    <p className="font-mono text-xs font-semibold text-slate-800 mt-1">
                      {drilldownModal.bidResult.actual_value !== null && drilldownModal.bidResult.actual_value !== undefined
                        ? String(drilldownModal.bidResult.actual_value)
                        : "Not verified / N/A"}
                    </p>
                  </div>
                </div>

                {/* Finding / Reason */}
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Determination Analysis
                  </span>
                  <div className="mt-1 rounded-lg bg-slate-50 p-3 border border-slate-200 text-slate-700 leading-relaxed">
                    {drilldownModal.bidResult.reason || "No specific determination notes recorded."}
                  </div>
                </div>

                {/* Evidence Summary */}
                {drilldownModal.bidResult.evidence_summary && (
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                      Evidence Details
                    </span>
                    <div className="mt-1 rounded-lg bg-purple-50/50 p-3 border border-purple-100 text-purple-950 font-mono text-[11px] leading-relaxed">
                      {drilldownModal.bidResult.evidence_summary}
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-3">
                <Link
                  href={`/procurement/tenders/${tenderId}/bids/${drilldownModal.bid.bid_id}/evaluation`}
                  className="inline-flex items-center gap-1 text-xs font-bold text-purple-900 hover:text-purple-800"
                >
                  <span>Open Full Bid Evaluation</span>
                  <ExternalLink className="h-3 w-3" />
                </Link>

                <button
                  type="button"
                  onClick={() => setDrilldownModal(null)}
                  className="rounded-lg bg-slate-900 px-4 py-1.5 text-xs font-bold text-white hover:bg-slate-800"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
