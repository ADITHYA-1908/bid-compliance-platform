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
  Calendar,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Eye,
  X,
  Sparkles,
} from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { certificateValidityApi } from "@/lib/api/certificate_validity";
import {
  DocumentValidityItem,
  ValidityStatus,
} from "@/types/certificate_validity";

function ProcurementCertificatesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  const [items, setItems] = useState<DocumentValidityItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize] = useState<number>(15);

  const [activeTab, setActiveTab] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [tenderFilter, setTenderFilter] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [recheckingId, setRecheckingId] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<DocumentValidityItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchCertificates = useCallback(
    async (page: number = 1, showRefresh: boolean = false) => {
      if (!user) return;
      if (showRefresh) setIsRefreshing(true);
      else setIsLoading(true);
      setError(null);

      try {
        const filterStatus = activeTab === "ALL" ? undefined : activeTab;
        const res = await certificateValidityApi.getProcurementCertificates({
          page,
          page_size: pageSize,
          tender_id: tenderFilter || undefined,
          status: filterStatus,
          search: searchQuery.trim() || undefined,
        });

        setItems(res.items || []);
        setTotalCount(res.total || 0);
        setTotalPages(res.total_pages || 1);
        setCurrentPage(res.page || 1);
      } catch (err: any) {
        setError(err.message || "Failed to load procurement certificates.");
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [user, activeTab, tenderFilter, searchQuery, pageSize]
  );

  useEffect(() => {
    fetchCertificates(1);
  }, [fetchCertificates]);

  const handleRecheck = async (documentId: string) => {
    setRecheckingId(documentId);
    try {
      const res = await certificateValidityApi.procurementRecheckDocument(documentId);
      setItems((prev) =>
        prev.map((item) => (item.document_id === documentId ? res.record : item))
      );
      if (selectedItem?.document_id === documentId) {
        setSelectedItem(res.record);
      }
    } catch (err: any) {
      alert(err.message || "Failed to recheck document validity.");
    } finally {
      setRecheckingId(null);
    }
  };

  const handleTriggerBatchCheck = async () => {
    try {
      setIsRefreshing(true);
      const res = await certificateValidityApi.triggerPeriodicCheck();
      alert(`Periodic batch check completed: ${res.total_checked} certificates evaluated, ${res.status_transitions} status transitions.`);
      fetchCertificates(currentPage, true);
    } catch (err: any) {
      alert(err.message || "Failed to execute batch validity check.");
      setIsRefreshing(false);
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
            NO EXPIRY
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
      return <span className="text-xs font-medium text-slate-500">Permanent</span>;
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
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Certificate Validity Monitor"
      description="Monitor statutory certificate expiration, inspect provenance snippets, and audit bidder compliance dates"
      breadcrumbs={[{ label: "Certificate Monitor" }]}
    >
      <div className="space-y-6 pb-16">
        {/* Top Control Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
          <div className="flex items-center gap-3.5">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-900 text-white shadow-xs">
              <Award className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Statutory Certificate Expiry Surveillance
              </h2>
              <p className="text-xs text-slate-500">
                Surveillance and countdown tracking across all submitted bidder certificates.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {user?.role === "ADMIN" && (
              <button
                type="button"
                onClick={handleTriggerBatchCheck}
                disabled={isRefreshing}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
                title="Run periodic expiration batch scan"
              >
                <Sparkles className="h-3.5 w-3.5 text-blue-900" />
                <span>Run Batch Scan</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => fetchCertificates(currentPage, true)}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-900 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-800 shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Filters and Tabs */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-3">
          <div className="flex items-center gap-1 overflow-x-auto pb-1 md:pb-0">
            {[
              { id: "ALL", label: "All Certificates" },
              { id: ValidityStatus.EXPIRING_SOON, label: "Expiring Soon" },
              { id: ValidityStatus.EXPIRED, label: "Expired" },
              { id: ValidityStatus.REVIEW_REQUIRED, label: "Review Required" },
              { id: ValidityStatus.VALID, label: "Valid" },
              { id: ValidityStatus.NO_EXPIRY, label: "Permanent" },
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
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search certificate or snippet..."
                className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-xs text-slate-900 focus:border-blue-900 focus:outline-hidden focus:ring-1 focus:ring-blue-900"
              />
            </div>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-medium text-red-800 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Table */}
        <div className="rounded-2xl border border-slate-200 bg-white shadow-2xs overflow-hidden">
          {isLoading && !isRefreshing ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <RefreshCw className="h-6 w-6 animate-spin text-blue-900 mb-2" />
              <p className="text-xs font-semibold text-slate-600">Loading certificate records...</p>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <FileCheck2 className="h-10 w-10 stroke-1 text-slate-300 mb-2" />
              <p className="text-sm font-semibold text-slate-700">No certificates found</p>
              <p className="text-xs text-slate-400 mt-0.5">
                {searchQuery
                  ? "Try adjusting your search query"
                  : "No certificate records match the selected filter."}
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
                    <th className="py-3 px-3">Confidence</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.map((item) => {
                    const isRechecking = recheckingId === item.document_id;
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

                        <td className="py-3 px-3 text-slate-600">
                          <span
                            className={`font-semibold ${
                              item.confidence >= 0.8
                                ? "text-emerald-700"
                                : item.confidence >= 0.6
                                ? "text-amber-700"
                                : "text-rose-700"
                            }`}
                          >
                            {Math.round(item.confidence * 100)}%
                          </span>
                        </td>

                        <td className="py-3 px-4 text-right">
                          <div className="inline-flex items-center gap-1.5 justify-end">
                            <button
                              type="button"
                              onClick={() => setSelectedItem(item)}
                              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
                              title="Inspect evidence details"
                            >
                              <Eye className="h-3.5 w-3.5 text-blue-900" />
                              <span>Inspect</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => handleRecheck(item.document_id)}
                              disabled={isRechecking}
                              className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-600 hover:border-blue-900 hover:text-blue-900 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
                              title="Re-evaluate validity"
                            >
                              <RefreshCw className={`h-3.5 w-3.5 ${isRechecking ? "animate-spin text-blue-900" : ""}`} />
                            </button>
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

        {/* Details Inspector Modal */}
        {selectedItem && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
            <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-6 shadow-xl animate-in fade-in zoom-in-95">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-900 text-white shadow-2xs">
                    <Award className="h-4.5 w-4.5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Certificate Validity Evidence</h3>
                    <p className="text-[11px] text-slate-500">{selectedItem.document_name || selectedItem.document_type}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="mt-4 space-y-3.5 text-xs">
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Validity Status</span>
                    <div className="mt-1">{getStatusBadge(selectedItem.validity_status)}</div>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Expiry Date</span>
                    <p className="mt-1 font-bold text-slate-900">{formatDate(selectedItem.expiry_date)}</p>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 p-3.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Extracted Evidence Snippet</span>
                  <div className="mt-1.5 rounded-lg bg-slate-50 p-2.5 font-mono text-[11px] text-slate-700 leading-relaxed border border-slate-100">
                    {selectedItem.source_text ? `"${selectedItem.source_text}"` : "No snippet available"}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-xl border border-slate-200 p-3">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Confidence</span>
                    <p className="mt-1 font-bold text-slate-900">{Math.round(selectedItem.confidence * 100)}%</p>
                  </div>

                  <div className="rounded-xl border border-slate-200 p-3">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Source</span>
                    <p className="mt-1 font-semibold text-slate-700">{selectedItem.date_source}</p>
                  </div>

                  <div className="rounded-xl border border-slate-200 p-3">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Submission Status</span>
                    <p className="mt-1 font-semibold text-slate-700">{selectedItem.submission_validity_status || "N/A"}</p>
                  </div>
                </div>

                {selectedItem.metadata_json?.quality_level && (
                  <div className="rounded-xl border border-slate-200 p-3 bg-slate-50/30">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Document Quality Impact (Part 11)</span>
                    <p className="mt-1 text-slate-700">
                      Quality Level: <strong className="text-slate-900">{selectedItem.metadata_json.quality_level}</strong> (Score: {selectedItem.metadata_json.quality_score}/100)
                    </p>
                  </div>
                )}
              </div>

              <div className="mt-6 flex items-center justify-end gap-2.5 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  className="rounded-lg border border-slate-200 bg-white px-4 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={() => handleRecheck(selectedItem.document_id)}
                  disabled={recheckingId === selectedItem.document_id}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-900 px-4 py-1.5 text-xs font-semibold text-white hover:bg-blue-800 transition-colors shadow-xs cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${recheckingId === selectedItem.document_id ? "animate-spin" : ""}`} />
                  <span>Re-evaluate</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

export default function ProcurementCertificatesPage() {
  return (
    <React.Suspense fallback={<div className="p-8 text-center text-xs text-slate-400">Loading certificate monitor...</div>}>
      <ProcurementCertificatesContent />
    </React.Suspense>
  );
}
