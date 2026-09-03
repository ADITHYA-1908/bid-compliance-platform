"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { getProcurementDashboardSummary } from "@/lib/api/procurement_dashboard";
import {
  ProcurementDashboardSummaryResponse,
  TenderEvaluationOverviewItem,
} from "@/types/procurement_dashboard";
import { StatCard } from "@/components/common/StatCard";
import { SectionCard } from "@/components/common/SectionCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { RiskBadge } from "@/components/common/RiskBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { LoadingState } from "@/components/common/LoadingState";
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
  PlusCircle,
  Eye,
  MessageSquareQuote,
  Award,
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
      (statusFilter === "EVALUATION" &&
        (t.status === "UNDER_EVALUATION" || t.status === "EVALUATION" || t.status === "CLOSED")) ||
      t.status.toUpperCase() === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Procurement Officer Command Center"
      description="Executive GeM tender oversight, statutory compliance matrices, and priority review queue."
      breadcrumbs={[{ label: "Procurement Portal", href: "/procurement" }, { label: "Dashboard" }]}
      action={
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadDashboard}
            disabled={loading}
            className="btn-navy-outline inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-semibold shadow-2xs cursor-pointer"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-emerald-600" : ""}`} />
            <span>Refresh</span>
          </button>
          <Link
            href="/procurement/tenders/new"
            className="btn-emerald-fintech inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold shadow-md cursor-pointer"
          >
            <PlusCircle className="h-4 w-4" />
            <span>+ Create New Tender</span>
          </Link>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Welcome Card */}
        <div className="floating-card rounded-2xl p-6 bg-white border border-slate-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-bold text-emerald-800 border border-emerald-200">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 status-indicator-pulse"></span>
                  Authenticated Officer
                </span>
                <span className="inline-flex items-center rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-800 border border-slate-200">
                  {user?.role || "PROCUREMENT_OFFICER"}
                </span>
              </div>
              <h2 className="font-heading text-2xl font-bold text-slate-900">
                Welcome back, {user?.full_name || "Procurement Officer"}
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Entity: <span className="font-semibold text-slate-700">{user?.organization || "Procuring Authority"}</span> • Official Email: <span className="font-mono text-slate-700">{user?.email}</span>
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/procurement/reviews"
                className="inline-flex items-center gap-1.5 rounded-xl bg-amber-50 border border-amber-200 px-4 py-2.5 text-xs font-bold text-amber-900 hover:bg-amber-100 transition-colors shadow-2xs"
              >
                <AlertCircle className="h-4 w-4 text-amber-600" />
                <span>Open Review Queue</span>
                {data?.counts.bids_requiring_review ? (
                  <span className="rounded-full bg-amber-600 px-1.5 py-0.2 text-[10px] font-mono font-extrabold text-white">
                    {data.counts.bids_requiring_review}
                  </span>
                ) : null}
              </Link>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
            <div className="flex-1 text-xs text-red-800">
              <p className="font-bold">Failed to load procurement dashboard metrics</p>
              <p className="mt-0.5">{error}</p>
            </div>
            <button
              onClick={loadDashboard}
              className="text-xs font-bold text-red-700 underline hover:text-red-900 cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* Executive KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard
            label="Total Tenders"
            value={loading ? "..." : (data?.tenders?.length ?? data?.counts.active_tenders ?? 0)}
            icon={FileText}
            variant="slate"
            subtitle="Department portfolio"
          />
          <StatCard
            label="Active Tenders"
            value={loading ? "..." : data?.counts.active_tenders ?? 0}
            icon={FileText}
            variant="emerald"
            subtitle={<span className="text-emerald-700 font-semibold">{data?.counts.open_tenders ?? 0} open for bids</span>}
          />
          <StatCard
            label="Total Bids"
            value={loading ? "..." : data?.counts.total_submitted_bids ?? 0}
            icon={Layers}
            variant="blue"
            subtitle="Received proposals"
          />
          <StatCard
            label="Review Required"
            value={loading ? "..." : data?.counts.bids_requiring_review ?? 0}
            icon={AlertCircle}
            variant="amber"
            subtitle="Pending human audit"
          />
          <StatCard
            label="Critical Risk"
            value={loading ? "..." : data?.counts.critical_risk_bids ?? 0}
            icon={ShieldAlert}
            variant="rose"
            subtitle="High risk findings"
          />
          <StatCard
            label="Open Clarifications"
            value={loading ? "..." : 2}
            icon={MessageSquareQuote}
            variant="purple"
            subtitle="Active buyer queries"
          />
        </div>

        {/* PRIORITY REVIEW QUEUE / ATTENTION CENTER SECTION */}
        <SectionCard
          title="Priority Review Queue & Attention Center"
          description="High-priority statutory mismatches, critical risk signals, and clarification responses requiring officer action."
          icon={ShieldAlert}
          badge={
            data?.counts.bids_requiring_review ? (
              <span className="rounded-full bg-amber-100 text-amber-900 border border-amber-300 px-2.5 py-0.5 text-[10px] font-bold">
                {data.counts.bids_requiring_review} Pending Items
              </span>
            ) : null
          }
          action={
            <Link
              href="/procurement/reviews"
              className="text-xs font-bold text-emerald-700 hover:text-emerald-800 hover:underline inline-flex items-center gap-1"
            >
              <span>View Full Queue</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          }
        >
          {loading ? (
            <LoadingState label="Loading review queue..." />
          ) : (
            <div className="space-y-3">
              {/* Example dynamic review signals */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="rounded-xl border border-red-200 bg-red-50/40 p-4 flex items-start gap-3">
                  <ShieldAlert className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-red-700 font-heading">
                      Critical Risk Alert
                    </span>
                    <h4 className="text-xs font-bold text-slate-900 mt-0.5">
                      Statutory Discrepancy & Threshold Deficit
                    </h4>
                    <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                      PAN legal entity name does not match GST registration certificate name.
                    </p>
                    <div className="mt-3 flex items-center gap-2">
                      <Link
                        href="/procurement/reviews"
                        className="rounded-lg bg-red-600 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-red-700 shadow-2xs"
                      >
                        Inspect Evidence
                      </Link>
                      <Link
                        href="/procurement/clarifications"
                        className="rounded-lg bg-white border border-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 shadow-2xs"
                      >
                        Request Clarification
                      </Link>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-amber-200 bg-amber-50/40 p-4 flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-amber-700 font-heading">
                      Document Quality Alert
                    </span>
                    <h4 className="text-xs font-bold text-slate-900 mt-0.5">
                      Low OCR Confidence (&lt; 65%)
                    </h4>
                    <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                      Audited turnover certificate page 3 is blurry or low resolution.
                    </p>
                    <div className="mt-3 flex items-center gap-2">
                      <Link
                        href="/procurement/reviews"
                        className="rounded-lg bg-amber-600 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-amber-700 shadow-2xs"
                      >
                        Review Document
                      </Link>
                      <Link
                        href="/procurement/clarifications"
                        className="rounded-lg bg-white border border-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 shadow-2xs"
                      >
                        Ask Re-upload
                      </Link>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-4 flex items-start gap-3">
                  <Award className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 font-heading">
                      Certificate Expiry Alert
                    </span>
                    <h4 className="text-xs font-bold text-slate-900 mt-0.5">
                      OEM Authorization Expiring Soon
                    </h4>
                    <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                      Validity expires within 18 days during the bid evaluation window.
                    </p>
                    <div className="mt-3 flex items-center gap-2">
                      <Link
                        href="/procurement/certificates"
                        className="rounded-lg bg-blue-600 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-blue-700 shadow-2xs"
                      >
                        Check Validity
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </SectionCard>

        {/* Tenders Under Evaluation Matrix Section */}
        <SectionCard
          title="Procurement Opportunities & Bidding Status"
          description="Track active tenders, total submitted proposals, and compliance evaluation progress."
          icon={FileText}
          action={
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter tenders..."
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  className="rounded-xl border border-slate-200 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:border-emerald-500 focus:outline-hidden"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-900 font-medium focus:border-emerald-500 focus:outline-hidden"
              >
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">Active Tenders</option>
                <option value="OPEN">Open for Bids</option>
                <option value="EVALUATION">Under Evaluation</option>
                <option value="CLOSED">Closed</option>
              </select>
            </div>
          }
        >
          {loading ? (
            <LoadingState label="Loading tenders..." />
          ) : filteredTenders.length === 0 ? (
            <EmptyState
              title="No tenders match the selected filters"
              description="Create a new procurement tender or adjust your search and status filters."
              action={
                <Link
                  href="/procurement/tenders/new"
                  className="btn-emerald-fintech inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-bold"
                >
                  <PlusCircle className="h-4 w-4" />
                  <span>Create Tender</span>
                </Link>
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold uppercase tracking-wider text-slate-500 font-heading">
                  <tr>
                    <th className="px-4 py-3">Tender Opportunity</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-center">Bids Received</th>
                    <th className="px-4 py-3 text-center">Evaluated</th>
                    <th className="px-4 py-3 text-center">Review Flags</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredTenders.map((tender) => (
                    <tr key={tender.tender_id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="flex flex-col">
                          <Link
                            href={`/procurement/tenders/${tender.tender_id}`}
                            className="font-heading font-bold text-slate-900 hover:text-emerald-700 transition-colors"
                          >
                            {tender.title}
                          </Link>
                          <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-500">
                            <span className="font-mono font-bold text-slate-700">{tender.tender_number}</span>
                            {tender.department && <span>• {tender.department}</span>}
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-3.5">
                        <StatusBadge status={tender.status} size="sm" />
                      </td>

                      <td className="px-4 py-3.5 text-center font-mono-score font-bold text-slate-900">
                        {tender.total_submitted_bids}
                      </td>

                      <td className="px-4 py-3.5 text-center">
                        <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 font-mono-score text-[11px] font-bold text-emerald-800 border border-emerald-200">
                          {tender.evaluated_bids}
                        </span>
                      </td>

                      <td className="px-4 py-3.5 text-center">
                        {tender.review_required_bids > 0 ? (
                          <span className="rounded-full bg-amber-50 px-2.5 py-0.5 font-mono-score text-[11px] font-bold text-amber-800 border border-amber-200">
                            {tender.review_required_bids}
                          </span>
                        ) : (
                          <span className="text-slate-400 font-mono">0</span>
                        )}
                      </td>

                      <td className="px-4 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Link
                            href={`/procurement/tenders/${tender.tender_id}`}
                            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-bold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs"
                          >
                            Tender Details
                          </Link>
                          <Link
                            href={`/procurement/tenders/${tender.tender_id}/evaluation`}
                            className="btn-emerald-fintech rounded-lg px-2.5 py-1 text-[11px] font-bold text-white shadow-2xs inline-flex items-center gap-1"
                          >
                            <span>Evaluate</span>
                            <ArrowRight className="h-3 w-3" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>
    </DashboardLayout>
  );
}
