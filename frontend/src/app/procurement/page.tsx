"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import {
  getProcurementDashboardSummary,
} from "@/lib/api/procurement_dashboard";
import {
  ProcurementDashboardSummaryResponse,
  TenderEvaluationOverviewItem,
} from "@/types/procurement_dashboard";
import {
  FileText,
  Building2,
  CheckCircle2,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  AlertTriangle,
  Layers,
  Activity,
  AlertCircle,
  Clock,
  Search,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  SlidersHorizontal,
} from "lucide-react";

export default function ProcurementDashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<ProcurementDashboardSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const summary = await getProcurementDashboardSummary();
      setData(summary);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err.message ||
          "Failed to load procurement dashboard summary."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const filteredTenders = (data?.tenders || []).filter((t: TenderEvaluationOverviewItem) => {
    const matchesSearch =
      !searchFilter.trim() ||
      t.tender_number.toLowerCase().includes(searchFilter.toLowerCase()) ||
      t.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
      (t.department && t.department.toLowerCase().includes(searchFilter.toLowerCase())) ||
      (t.category && t.category.toLowerCase().includes(searchFilter.toLowerCase()));

    const matchesStatus =
      statusFilter === "ALL" ||
      (statusFilter === "ACTIVE" && t.status !== "CLOSED" && t.status !== "ARCHIVED") ||
      (statusFilter === "EVALUATION" && (t.status === "UNDER_EVALUATION" || t.status === "EVALUATION" || t.status === "CLOSED")) ||
      t.status.toUpperCase() === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Procurement Officer Command Center"
      description="Real-time GeM tender monitoring, compliance evaluation matrices, and deterministic risk oversight."
      breadcrumbs={[{ label: "Procurement Portal", href: "/procurement" }, { label: "Dashboard" }]}
    >
      <div className="space-y-6">
        {/* Welcome & Department Card */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 border border-emerald-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-600 animate-pulse"></span>
                  Authenticated Officer
                </span>
                <span className="inline-flex items-center rounded-md bg-purple-50 px-2 py-0.5 text-xs font-semibold text-purple-800 border border-purple-200">
                  PROCUREMENT_OFFICER
                </span>
              </div>
              <h2 className="text-xl font-bold text-slate-900">
                Welcome back, {user?.full_name}
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Organization: <span className="font-semibold text-slate-700">{user?.organization || "Procuring Authority"}</span> • Official Email: <span className="font-mono text-slate-700">{user?.email}</span>
              </p>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-center">
              <button
                onClick={loadDashboard}
                disabled={loading}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors shadow-xs"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-purple-600" : ""}`} />
                Refresh
              </button>
              <Link
                href="/procurement/tenders/new"
                className="inline-flex items-center gap-1.5 rounded-md bg-purple-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-purple-800 transition-colors shadow-xs"
              >
                Publish New Tender
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
            <div className="flex-1 text-xs text-red-800">
              <p className="font-bold">Failed to load procurement dashboard metrics</p>
              <p className="mt-0.5">{error}</p>
            </div>
            <button
              onClick={loadDashboard}
              className="text-xs font-semibold text-red-700 underline hover:text-red-900"
            >
              Retry
            </button>
          </div>
        )}

        {/* Dynamic Summary Cards (Real Backend Data) */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {/* Card 1: Active Tenders */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-slate-300">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Active Tenders
              </span>
              <div className="rounded-lg bg-purple-50 p-2 text-purple-900">
                <FileText className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">
              {loading ? "..." : data?.counts.active_tenders ?? 0}
            </p>
            <div className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-500">
              <span className="font-semibold text-purple-700">{data?.counts.open_tenders ?? 0}</span> open for bids
            </div>
          </div>

          {/* Card 2: Submitted Bids */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-slate-300">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Submitted Bids
              </span>
              <div className="rounded-lg bg-blue-50 p-2 text-blue-900">
                <Layers className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">
              {loading ? "..." : data?.counts.total_submitted_bids ?? 0}
            </p>
            <p className="mt-1 text-[11px] text-slate-500">Across all active tenders</p>
          </div>

          {/* Card 3: Under Evaluation */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-slate-300">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Under Evaluation
              </span>
              <div className="rounded-lg bg-indigo-50 p-2 text-indigo-900">
                <Activity className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">
              {loading ? "..." : data?.counts.closed_under_evaluation ?? 0}
            </p>
            <div className="mt-1 flex items-center gap-1 text-[11px] text-slate-500">
              <span className="font-semibold text-indigo-700">{data?.counts.pending_evaluations ?? 0}</span> bids pending
            </div>
          </div>

          {/* Card 4: Review Required */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-slate-300">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Review Required
              </span>
              <div className="rounded-lg bg-amber-50 p-2 text-amber-700">
                <AlertCircle className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-amber-900">
              {loading ? "..." : data?.counts.bids_requiring_review ?? 0}
            </p>
            <p className="mt-1 text-[11px] text-amber-700 font-medium">Bids need human inspection</p>
          </div>

          {/* Card 5: Critical Findings */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-slate-300">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Critical Findings
              </span>
              <div className="rounded-lg bg-rose-50 p-2 text-rose-700">
                <ShieldAlert className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-rose-900">
              {loading ? "..." : data?.counts.critical_risk_bids ?? 0}
            </p>
            <p className="mt-1 text-[11px] text-rose-700 font-medium">Critical risk / defect bids</p>
          </div>

          {/* Card 6: Evaluation Completed */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-slate-300">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Completed
              </span>
              <div className="rounded-lg bg-emerald-50 p-2 text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-emerald-900">
              {loading ? "..." : data?.counts.evaluation_completed_bids ?? 0}
            </p>
            <p className="mt-1 text-[11px] text-emerald-700 font-medium">Deterministic evaluations</p>
          </div>
        </div>

        {/* Tenders Under Evaluation Matrix Section */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
          <div className="border-b border-slate-200 p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Activity className="h-4 w-4 text-purple-900" />
                  Tenders & Evaluation Progress Overview
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Monitor live bidder submission volumes, clause compliance progress, and critical risk flags.
                </p>
              </div>

              {/* Filters & Search */}
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
                  <input
                    type="text"
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    placeholder="Search tenders, numbers, depts..."
                    className="h-8.5 w-48 sm:w-64 rounded-md border border-slate-300 bg-white pl-8 pr-3 text-xs text-slate-800 placeholder-slate-400 focus:border-purple-600 focus:outline-hidden focus:ring-1 focus:ring-purple-600"
                  />
                </div>

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="h-8.5 rounded-md border border-slate-300 bg-white px-2.5 text-xs text-slate-700 focus:border-purple-600 focus:outline-hidden focus:ring-1 focus:ring-purple-600"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="ACTIVE">Active Tenders</option>
                  <option value="OPEN">Open for Bids</option>
                  <option value="EVALUATION">Under Evaluation</option>
                  <option value="CLOSED">Closed</option>
                </select>
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-600">
                  <th className="py-3.5 px-4">Tender Info</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-center">Submitted Bids</th>
                  <th className="py-3.5 px-4 min-w-[180px]">Evaluation Progress</th>
                  <th className="py-3.5 px-4 text-center">Review Req.</th>
                  <th className="py-3.5 px-4 text-center">Critical Risk</th>
                  <th className="py-3.5 px-4">Deadline</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-slate-400">
                      <RefreshCw className="h-6 w-6 animate-spin mx-auto text-purple-600 mb-2" />
                      <p className="text-xs font-medium text-slate-600">Loading tenders and evaluation summaries...</p>
                    </td>
                  </tr>
                ) : filteredTenders.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-slate-500">
                      <FileText className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                      <p className="text-sm font-semibold text-slate-700">No tenders found</p>
                      <p className="text-xs text-slate-400 mt-1">
                        {searchFilter
                          ? "No active tenders matched your search filters."
                          : "No tenders are currently available for evaluation."}
                      </p>
                    </td>
                  </tr>
                ) : (
                  filteredTenders.map((tender: TenderEvaluationOverviewItem) => {
                    const isFullyEvaluated =
                      tender.total_submitted_bids > 0 &&
                      tender.evaluated_bids === tender.total_submitted_bids;

                    return (
                      <tr
                        key={tender.tender_id}
                        className="hover:bg-slate-50/80 transition-colors group"
                      >
                        {/* Tender Info */}
                        <td className="py-3.5 px-4">
                          <Link
                            href={`/procurement/tenders/${tender.tender_id}/evaluation`}
                            className="font-bold text-slate-900 hover:text-purple-900 transition-colors flex items-center gap-1.5"
                          >
                            <span>{tender.title}</span>
                          </Link>
                          <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                            <span className="font-mono font-medium text-purple-900 bg-purple-50 px-1.5 py-0.2 rounded border border-purple-100">
                              {tender.tender_number}
                            </span>
                            {tender.category && (
                              <span>• {tender.category}</span>
                            )}
                            {tender.department && (
                              <span className="hidden md:inline">• {tender.department}</span>
                            )}
                          </div>
                        </td>

                        {/* Status */}
                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                              tender.status === "OPEN"
                                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                                : tender.status === "UNDER_EVALUATION" || tender.status === "EVALUATION"
                                ? "bg-indigo-50 text-indigo-800 border-indigo-200"
                                : tender.status === "CLOSED"
                                ? "bg-slate-100 text-slate-700 border-slate-300"
                                : "bg-amber-50 text-amber-800 border-amber-200"
                            }`}
                          >
                            {tender.status}
                          </span>
                        </td>

                        {/* Submitted Bids */}
                        <td className="py-3.5 px-4 text-center">
                          <span className="inline-flex items-center justify-center font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded text-xs">
                            {tender.total_submitted_bids}
                          </span>
                        </td>

                        {/* Progress Bar */}
                        <td className="py-3.5 px-4">
                          <div className="space-y-1">
                            <div className="flex items-center justify-between text-[11px]">
                              <span className="font-medium text-slate-700">
                                <span className="font-bold text-purple-900">{tender.evaluated_bids}</span> / {tender.total_submitted_bids} Evaluated
                              </span>
                              <span className="font-mono text-slate-500 font-semibold">
                                {tender.evaluation_progress_percentage}%
                              </span>
                            </div>
                            <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden border border-slate-200">
                              <div
                                className={`h-full rounded-full transition-all duration-300 ${
                                  isFullyEvaluated
                                    ? "bg-emerald-600"
                                    : tender.evaluation_progress_percentage > 0
                                    ? "bg-purple-700"
                                    : "bg-slate-300"
                                }`}
                                style={{ width: `${Math.min(100, Math.max(0, tender.evaluation_progress_percentage))}%` }}
                              />
                            </div>
                          </div>
                        </td>

                        {/* Review Required */}
                        <td className="py-3.5 px-4 text-center">
                          {tender.review_required_bids > 0 ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-800 border border-amber-200">
                              <AlertCircle className="h-3 w-3 text-amber-600" />
                              {tender.review_required_bids}
                            </span>
                          ) : (
                            <span className="text-slate-400 text-[11px]">0</span>
                          )}
                        </td>

                        {/* Critical Risk */}
                        <td className="py-3.5 px-4 text-center">
                          {tender.critical_risk_bids > 0 ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-bold text-rose-800 border border-rose-200">
                              <ShieldAlert className="h-3 w-3 text-rose-600" />
                              {tender.critical_risk_bids}
                            </span>
                          ) : (
                            <span className="text-slate-400 text-[11px]">0</span>
                          )}
                        </td>

                        {/* Deadline */}
                        <td className="py-3.5 px-4 text-slate-600 whitespace-nowrap">
                          {tender.submission_end_date ? (
                            <div className="flex items-center gap-1 text-[11px]">
                              <Clock className="h-3 w-3 text-slate-400" />
                              {new Date(tender.submission_end_date).toLocaleDateString()}
                            </div>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Link
                              href={`/procurement/tenders/${tender.tender_id}/evaluation`}
                              className="inline-flex items-center gap-1 rounded-md bg-purple-900 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-purple-800 transition-colors shadow-xs"
                            >
                              Evaluate Bids
                              <ChevronRight className="h-3 w-3" />
                            </Link>
                            <Link
                              href={`/procurement/tenders/${tender.tender_id}`}
                              className="inline-flex items-center p-1 text-slate-400 hover:text-slate-600 rounded hover:bg-slate-100 transition-colors"
                              title="View Tender Details"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Advisory Operational Notice */}
        <div className="rounded-xl border border-purple-200 bg-purple-50/40 p-5">
          <div className="flex items-start gap-3">
            <ShieldCheck className="h-5 w-5 text-purple-900 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-700 space-y-1">
              <p className="font-bold text-purple-900">
                Enterprise Procurement Evaluation Policy & System Boundaries
              </p>
              <p>
                Compliance results, category scores, base risks, and override adjustments are calculated deterministically from authoritative evidence.
                AI recommendations are non-binding and purely advisory. Final bid qualification, disqualification, and tender awards remain strictly reserved for the authorized Procurement Officer.
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
