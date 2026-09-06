"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  BadgeAlert,
  CheckCircle2,
  Clock,
  ExternalLink,
  Filter,
  Layers,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  XCircle,
} from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { getHumanReviewQueue } from "@/lib/api/human_review";
import {
  ReviewQueueItem,
  ReviewQueueKPIs,
  ReviewSeverity,
  ReviewStatus,
  ReviewType,
} from "@/types/human_review";

export default function HumanReviewQueuePage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [kpis, setKpis] = useState<ReviewQueueKPIs>({
    total_open: 0,
    critical_open: 0,
    high_open: 0,
    awaiting_clarification: 0,
    in_review: 0,
    resolved_today: 0,
    escalated: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination State
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [reviewTypeFilter, setReviewTypeFilter] = useState<string>("");
  const [criticalOnly, setCriticalOnly] = useState<boolean>(false);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);

  const fetchQueue = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getHumanReviewQueue({
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        review_type: reviewTypeFilter || undefined,
        critical_only: criticalOnly || undefined,
        search: search.trim() || undefined,
        page,
        page_size: pageSize,
      });

      setItems(res.items);
      setKpis(res.kpis);
      setTotalPages(res.total_pages);
      setTotalCount(res.total_count);
    } catch (err: any) {
      console.error("Failed to load human review queue:", err);
      setError(err?.message || "Failed to load human review queue items.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, severityFilter, reviewTypeFilter, criticalOnly, search, page, pageSize]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchQueue();
  };

  const getSeverityBadge = (severity: ReviewSeverity) => {
    switch (severity) {
      case "CRITICAL":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-0.5 text-xs font-bold text-rose-700 border border-rose-200">
            <ShieldAlert className="h-3 w-3 text-rose-600" />
            CRITICAL
          </span>
        );
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-orange-50 px-2 py-0.5 text-xs font-semibold text-orange-700 border border-orange-200">
            <AlertTriangle className="h-3 w-3 text-orange-600" />
            HIGH
          </span>
        );
      case "MEDIUM":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 border border-amber-200">
            MEDIUM
          </span>
        );
      case "LOW":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 border border-slate-200">
            LOW
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
            {severity}
          </span>
        );
    }
  };

  const getStatusBadge = (status: ReviewStatus) => {
    switch (status) {
      case "OPEN":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-0.5 text-xs font-bold text-blue-700 border border-blue-200">
            <Clock className="h-3 w-3 text-blue-600 shrink-0" />
            OPEN
          </span>
        );
      case "IN_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-purple-50 px-2 py-0.5 text-xs font-bold text-purple-700 border border-purple-200">
            <Clock className="h-3 w-3 text-purple-600 shrink-0" />
            IN REVIEW
          </span>
        );
      case "RESOLVED":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="h-3 w-3 text-emerald-600 shrink-0" />
            RESOLVED
          </span>
        );
      case "ESCALATED":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-800 border border-amber-200">
            <AlertTriangle className="h-3 w-3 text-amber-600 shrink-0" />
            ESCALATED
          </span>
        );
      case "SUPERSEDED":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500 border border-slate-200">
            <XCircle className="h-3 w-3 text-slate-400 shrink-0" />
            SUPERSEDED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 border border-slate-200">
            <Clock className="h-3 w-3 text-slate-500 shrink-0" />
            {status}
          </span>
        );
    }
  };

  const formatReviewType = (type: ReviewType) => {
    switch (type) {
      case "COMPLIANCE_REVIEW":
        return "Compliance Clause";
      case "VERIFICATION_REVIEW":
        return "External Verification";
      case "DOCUMENT_REVIEW":
        return "Document Authenticity";
      case "IDENTITY_MISMATCH":
        return "Identity Discrepancy";
      case "LOW_CONFIDENCE":
        return "Low OCR Confidence";
      case "PENDING_SOURCE":
        return "Pending Check";
      case "CRITICAL_REVIEW":
        return "Critical Clause Failure";
      default:
        return type.replace("_", " ");
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Human Review & Evidence Inspection Queue"
      description="Inspect flagged evidence, clarify verification discrepancies, add auditable remarks, and record human compliance resolutions."
      breadcrumbs={[
        { label: "Procurement Portal", href: "/procurement" },
        { label: "Human Review Queue" },
      ]}
    >
      <div className="space-y-6 pb-16">
        {/* KPI Cards Grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {/* Card 1: Open Reviews */}
          <div className="rounded-xl border border-blue-200/80 bg-gradient-to-br from-blue-50/50 to-white p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-700">Open Reviews</span>
              <div className="rounded-lg bg-blue-100 p-2 text-blue-700">
                <Clock className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-black tracking-tight text-blue-900">{kpis.total_open}</span>
              <span className="text-xs text-slate-500">awaiting review</span>
            </div>
          </div>

          {/* Card 2: Critical Reviews */}
          <div className="rounded-xl border border-rose-200/80 bg-gradient-to-br from-rose-50/50 to-white p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-rose-700">Critical Reviews</span>
              <div className="rounded-lg bg-rose-100 p-2 text-rose-700">
                <ShieldAlert className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-black tracking-tight text-rose-900">{kpis.critical_open}</span>
              <span className="text-xs text-rose-600 font-medium">high priority</span>
            </div>
          </div>

          {/* Card 3: In Review */}
          <div className="rounded-xl border border-purple-200/80 bg-gradient-to-br from-purple-50/50 to-white p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-purple-700">In Review</span>
              <div className="rounded-lg bg-purple-100 p-2 text-purple-700">
                <UserCheck className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-black tracking-tight text-purple-900">{kpis.in_review}</span>
              <span className="text-xs text-slate-500">claimed by officers</span>
            </div>
          </div>

          {/* Card 4: Resolved Today */}
          <div className="rounded-xl border border-emerald-200/80 bg-gradient-to-br from-emerald-50/50 to-white p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700">Resolved Today</span>
              <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-black tracking-tight text-emerald-900">{kpis.resolved_today}</span>
              <span className="text-xs text-slate-500">completed</span>
            </div>
          </div>

          {/* Card 5: Escalated */}
          <div className="rounded-xl border border-amber-200/80 bg-gradient-to-br from-amber-50/50 to-white p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-amber-700">Escalated</span>
              <div className="rounded-lg bg-amber-100 p-2 text-amber-700">
                <BadgeAlert className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-black tracking-tight text-amber-900">{kpis.escalated}</span>
              <span className="text-xs text-slate-500">senior review</span>
            </div>
          </div>
        </div>

        {/* View Controls & Filter Bar */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            {/* Search Bar */}
            <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search Bid #, Bidder Name, Clause, PAN, GSTIN..."
                className="w-full rounded-lg border border-slate-300 pl-9 pr-4 py-2 text-xs text-slate-800 placeholder-slate-400 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
              />
            </form>

            {/* Quick Action Buttons */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setCriticalOnly(!criticalOnly)}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold transition-colors ${
                  criticalOnly
                    ? "bg-rose-600 text-white shadow-xs"
                    : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                <ShieldAlert className="h-3.5 w-3.5" />
                Critical Only
              </button>

              <button
                type="button"
                onClick={fetchQueue}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 shadow-xs"
                title="Refresh Review Queue"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-blue-600" : ""}`} />
                Refresh
              </button>
            </div>
          </div>

          {/* Filter Dropdowns */}
          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-slate-100 text-xs">
            <div className="flex items-center gap-1.5 text-slate-500 font-medium">
              <Filter className="h-3.5 w-3.5" />
              Filters:
            </div>

            {/* Status Select */}
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-700 focus:border-blue-600 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="OPEN">Open Only</option>
              <option value="IN_REVIEW">In Review</option>
              <option value="RESOLVED">Resolved</option>
              <option value="ESCALATED">Escalated</option>
            </select>

            {/* Severity Select */}
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-700 focus:border-blue-600 focus:outline-none"
            >
              <option value="">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>

            {/* Review Type Select */}
            <select
              value={reviewTypeFilter}
              onChange={(e) => {
                setReviewTypeFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-700 focus:border-blue-600 focus:outline-none"
            >
              <option value="">All Review Types</option>
              <option value="COMPLIANCE_REVIEW">Compliance Clause</option>
              <option value="CRITICAL_REVIEW">Critical Failure</option>
              <option value="VERIFICATION_REVIEW">Verification Discrepancy</option>
              <option value="IDENTITY_MISMATCH">Identity Mismatch</option>
              <option value="LOW_CONFIDENCE">Low OCR Confidence</option>
            </select>

            {(statusFilter || severityFilter || reviewTypeFilter || criticalOnly || search) && (
              <button
                type="button"
                onClick={() => {
                  setStatusFilter("");
                  setSeverityFilter("");
                  setReviewTypeFilter("");
                  setCriticalOnly(false);
                  setSearch("");
                  setPage(1);
                }}
                className="text-xs text-blue-600 hover:text-blue-800 font-semibold underline ml-auto"
              >
                Clear all filters
              </button>
            )}
          </div>
        </div>

        {/* Review Queue Table */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
          {loading ? (
            <div className="p-12 text-center">
              <RefreshCw className="mx-auto h-8 w-8 animate-spin text-blue-600" />
              <p className="mt-3 text-sm font-semibold text-slate-700">Loading Human Review Queue...</p>
              <p className="text-xs text-slate-500">Aggregating multi-source verification and compliance evidence.</p>
            </div>
          ) : error ? (
            <div className="p-8 text-center bg-rose-50/50">
              <XCircle className="mx-auto h-8 w-8 text-rose-600" />
              <p className="mt-2 text-sm font-bold text-rose-900">Failed to load review items</p>
              <p className="text-xs text-rose-700 mt-1">{error}</p>
              <button
                type="button"
                onClick={fetchQueue}
                className="mt-4 rounded-lg bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700"
              >
                Retry
              </button>
            </div>
          ) : items.length === 0 ? (
            <div className="p-16 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <p className="mt-4 text-base font-bold text-slate-800">All Human Review Items Resolved</p>
              <p className="mt-1 text-xs text-slate-500 max-w-md mx-auto">
                There are no open or pending human review items matching your current filters. Any new discrepancies will appear here automatically.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                  <tr>
                    <th scope="col" className="px-4 py-3">Discrepancy / Requirement</th>
                    <th scope="col" className="px-4 py-3">Tender</th>
                    <th scope="col" className="px-4 py-3">Bidder Organization</th>
                    <th scope="col" className="px-4 py-3">Review Type</th>
                    <th scope="col" className="px-4 py-3">Severity</th>
                    <th scope="col" className="px-4 py-3">Status</th>
                    <th scope="col" className="px-4 py-3">Created</th>
                    <th scope="col" className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.map((item) => (
                    <tr
                      key={item.id}
                      className={`hover:bg-slate-50/80 transition-colors ${
                        item.severity === "CRITICAL" ? "bg-rose-50/20" : ""
                      }`}
                    >
                      {/* Title & Reason */}
                      <td className="px-4 py-3.5 max-w-xs">
                        <div className="flex flex-col">
                          <span className="font-bold text-slate-900 line-clamp-1">{item.title}</span>
                          <span className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">{item.reason}</span>
                        </div>
                      </td>

                      {/* Tender */}
                      <td className="px-4 py-3.5">
                        <div className="flex flex-col">
                          <span className="font-semibold text-slate-800">{item.tender_number}</span>
                          <span className="text-[11px] text-slate-500 line-clamp-1">{item.tender_title}</span>
                        </div>
                      </td>

                      {/* Bidder */}
                      <td className="px-4 py-3.5">
                        <div className="flex flex-col">
                          <span className="font-bold text-slate-900">{item.bidder_name}</span>
                          <span className="text-[11px] text-slate-500 font-mono">{item.bid_number}</span>
                        </div>
                      </td>

                      {/* Review Type */}
                      <td className="px-4 py-3.5">
                        <span className="inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                          {formatReviewType(item.review_type)}
                        </span>
                      </td>

                      {/* Severity */}
                      <td className="px-4 py-3.5">{getSeverityBadge(item.severity)}</td>

                      {/* Status */}
                      <td className="px-4 py-3.5">
                        <div className="flex flex-col gap-1">
                          {getStatusBadge(item.status)}
                          {item.claimed_by_name && item.status === "IN_REVIEW" && (
                            <span className="text-[10px] text-purple-700 font-medium truncate">
                              by {item.claimed_by_name}
                            </span>
                          )}
                          {item.resolved_by_name && item.status === "RESOLVED" && (
                            <span className="text-[10px] text-emerald-700 font-medium truncate">
                              by {item.resolved_by_name}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Created Date */}
                      <td className="px-4 py-3.5 text-slate-500 text-[11px] whitespace-nowrap">
                        {new Date(item.created_at).toLocaleDateString()}
                      </td>

                      {/* Action */}
                      <td className="px-4 py-3.5 text-right whitespace-nowrap">
                        <Link
                          href={`/procurement/reviews/${item.id}`}
                          className="inline-flex items-center gap-1 rounded-lg bg-blue-900 px-3 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-blue-800 transition-colors"
                        >
                          Inspect Evidence
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          {!loading && items.length > 0 && (
            <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 bg-slate-50 text-xs">
              <div className="text-slate-500">
                Showing <span className="font-semibold text-slate-900">{(page - 1) * pageSize + 1}</span> to{" "}
                <span className="font-semibold text-slate-900">{Math.min(page * pageSize, totalCount)}</span> of{" "}
                <span className="font-semibold text-slate-900">{totalCount}</span> review items
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                  className="rounded border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed shadow-2xs"
                >
                  Previous
                </button>
                <span className="text-slate-600 font-medium">
                  Page {page} of {totalPages}
                </span>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                  className="rounded border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed shadow-2xs"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
