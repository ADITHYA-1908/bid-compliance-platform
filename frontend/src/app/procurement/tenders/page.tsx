"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { TenderTable } from "@/components/tenders/TenderTable";
import { TenderFilters } from "@/components/tenders/TenderFilters";
import { ConfirmArchiveModal } from "@/components/tenders/ConfirmArchiveModal";
import { api, Tender, ApiError } from "@/lib/api";
import { PlusCircle, FileText, CheckCircle2, Clock, Archive } from "lucide-react";

export default function ProcurementTendersPage() {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Archive modal state
  const [selectedTenderForArchive, setSelectedTenderForArchive] = useState<Tender | null>(null);
  const [isArchiving, setIsArchiving] = useState(false);

  // Notification message
  const [feedbackMessage, setFeedbackMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const loadTenders = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getTenders({
        page,
        page_size: pageSize,
        search: search || undefined,
        status: statusFilter || undefined,
        include_archived: includeArchived,
      });
      setTenders(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err: any) {
      setError(
        err?.message || "Unable to connect to the BidVerify API. Please ensure the backend server is running."
      );
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, search, statusFilter, includeArchived]);

  useEffect(() => {
    loadTenders();
  }, [loadTenders]);

  const handleConfirmArchive = async () => {
    if (!selectedTenderForArchive) return;
    setIsArchiving(true);
    try {
      await api.archiveTender(selectedTenderForArchive.id);
      setFeedbackMessage({
        type: "success",
        text: `Tender ${selectedTenderForArchive.tender_number} has been archived successfully.`,
      });
      setSelectedTenderForArchive(null);
      await loadTenders();
    } catch (err: any) {
      setFeedbackMessage({
        type: "error",
        text: err?.message || "Failed to archive tender.",
      });
    } finally {
      setIsArchiving(false);
    }
  };

  const handleResetFilters = () => {
    setSearch("");
    setStatusFilter("");
    setIncludeArchived(false);
    setPage(1);
  };

  // Calculate real metrics from current result set
  const draftCount = tenders.filter((t) => t.status === "DRAFT" && t.is_active).length;
  const openCount = tenders.filter((t) => t.status === "OPEN" && t.is_active).length;
  const archivedCount = tenders.filter((t) => !t.is_active || t.status === "ARCHIVED").length;

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER"]}
      title="Tender Management"
      description="Create, monitor, and manage procurement tenders for your department."
      breadcrumbs={[
        { label: "Procurement Portal", href: "/procurement" },
        { label: "Tenders" },
      ]}
      action={
        <Link
          href="/procurement/tenders/new"
          className="btn-emerald-fintech inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-xs font-bold shadow-md cursor-pointer"
        >
          <PlusCircle className="h-4 w-4" />
          <span>+ Create New Tender</span>
        </Link>
      }
    >
      <div className="space-y-6">
        {/* Feedback Alert */}
        {feedbackMessage && (
          <div
            className={`rounded-xl border p-4 text-xs font-medium flex items-center justify-between ${
              feedbackMessage.type === "success"
                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                : "bg-red-50 text-red-800 border-red-200"
            }`}
          >
            <span>{feedbackMessage.text}</span>
            <button
              onClick={() => setFeedbackMessage(null)}
              className="text-slate-500 hover:text-slate-700 font-bold ml-4 cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}

        {/* Telemetry Summary Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Total Listed
              </span>
              <div className="rounded-lg bg-purple-50 p-2 text-purple-900">
                <FileText className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">{total}</p>
            <p className="mt-1 text-[11px] text-slate-500">Departmental procurement opportunities</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Drafts
              </span>
              <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
                <Clock className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">{draftCount}</p>
            <p className="mt-1 text-[11px] text-slate-500">Awaiting requirement setup</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Open for Bidding
              </span>
              <div className="rounded-lg bg-emerald-50 p-2 text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">{openCount}</p>
            <p className="mt-1 text-[11px] text-slate-500">Active submission window</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Archived
              </span>
              <div className="rounded-lg bg-rose-50 p-2 text-rose-700">
                <Archive className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">{archivedCount}</p>
            <p className="mt-1 text-[11px] text-slate-500">Soft-deleted procurement records</p>
          </div>
        </div>

        {/* Filter Controls */}
        <TenderFilters
          search={search}
          status={statusFilter}
          includeArchived={includeArchived}
          onSearchChange={(s) => {
            setSearch(s);
            setPage(1);
          }}
          onStatusChange={(st) => {
            setStatusFilter(st);
            setPage(1);
          }}
          onIncludeArchivedChange={(inc) => {
            setIncludeArchived(inc);
            setPage(1);
          }}
          onReset={handleResetFilters}
        />

        {/* Tender Table */}
        <TenderTable
          tenders={tenders}
          page={page}
          pageSize={pageSize}
          total={total}
          totalPages={totalPages}
          isLoading={isLoading}
          error={error}
          onPageChange={setPage}
          onArchiveClick={(tender) => setSelectedTenderForArchive(tender)}
          onRetry={loadTenders}
        />
      </div>

      {/* Confirmation Dialog */}
      <ConfirmArchiveModal
        isOpen={Boolean(selectedTenderForArchive)}
        tenderNumber={selectedTenderForArchive?.tender_number || ""}
        tenderTitle={selectedTenderForArchive?.title || ""}
        isSubmitting={isArchiving}
        onConfirm={handleConfirmArchive}
        onClose={() => setSelectedTenderForArchive(null)}
      />
    </DashboardLayout>
  );
}
