"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  api,
  ApiError,
  BidListItem,
  BidListResponse,
} from "@/lib/api";
import {
  formatCurrency,
  formatDateTime,
  formatDeadlineRemaining,
} from "@/lib/formatters";
import { StatusBadge } from "@/components/common/StatusBadge";
import {
  FileText,
  Search,
  Filter,
  ArrowRight,
  Clock,
  Building2,
  AlertCircle,
  Loader2,
  RefreshCw,
  PlusCircle,
  CheckCircle2,
  Layers,
  Calendar,
  FileEdit,
  ExternalLink,
  Eye,
} from "lucide-react";


export default function BidderBidsPage() {
  const [bids, setBids] = useState<BidListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filters & Pagination
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalBids, setTotalBids] = useState<number>(0);

  const fetchBids = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const resp: BidListResponse = await api.getMyBids({
        search: searchQuery.trim() || undefined,
        status: statusFilter || undefined,
        page,
        page_size: 10,
      });
      setBids(resp.items);
      setTotalPages(resp.total_pages);
      setTotalBids(resp.total);
    } catch (err: any) {
      setErrorMessage(
        err instanceof ApiError
          ? err.message
          : "Failed to load bid submissions. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBids();
  }, [page, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchBids();
  };

  const draftCount = bids.filter((b) => b.status === "DRAFT").length;

  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title="My Bids"
      description="View, edit, and track your tender participation and draft proposals."
      breadcrumbs={[
        { label: "Bidder Portal", href: "/bidder" },
        { label: "My Bids" },
      ]}
    >
      <div className="space-y-6">
        {/* Top Header & Actions Bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              Bid Participation Pipeline
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Manage your active proposals and continue draft bid workspaces.
            </p>
          </div>

          <Link
            href="/bidder/tenders"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-700 px-4 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-blue-800 transition-colors shrink-0"
          >
            <PlusCircle className="h-4 w-4" />
            Browse Open Tenders
          </Link>
        </div>

        {/* Stats Metrics Overview */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">
                Total Bids
              </span>
              <span className="rounded-lg bg-blue-50 p-2 text-blue-700">
                <Layers className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-2 text-2xl font-extrabold text-slate-900">
              {totalBids}
            </p>
            <p className="mt-1 text-[11px] text-slate-500">
              Tenders with registered participation
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">
                Draft Workspaces
              </span>
              <span className="rounded-lg bg-amber-50 p-2 text-amber-700">
                <FileEdit className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-2 text-2xl font-extrabold text-slate-900">
              {bids.filter((b) => b.status === "DRAFT").length}
            </p>
            <p className="mt-1 text-[11px] text-amber-700 font-medium">
              In preparation / editable
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">
                Submitted Proposals
              </span>
              <span className="rounded-lg bg-emerald-50 p-2 text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-2 text-2xl font-extrabold text-slate-900">
              {bids.filter((b) => b.status === "SUBMITTED").length}
            </p>
            <p className="mt-1 text-[11px] text-emerald-700 font-medium">
              Locked and verified proposals
            </p>
          </div>
        </div>


        {/* Filter & Search Bar */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            {/* Search Input */}
            <form onSubmit={handleSearchSubmit} className="w-full md:w-96">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search by bid number, tender title..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-slate-50/50 pl-9 pr-20 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-600"
                />
                <button
                  type="submit"
                  className="absolute right-1.5 top-1.5 rounded-md bg-slate-200 hover:bg-slate-300 px-2.5 py-1 text-[11px] font-semibold text-slate-700 transition-colors"
                >
                  Search
                </button>
              </div>
            </form>

            {/* Status Filter Tabs */}
            <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto">
              <span className="text-xs font-semibold text-slate-500 mr-1 flex items-center gap-1">
                <Filter className="h-3.5 w-3.5" />
                Status:
              </span>
              {[
                { label: "All Bids", value: "" },
                { label: "Draft", value: "DRAFT" },
                { label: "Submitted", value: "SUBMITTED" },
              ].map((tab) => (
                <button
                  key={tab.value}
                  onClick={() => {
                    setStatusFilter(tab.value);
                    setPage(1);
                  }}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors shrink-0 ${
                    statusFilter === tab.value
                      ? "bg-blue-700 text-white shadow-2xs"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Content Area */}
        {loading ? (
          <div className="rounded-xl border border-slate-200 bg-white p-16 text-center shadow-xs">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-700" />
            <p className="mt-3 text-sm font-medium text-slate-600">
              Loading your bid participation records...
            </p>
          </div>
        ) : errorMessage ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-8 text-center shadow-xs">
            <AlertCircle className="mx-auto h-10 w-10 text-rose-600" />
            <h3 className="mt-3 text-base font-bold text-rose-900">
              Failed to Load Bids
            </h3>
            <p className="mt-1 text-xs text-rose-700 max-w-md mx-auto">
              {errorMessage}
            </p>
            <button
              onClick={fetchBids}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700 shadow-xs"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </button>
          </div>
        ) : bids.length === 0 ? (
          /* Clean Empty State */
          <div className="rounded-xl border border-slate-200 bg-white p-16 text-center shadow-xs space-y-4">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-blue-50 text-blue-700 border border-blue-100">
              <FileText className="h-7 w-7" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-900">
                {searchQuery || statusFilter
                  ? "No matching bids found"
                  : "No bids created yet"}
              </h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
                {searchQuery || statusFilter
                  ? "Try adjusting your search keywords or status filter."
                  : "Explore open tenders across government entities and start your first draft bid workspace."}
              </p>
            </div>
            {searchQuery || statusFilter ? (
              <button
                onClick={() => {
                  setSearchQuery("");
                  setStatusFilter("");
                  setPage(1);
                }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs"
              >
                Clear Filters
              </button>
            ) : (
              <Link
                href="/bidder/tenders"
                className="inline-flex items-center gap-2 rounded-lg bg-blue-700 px-5 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-blue-800 transition-colors"
              >
                <PlusCircle className="h-4 w-4" />
                Browse Open Tenders
              </Link>
            )}
          </div>
        ) : (
          /* Bids Table / Grid */
          <div className="space-y-4">
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-700">
                  <thead className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-700">
                    <tr>
                      <th className="py-3.5 px-4">Bid Reference</th>
                      <th className="py-3.5 px-4">Tender Details</th>
                      <th className="py-3.5 px-4">Quoted Amount</th>
                      <th className="py-3.5 px-4">Status</th>
                      <th className="py-3.5 px-4">Submission Deadline</th>
                      <th className="py-3.5 px-4">Last Updated</th>
                      <th className="py-3.5 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {bids.map((bid) => {
                      const deadline = formatDeadlineRemaining(bid.submission_end_date);
                      return (
                        <tr
                          key={bid.id}
                          className="hover:bg-slate-50/75 transition-colors"
                        >
                          {/* Bid Reference Number */}
                          <td className="py-4 px-4 font-mono font-bold text-slate-900 whitespace-nowrap">
                            <span className="inline-flex items-center gap-1 bg-slate-100 px-2 py-1 rounded border border-slate-200 text-slate-800">
                              {bid.bid_number}
                            </span>
                          </td>

                          {/* Tender Details */}
                          <td className="py-4 px-4 max-w-xs">
                            <div className="space-y-1">
                              <span className="font-mono text-[11px] text-blue-700 font-semibold">
                                {bid.tender_number}
                              </span>
                              <p className="font-bold text-slate-900 line-clamp-1 hover:text-blue-700 transition-colors">
                                <Link href={`/bidder/tenders/${bid.tender_id}`}>
                                  {bid.tender_title}
                                </Link>
                              </p>
                              {bid.procuring_organization_name && (
                                <p className="text-[11px] text-slate-500 flex items-center gap-1">
                                  <Building2 className="h-3 w-3 shrink-0" />
                                  <span className="truncate">{bid.procuring_organization_name}</span>
                                </p>
                              )}
                            </div>
                          </td>

                          {/* Quoted Commercial Amount */}
                          <td className="py-4 px-4 font-mono font-bold text-slate-900 whitespace-nowrap">
                            {bid.quoted_amount ? (
                              <span className="text-emerald-700">
                                {formatCurrency(bid.quoted_amount, bid.currency)}
                              </span>
                            ) : (
                              <span className="text-slate-400 font-sans text-xs italic">
                                Not quoted yet
                              </span>
                            )}
                          </td>

                          {/* Bid Status Badge */}
                          <td className="py-4 px-4 whitespace-nowrap">
                            <StatusBadge status={bid.status} size="sm" />
                          </td>

                          {/* Submission Deadline */}
                          <td className="py-4 px-4 whitespace-nowrap">
                            <div className="space-y-0.5">
                              <p className="font-medium text-slate-800 text-[11px]">
                                {formatDateTime(bid.submission_end_date)}
                              </p>
                              <span
                                className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-bold border ${deadline.colorClass}`}
                              >
                                {deadline.text}
                              </span>
                            </div>
                          </td>

                          {/* Last Updated */}
                          <td className="py-4 px-4 text-slate-500 text-[11px] whitespace-nowrap">
                            {formatDateTime(bid.updated_at)}
                          </td>

                          {/* Action Button */}
                          <td className="py-4 px-4 text-right whitespace-nowrap">
                            <Link
                              href={`/bidder/bids/${bid.id}`}
                              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold border transition-colors shadow-2xs ${
                                bid.status === "SUBMITTED"
                                  ? "bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border-emerald-200"
                                  : "bg-blue-50 hover:bg-blue-100 text-blue-700 border-blue-200"
                              }`}
                            >
                              {bid.status === "SUBMITTED" ? (
                                <>
                                  <Eye className="h-3.5 w-3.5" />
                                  View Submitted Bid
                                </>
                              ) : (
                                <>
                                  <FileEdit className="h-3.5 w-3.5" />
                                  Continue Proposal
                                  <ArrowRight className="h-3.5 w-3.5" />
                                </>
                              )}
                            </Link>
                          </td>
                        </tr>

                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-2 py-2">
                <span className="text-xs text-slate-500">
                  Page <strong>{page}</strong> of <strong>{totalPages}</strong> ({totalBids} bids total)
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 transition-colors"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
