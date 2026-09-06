"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Award,
  AlertTriangle,
  CheckCircle2,
  Clock,
  XCircle,
  FileCheck2,
  FileText,
  Filter,
  Info,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Upload,
  Calendar,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { certificateValidityApi } from "@/lib/api/certificate_validity";
import {
  DocumentValidityItem,
  CertificateValidityStats,
  ValidityStatus,
} from "@/types/certificate_validity";

function BidderCertificatesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  const [items, setItems] = useState<DocumentValidityItem[]>([]);
  const [stats, setStats] = useState<CertificateValidityStats>({
    total_monitored: 0,
    valid_count: 0,
    expiring_soon_count: 0,
    expired_count: 0,
    no_expiry_count: 0,
    review_required_count: 0,
    unknown_count: 0,
  });

  const [totalCount, setTotalCount] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize] = useState<number>(15);

  const [activeTab, setActiveTab] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [recheckingId, setRecheckingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchCertificates = useCallback(
    async (page: number = 1, showRefresh: boolean = false) => {
      if (!user) return;
      if (showRefresh) setIsRefreshing(true);
      else setIsLoading(true);
      setError(null);

      try {
        const filterStatus = activeTab === "ALL" ? undefined : activeTab;
        const res = await certificateValidityApi.getBidderCertificates({
          page,
          page_size: pageSize,
          status: filterStatus,
          search: searchQuery.trim() || undefined,
        });

        setItems(res.items || []);
        setStats(res.stats || {
          total_monitored: 0,
          valid_count: 0,
          expiring_soon_count: 0,
          expired_count: 0,
          no_expiry_count: 0,
          review_required_count: 0,
          unknown_count: 0,
        });
        setTotalCount(res.total || 0);
        setTotalPages(res.total_pages || 1);
        setCurrentPage(res.page || 1);
      } catch (err: any) {
        setError(err.message || "Failed to load certificate validity records.");
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [user, activeTab, searchQuery, pageSize]
  );

  useEffect(() => {
    fetchCertificates(1);
  }, [fetchCertificates]);

  const handleRecheck = async (documentId: string) => {
    setRecheckingId(documentId);
    try {
      const res = await certificateValidityApi.recheckDocumentValidity(documentId);
      setItems((prev) =>
        prev.map((item) => (item.document_id === documentId ? res.record : item))
      );
      // Refresh list to update stats
      fetchCertificates(currentPage, true);
    } catch (err: any) {
      alert(err.message || "Failed to recheck document validity.");
    } finally {
      setRecheckingId(null);
    }
  };

  const getStatusBadge = (statusStr: string) => {
    switch (statusStr) {
      case ValidityStatus.VALID:
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
            VALID
          </span>
        );
      case ValidityStatus.EXPIRING_SOON:
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-700 border border-amber-200">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-600 shrink-0" />
            EXPIRING SOON
          </span>
        );
      case ValidityStatus.EXPIRED:
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-0.5 text-xs font-bold text-rose-700 border border-rose-200">
            <XCircle className="h-3.5 w-3.5 text-rose-600 shrink-0" />
            EXPIRED
          </span>
        );
      case ValidityStatus.NO_EXPIRY:
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
            PERMANENT / NO EXPIRY
          </span>
        );
      case ValidityStatus.REVIEW_REQUIRED:
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-800 border border-amber-200">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-600 shrink-0" />
            REVIEW REQUIRED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-bold text-slate-600 border border-slate-200">
            <Clock className="h-3.5 w-3.5 text-slate-500 shrink-0" />
            UNKNOWN
          </span>
        );
    }
  };

  const getDaysRemainingPill = (days?: number | null, statusStr?: string) => {
    if (statusStr === ValidityStatus.NO_EXPIRY) {
      return (
        <span className="text-xs font-medium text-slate-500">
          Permanent
        </span>
      );
    }
    if (days === null || days === undefined) {
      return <span className="text-xs text-slate-400">N/A</span>;
    }
    if (days < 0) {
      return (
        <span className="inline-flex items-center rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-bold text-rose-800">
          Expired {Math.abs(days)}d ago
        </span>
      );
    }
    if (days <= 1) {
      return (
        <span className="inline-flex items-center rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-bold text-rose-800 animate-pulse">
          {days === 0 ? "Expires Today" : "1 day left"}
        </span>
      );
    }
    if (days <= 7) {
      return (
        <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-800">
          {days} days left
        </span>
      );
    }
    if (days <= 30) {
      return (
        <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700 border border-amber-200">
          {days} days left
        </span>
      );
    }
    return (
      <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 border border-emerald-200">
        {days} days remaining
      </span>
    );
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "—";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["BIDDER", "ADMIN"]}
      title="Certificate Validity Monitoring"
      description="Track statutory certificate expiry dates, renewal warnings, and update compliance documentation"
      breadcrumbs={[{ label: "Certificates & Validity" }]}
    >
      <div className="space-y-6 pb-16">
        {/* Top Summary Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Monitored</span>
              <Award className="h-4 w-4 text-blue-900" />
            </div>
            <p className="mt-2 text-xl font-black text-slate-900">{stats.total_monitored}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">Total documents</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Valid</span>
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            </div>
            <p className="mt-2 text-xl font-black text-emerald-700">{stats.valid_count}</p>
            <p className="text-[10px] text-emerald-600 font-medium mt-0.5">&gt; 30 days remaining</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Expiring Soon</span>
              <Clock className="h-4 w-4 text-amber-500" />
            </div>
            <p className="mt-2 text-xl font-black text-amber-600">{stats.expiring_soon_count}</p>
            <p className="text-[10px] text-amber-600 font-medium mt-0.5">Within 30 days</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Expired</span>
              <ShieldAlert className="h-4 w-4 text-rose-500" />
            </div>
            <p className="mt-2 text-xl font-black text-rose-600">{stats.expired_count}</p>
            <p className="text-[10px] text-rose-600 font-medium mt-0.5">Renewal required</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Permanent</span>
              <ShieldCheck className="h-4 w-4 text-blue-600" />
            </div>
            <p className="mt-2 text-xl font-black text-blue-700">{stats.no_expiry_count}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">PAN / Udyam / History</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Review</span>
              <AlertTriangle className="h-4 w-4 text-purple-500" />
            </div>
            <p className="mt-2 text-xl font-black text-purple-700">{stats.review_required_count}</p>
            <p className="text-[10px] text-purple-600 font-medium mt-0.5">Uncertain scan/date</p>
          </div>
        </div>

        {/* Filters and Search Bar */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-3">
          {/* Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 md:pb-0">
            {[
              { id: "ALL", label: "All Documents", count: stats.total_monitored },
              { id: ValidityStatus.EXPIRING_SOON, label: "Expiring Soon", count: stats.expiring_soon_count },
              { id: ValidityStatus.EXPIRED, label: "Expired", count: stats.expired_count },
              { id: ValidityStatus.VALID, label: "Valid", count: stats.valid_count },
              { id: ValidityStatus.REVIEW_REQUIRED, label: "Review Required", count: stats.review_required_count },
              { id: ValidityStatus.NO_EXPIRY, label: "Permanent", count: stats.no_expiry_count },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setActiveTab(tab.id);
                  setCurrentPage(1);
                }}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors cursor-pointer whitespace-nowrap ${
                  activeTab === tab.id
                    ? "bg-blue-900 text-white shadow-2xs"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <span>{tab.label}</span>
                {tab.count !== undefined && tab.count > 0 && (
                  <span
                    className={`rounded-full px-1.5 py-0.2 text-[10px] font-bold ${
                      activeTab === tab.id
                        ? "bg-blue-800 text-blue-100"
                        : "bg-slate-200 text-slate-700"
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Search & Actions */}
          <div className="flex items-center gap-2">
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search certificate name/evidence..."
                className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-xs text-slate-900 focus:border-blue-900 focus:outline-hidden focus:ring-1 focus:ring-blue-900"
              />
            </div>

            <button
              type="button"
              onClick={() => fetchCertificates(currentPage, true)}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin text-blue-900" : "text-slate-500"}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-medium text-red-800 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Certificate Table */}
        <div className="rounded-2xl border border-slate-200 bg-white shadow-2xs overflow-hidden">
          {isLoading && !isRefreshing ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <RefreshCw className="h-6 w-6 animate-spin text-blue-900 mb-2" />
              <p className="text-xs font-semibold text-slate-600">Loading certificate validity records...</p>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <FileCheck2 className="h-10 w-10 stroke-1 text-slate-300 mb-2" />
              <p className="text-sm font-semibold text-slate-700">No certificates found</p>
              <p className="text-xs text-slate-400 mt-0.5">
                {searchQuery
                  ? "Try adjusting your search query"
                  : "No certificate validity records match the current filter."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                    <th className="py-3 px-4">Document / Certificate</th>
                    <th className="py-3 px-3">Type</th>
                    <th className="py-3 px-3">Issue Date</th>
                    <th className="py-3 px-3">Expiry Date</th>
                    <th className="py-3 px-3">Validity Status</th>
                    <th className="py-3 px-3">Countdown</th>
                    <th className="py-3 px-3">Evidence / Source</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.map((item) => {
                    const isRechecking = recheckingId === item.document_id;
                    const isExpiringOrExpired =
                      item.validity_status === ValidityStatus.EXPIRING_SOON ||
                      item.validity_status === ValidityStatus.EXPIRED;

                    return (
                      <tr
                        key={item.id}
                        className={`hover:bg-slate-50/80 transition-colors ${
                          item.validity_status === ValidityStatus.EXPIRED
                            ? "bg-rose-50/15"
                            : item.validity_status === ValidityStatus.EXPIRING_SOON
                            ? "bg-amber-50/15"
                            : ""
                        }`}
                      >
                        <td className="py-3 px-4 font-semibold text-slate-900">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-blue-900 shrink-0" />
                            <span className="truncate max-w-xs" title={item.document_name || item.document_type}>
                              {item.document_name || item.document_type}
                            </span>
                          </div>
                        </td>

                        <td className="py-3 px-3 text-slate-600 font-medium">
                          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-700">
                            {item.document_type.replace(/_/g, " ")}
                          </span>
                        </td>

                        <td className="py-3 px-3 text-slate-600">
                          {formatDate(item.issue_date)}
                        </td>

                        <td className="py-3 px-3 font-semibold text-slate-800">
                          {formatDate(item.expiry_date)}
                        </td>

                        <td className="py-3 px-3">
                          {getStatusBadge(item.validity_status)}
                        </td>

                        <td className="py-3 px-3">
                          {getDaysRemainingPill(item.days_until_expiry, item.validity_status)}
                        </td>

                        <td className="py-3 px-3 text-slate-500 max-w-xs">
                          {item.source_text ? (
                            <span
                              className="italic text-[11px] truncate block text-slate-600"
                              title={item.source_text}
                            >
                              &ldquo;{item.source_text}&rdquo;
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>

                        <td className="py-3 px-4 text-right">
                          <div className="inline-flex items-center gap-1.5 justify-end">
                            <button
                              type="button"
                              onClick={() => handleRecheck(item.document_id)}
                              disabled={isRechecking}
                              className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-600 hover:border-blue-900 hover:text-blue-900 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
                              title="Recheck validity"
                            >
                              <RefreshCw className={`h-3.5 w-3.5 ${isRechecking ? "animate-spin text-blue-900" : ""}`} />
                            </button>

                            {isExpiringOrExpired && (
                              <button
                                type="button"
                                onClick={() => router.push(`/bidder/bids`)}
                                className="inline-flex items-center gap-1 rounded-lg bg-blue-900 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-blue-800 transition-colors shadow-2xs cursor-pointer"
                                title="Upload replacement document"
                              >
                                <Upload className="h-3 w-3" />
                                <span>Replace</span>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Pagination Toolbar */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-200 pt-4 text-xs">
            <span className="text-slate-500">
              Showing page <strong className="text-slate-800">{currentPage}</strong> of{" "}
              <strong className="text-slate-800">{totalPages}</strong> ({totalCount} total certificates)
            </span>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => fetchCertificates(currentPage - 1)}
                disabled={currentPage <= 1 || isLoading}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors shadow-2xs cursor-pointer"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                Previous
              </button>

              <button
                type="button"
                onClick={() => fetchCertificates(currentPage + 1)}
                disabled={currentPage >= totalPages || isLoading}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors shadow-2xs cursor-pointer"
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

export default function BidderCertificatesPage() {
  return (
    <React.Suspense fallback={<div className="p-8 text-center text-xs text-slate-400">Loading certificate monitor...</div>}>
      <BidderCertificatesContent />
    </React.Suspense>
  );
}
