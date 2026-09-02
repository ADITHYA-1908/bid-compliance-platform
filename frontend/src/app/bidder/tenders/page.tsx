"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  api,
  ApiError,
  BidderTenderSummary,
  BidderTenderListParams,
} from "@/lib/api";
import { formatCurrency, formatDate, formatDeadlineRemaining } from "@/lib/formatters";
import {
  Search,
  Filter,
  Building2,
  Calendar,
  IndianRupee,
  ShieldCheck,
  ArrowRight,
  RotateCcw,
  Loader2,
  AlertCircle,
  FileText,
  Clock,
  Sparkles,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const CATEGORIES = [
  "IT & Telecom",
  "Civil & Electrical",
  "Medical & Healthcare",
  "Consulting & Advisory",
  "Heavy Equipment",
  "Defence & Security",
  "Facility Management",
  "Logistics & Transportation",
  "Services",
  "Other",
];

const PROCUREMENT_TYPES = ["Goods", "Services", "Works"];

const SORT_OPTIONS = [
  { value: "newest", label: "Newest First" },
  { value: "deadline", label: "Deadline Approaching" },
  { value: "value_high", label: "Highest Value" },
  { value: "value_low", label: "Lowest Value" },
];

export default function BidderTendersPage() {
  const [tenders, setTenders] = useState<BidderTenderSummary[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filter & Search state
  const [searchInput, setSearchInput] = useState<string>("");
  const [activeSearch, setActiveSearch] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [procurementTypeFilter, setProcurementTypeFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("newest");

  const fetchTenders = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);

    const params: BidderTenderListParams = {
      search: activeSearch.trim() || undefined,
      category: categoryFilter || undefined,
      procurement_type: procurementTypeFilter || undefined,
      status: statusFilter || undefined,
      sort_by: sortBy,
      page: page,
      page_size: 9,
    };

    try {
      const response = await api.getAvailableTenders(params);
      setTenders(response.items);
      setTotal(response.total);
      setTotalPages(response.total_pages);
    } catch (err: any) {
      setErrorMessage(
        err instanceof ApiError ? err.message : "Failed to fetch available tenders."
      );
    } finally {
      setLoading(false);
    }
  }, [activeSearch, categoryFilter, procurementTypeFilter, statusFilter, sortBy, page]);

  useEffect(() => {
    fetchTenders();
  }, [fetchTenders]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setActiveSearch(searchInput);
  };

  const handleResetFilters = () => {
    setSearchInput("");
    setActiveSearch("");
    setCategoryFilter("");
    setProcurementTypeFilter("");
    setStatusFilter("");
    setSortBy("newest");
    setPage(1);
  };

  const hasActiveFilters =
    Boolean(activeSearch) ||
    Boolean(categoryFilter) ||
    Boolean(procurementTypeFilter) ||
    Boolean(statusFilter) ||
    sortBy !== "newest";

  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title="Available Tenders"
      description="Discover, search, and analyze public procurement opportunities open for bidding across all government buyers."
      breadcrumbs={[
        { label: "Bidder Portal", href: "/bidder" },
        { label: "Tenders" },
      ]}
    >
      <div className="space-y-6">
        {/* Search & Filter Toolbar */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
          {/* Top Search Bar */}
          <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <Search className="h-4 w-4 text-slate-400" />
              </div>
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search by tender title, GEM reference, department, or keyword..."
                className="block w-full rounded-lg border border-slate-300 bg-slate-50/50 pl-9.5 pr-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
              />
            </div>
            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors shadow-xs"
            >
              <Search className="h-4 w-4" />
              Search Tenders
            </button>
          </form>

          {/* Filter Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-3 border-t border-slate-100">
            {/* Category Filter */}
            <div>
              <label htmlFor="category" className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Category
              </label>
              <select
                id="category"
                value={categoryFilter}
                onChange={(e) => {
                  setCategoryFilter(e.target.value);
                  setPage(1);
                }}
                className="block w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700"
              >
                <option value="">All Categories</option>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            {/* Procurement Type Filter */}
            <div>
              <label htmlFor="procType" className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Procurement Type
              </label>
              <select
                id="procType"
                value={procurementTypeFilter}
                onChange={(e) => {
                  setProcurementTypeFilter(e.target.value);
                  setPage(1);
                }}
                className="block w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700"
              >
                <option value="">All Types (Goods/Services/Works)</option>
                {PROCUREMENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            {/* Status Filter */}
            <div>
              <label htmlFor="status" className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Participation State
              </label>
              <select
                id="status"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="block w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700"
              >
                <option value="">All Open & Upcoming</option>
                <option value="OPEN">Open for Bidding</option>
                <option value="PUBLISHED">Upcoming Notices</option>
              </select>
            </div>

            {/* Sort Options */}
            <div>
              <label htmlFor="sort" className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Sort By
              </label>
              <select
                id="sort"
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setPage(1);
                }}
                className="block w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700"
              >
                {SORT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Active Filter Badges & Reset Button */}
          {hasActiveFilters && (
            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-500">Active Filters:</span>
                {activeSearch && (
                  <span className="rounded bg-blue-50 px-2 py-0.5 font-medium text-blue-700 border border-blue-200">
                    Keyword: &quot;{activeSearch}&quot;
                  </span>
                )}
                {categoryFilter && (
                  <span className="rounded bg-slate-100 px-2 py-0.5 font-medium text-slate-700 border border-slate-200">
                    Category: {categoryFilter}
                  </span>
                )}
                {procurementTypeFilter && (
                  <span className="rounded bg-slate-100 px-2 py-0.5 font-medium text-slate-700 border border-slate-200">
                    Type: {procurementTypeFilter}
                  </span>
                )}
                {statusFilter && (
                  <span className="rounded bg-slate-100 px-2 py-0.5 font-medium text-slate-700 border border-slate-200">
                    Status: {statusFilter}
                  </span>
                )}
              </div>
              <button
                onClick={handleResetFilters}
                className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600 hover:text-rose-600 transition-colors"
              >
                <RotateCcw className="h-3 w-3" />
                Reset All Filters
              </button>
            </div>
          )}
        </div>

        {/* Results Header */}
        <div className="flex items-center justify-between px-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {loading ? "Searching..." : `Showing ${tenders.length} of ${total} Opportunities`}
          </p>
          <span className="text-xs text-slate-500">
            GeM Procurement Bridge Active
          </span>
        </div>

        {/* Tender Cards Grid or Loading / Error / Empty States */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs animate-pulse space-y-4"
              >
                <div className="flex items-center justify-between">
                  <div className="h-5 w-24 rounded bg-slate-200" />
                  <div className="h-5 w-16 rounded bg-slate-200" />
                </div>
                <div className="space-y-2">
                  <div className="h-4 w-full rounded bg-slate-200" />
                  <div className="h-4 w-3/4 rounded bg-slate-200" />
                </div>
                <div className="h-10 rounded bg-slate-100" />
                <div className="h-8 rounded bg-slate-200" />
              </div>
            ))}
          </div>
        ) : errorMessage ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-8 text-center shadow-xs">
            <AlertCircle className="mx-auto h-8 w-8 text-rose-600" />
            <h3 className="mt-2 text-sm font-bold text-rose-900">
              Unable to Load Tenders
            </h3>
            <p className="mt-1 text-xs text-rose-700">{errorMessage}</p>
            <button
              onClick={fetchTenders}
              className="mt-4 inline-flex items-center gap-1.5 rounded-md bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700 shadow-xs"
            >
              Retry Discovery
            </button>
          </div>
        ) : tenders.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-xs">
            <FileText className="mx-auto h-12 w-12 text-slate-300" />
            <h3 className="mt-3 text-base font-bold text-slate-900">
              No Tenders Available
            </h3>
            <p className="mt-1 text-xs text-slate-500 max-w-md mx-auto">
              {hasActiveFilters
                ? "No procurement opportunities matched your search criteria. Try modifying or clearing your filters."
                : "There are currently no active public procurement notices open for bidding. Please check back soon."}
            </p>
            {hasActiveFilters && (
              <button
                onClick={handleResetFilters}
                className="mt-4 inline-flex items-center gap-1.5 rounded-md bg-blue-700 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-800 shadow-xs"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Clear Filters
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {tenders.map((tender) => {
              const deadline = formatDeadlineRemaining(tender.submission_end_date);
              const isOpen = tender.status === "OPEN";

              return (
                <div
                  key={tender.id}
                  className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-xs hover:shadow-md hover:border-blue-300 transition-all group"
                >
                  <div className="space-y-3.5">
                    {/* Status & Reference Header */}
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-[11px] font-bold text-slate-500 tracking-wide">
                        {tender.tender_number}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold border ${
                          isOpen
                            ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                            : "bg-blue-50 text-blue-800 border-blue-200"
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            isOpen ? "bg-emerald-600 animate-pulse" : "bg-blue-600"
                          }`}
                        />
                        {isOpen ? "OPEN FOR BIDDING" : "UPCOMING"}
                      </span>
                    </div>

                    {/* Title */}
                    <div>
                      <Link
                        href={`/bidder/tenders/${tender.id}`}
                        className="text-sm font-bold text-slate-900 group-hover:text-blue-700 line-clamp-2 transition-colors"
                      >
                        {tender.title}
                      </Link>
                      <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                        {tender.category && (
                          <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                            {tender.category}
                          </span>
                        )}
                        {tender.procurement_type && (
                          <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                            {tender.procurement_type}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Procuring Entity */}
                    <div className="flex items-start gap-2 text-xs text-slate-600 pt-1">
                      <Building2 className="h-4 w-4 shrink-0 text-slate-400 mt-0.5" />
                      <div className="line-clamp-1">
                        <span className="font-semibold text-slate-800">
                          {tender.organization_name || "Procuring Authority"}
                        </span>
                        {tender.organization_city && (
                          <span className="text-slate-500">
                            {" "}
                            • {tender.organization_city}
                            {tender.organization_state ? `, ${tender.organization_state}` : ""}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Value and Dates Card */}
                    <div className="rounded-lg bg-slate-50 p-3 border border-slate-200/75 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-slate-500 font-medium">
                          Estimated Value
                        </span>
                        <span className="font-mono font-bold text-slate-900 text-sm">
                          {formatCurrency(tender.estimated_value, tender.currency)}
                        </span>
                      </div>

                      <div className="flex items-center justify-between pt-1 border-t border-slate-200/60 text-xs">
                        <div className="flex items-center gap-1 text-slate-500 text-[11px]">
                          <Calendar className="h-3.5 w-3.5" />
                          <span>Deadline: {formatDate(tender.submission_end_date)}</span>
                        </div>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-bold border ${deadline.colorClass}`}
                        >
                          {deadline.text}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Card Footer */}
                  <div className="pt-4 mt-4 border-t border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-1 text-[11px] text-slate-500 font-medium">
                      <ShieldCheck className="h-3.5 w-3.5 text-blue-700" />
                      <span>{tender.active_requirements_count} Rules</span>
                    </div>

                    <Link
                      href={`/bidder/tenders/${tender.id}`}
                      className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700 group-hover:bg-blue-700 group-hover:text-white transition-colors"
                    >
                      View Details
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination Controls */}
        {!loading && totalPages > 1 && (
          <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-5 py-3.5 shadow-xs">
            <p className="text-xs text-slate-600 font-medium">
              Page <span className="font-bold text-slate-900">{page}</span> of{" "}
              <span className="font-bold text-slate-900">{totalPages}</span>
            </p>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 transition-colors shadow-xs"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                Previous
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 transition-colors shadow-xs"
              >
                Next
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
