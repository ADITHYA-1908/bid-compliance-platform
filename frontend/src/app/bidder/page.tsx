"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import {
  api,
  BidderProfileResponse,
  BidListItem,
  BidderTenderSummary,
} from "@/lib/api";
import { StatCard } from "@/components/common/StatCard";
import { SectionCard } from "@/components/common/SectionCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState } from "@/components/common/EmptyState";
import {
  FileText,
  Send,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Search,
  RotateCcw,
  Clock,
  Building2,
  ShieldCheck,
  ShieldAlert,
  ArrowUpRight,
} from "lucide-react";

interface ActionItem {
  id: string;
  issue: string;
  related: string;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  actionLabel: string;
  actionHref: string;
}

export default function BidderDashboardPage() {
  const { user } = useAuth();
  const [profileData, setProfileData] = useState<BidderProfileResponse | null>(null);
  const [recentBids, setRecentBids] = useState<BidListItem[]>([]);
  const [openTenders, setOpenTenders] = useState<BidderTenderSummary[]>([]);
  const [totalTendersCount, setTotalTendersCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [profRes, bidsRes, tendersRes] = await Promise.allSettled([
        api.getBidderProfile(),
        api.getMyBids({ page_size: 5 }),
        api.getAvailableTenders({ page_size: 5 }),
      ]);

      let hasSuccess = false;

      if (profRes.status === "fulfilled") {
        setProfileData(profRes.value);
        hasSuccess = true;
      }
      if (bidsRes.status === "fulfilled") {
        setRecentBids(bidsRes.value?.items || []);
        hasSuccess = true;
      }
      if (tendersRes.status === "fulfilled") {
        setOpenTenders(tendersRes.value?.items || []);
        setTotalTendersCount(tendersRes.value?.total || 0);
        hasSuccess = true;
      }

      if (!hasSuccess) {
        setError("Unable to load bidder dashboard. Please check your connection.");
      }
    } catch {
      setError("Unable to load bidder dashboard data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const completion = profileData?.completion;
  const draftBids = recentBids.filter((b) => b.status === "DRAFT");
  const draftBidsCount = draftBids.length;
  const submittedBidsCount = recentBids.filter((b) => b.status === "SUBMITTED").length;

  // Build dynamic, high-utility Action Items
  const actionItems: ActionItem[] = [];

  // 1. Profile completeness check
  if (completion && !completion.is_complete) {
    const missingCount = completion.missing_required_fields?.length || 0;
    actionItems.push({
      id: "incomplete-profile",
      issue: `Incomplete Organization Profile (${missingCount} required field${missingCount > 1 ? "s" : ""} missing)`,
      related: "Statutory Organization Setup",
      priority: "HIGH",
      actionLabel: "Complete Profile",
      actionHref: "/bidder/organization",
    });
  }

  // 2. Draft bids requiring completion
  draftBids.forEach((bid) => {
    actionItems.push({
      id: `draft-bid-${bid.id}`,
      issue: "Draft Proposal Incomplete",
      related: `Bid #${bid.bid_number} • ${bid.tender_title || "Procurement Opportunity"}`,
      priority: "MEDIUM",
      actionLabel: "Continue Bid",
      actionHref: `/bidder/bids/${bid.id}`,
    });
  });

  // Safe Dynamic Profile Status computation
  const getDynamicProfileStatus = () => {
    if (!profileData || !completion) {
      return {
        label: "Verification Pending",
        classes: "bg-slate-100 text-slate-700 border-slate-200",
        icon: Clock,
      };
    }
    if (completion.is_complete && completion.completion_percentage === 100) {
      return {
        label: "Profile Verified",
        classes: "bg-emerald-50 text-emerald-800 border-emerald-200",
        icon: CheckCircle2,
      };
    }
    if (completion.completion_percentage > 0) {
      return {
        label: "Incomplete Profile",
        classes: "bg-amber-50 text-amber-800 border-amber-200",
        icon: AlertTriangle,
      };
    }
    return {
      label: "Verification Pending",
      classes: "bg-blue-50 text-blue-800 border-blue-200",
      icon: Clock,
    };
  };

  const dynamicStatus = getDynamicProfileStatus();
  const StatusIcon = dynamicStatus.icon;

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "—";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  const formatCurrency = (val?: number | string | null) => {
    if (val === null || val === undefined || val === "") return "—";
    const num = Number(val);
    if (isNaN(num)) return "—";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(num);
  };

  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title="Bidder Workspace"
      description="Manage tenders, bids, documents, and compliance readiness."
      breadcrumbs={[{ label: "Bidder Portal", href: "/bidder" }, { label: "Dashboard" }]}
      action={
        <Link
          href="/bidder/tenders"
          className="btn-emerald-fintech inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold shadow-2xs cursor-pointer transition-all"
        >
          <Search className="h-4 w-4" />
          <span>Browse Tenders</span>
        </Link>
      }
    >
      <div className="space-y-6">
        {/* Error State Banner */}
        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-800 flex items-center justify-between shadow-2xs">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
              <p className="text-xs font-semibold">{error}</p>
            </div>
            <button
              onClick={loadDashboardData}
              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-white px-3 py-1 text-xs font-bold text-rose-700 hover:bg-rose-100 transition-colors cursor-pointer"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Loading Skeleton */}
        {loading ? (
          <div className="space-y-6 animate-pulse">
            <div className="h-28 rounded-2xl bg-slate-200/70" />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="h-24 rounded-2xl bg-slate-200/70" />
              <div className="h-24 rounded-2xl bg-slate-200/70" />
              <div className="h-24 rounded-2xl bg-slate-200/70" />
              <div className="h-24 rounded-2xl bg-slate-200/70" />
            </div>
            <div className="h-44 rounded-2xl bg-slate-200/70" />
            <div className="h-64 rounded-2xl bg-slate-200/70" />
          </div>
        ) : (
          <>
            {/* 1. Organization Summary Card */}
            <div className="rounded-2xl p-6 bg-white border border-slate-200 shadow-2xs">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-bold border ${dynamicStatus.classes}`}
                    >
                      <StatusIcon className="h-3.5 w-3.5" />
                      {dynamicStatus.label}
                    </span>
                    <span className="inline-flex items-center rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 border border-slate-200">
                      Bidder Organization
                    </span>
                  </div>

                  <h2 className="font-heading text-xl sm:text-2xl font-bold text-slate-900">
                    {user?.organization || profileData?.profile?.organization?.name || "My Enterprise"}
                  </h2>

                  <p className="text-xs text-slate-500">
                    Authorized User: <span className="font-semibold text-slate-700">{user?.full_name || "User"}</span> • Login: <span className="font-mono text-slate-600">{user?.email}</span>
                  </p>
                </div>

                {/* Statutory Readiness Progress Widget */}
                <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 w-full lg:w-72 shrink-0">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-slate-700 font-heading">Statutory Readiness</span>
                    <span className="font-mono text-xs font-extrabold text-slate-900">
                      {completion ? `${completion.completion_percentage}%` : "Unavailable"}
                    </span>
                  </div>

                  {completion ? (
                    <>
                      <div className="h-2 w-full rounded-full bg-slate-200 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            completion.completion_percentage >= 80 ? "bg-emerald-600" : "bg-amber-500"
                          }`}
                          style={{ width: `${completion.completion_percentage}%` }}
                        />
                      </div>
                      <p className="mt-1.5 text-[11px] text-slate-500">
                        {completion.is_complete
                          ? "All required statutory credentials verified"
                          : `${completion.missing_required_fields?.length || 0} mandatory credential(s) pending`}
                      </p>
                    </>
                  ) : (
                    <p className="text-[11px] text-slate-500 italic">Readiness data unavailable</p>
                  )}
                </div>
              </div>
            </div>

            {/* 2. Executive KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                label="Available Tenders"
                value={totalTendersCount}
                icon={FileText}
                variant="blue"
                subtitle="Open opportunities"
              />
              <StatCard
                label="Bids in Progress"
                value={draftBidsCount}
                icon={Send}
                variant="purple"
                subtitle="Draft proposals"
              />
              <StatCard
                label="Submitted Bids"
                value={submittedBidsCount}
                icon={CheckCircle2}
                variant="emerald"
                subtitle="Under evaluation"
              />
              <StatCard
                label="Action Required"
                value={actionItems.length}
                icon={AlertCircle}
                variant={actionItems.length > 0 ? "amber" : "slate"}
                subtitle={actionItems.length > 0 ? "Items needing attention" : "All in order"}
              />
            </div>

            {/* 3. Action Required Section */}
            <SectionCard
              title="Action Required"
              description="High-priority statutory requirements, draft proposals, and items requiring bidder action."
              icon={AlertCircle}
            >
              {actionItems.length === 0 ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <CheckCircle2 className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-900">
                        All monitored credentials and submissions are currently in order.
                      </p>
                      <p className="text-[11px] text-slate-500">
                        No immediate compliance actions or pending clarifications required.
                      </p>
                    </div>
                  </div>
                  <Link
                    href="/bidder/tenders"
                    className="hidden sm:inline-flex items-center gap-1 text-xs font-bold text-emerald-700 hover:text-emerald-800 hover:underline"
                  >
                    <span>Browse Tenders</span>
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {actionItems.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-xl border border-slate-200 bg-white p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-slate-300 transition-colors shadow-2xs"
                    >
                      <div className="flex items-start gap-3">
                        <span
                          className={`mt-0.5 inline-flex items-center rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                            item.priority === "HIGH" || item.priority === "CRITICAL"
                              ? "bg-rose-50 text-rose-700 border border-rose-200"
                              : "bg-amber-50 text-amber-700 border border-amber-200"
                          }`}
                        >
                          {item.priority}
                        </span>
                        <div>
                          <p className="text-xs font-bold text-slate-900">{item.issue}</p>
                          <p className="text-[11px] text-slate-500">{item.related}</p>
                        </div>
                      </div>

                      <Link
                        href={item.actionHref}
                        className="self-end sm:self-center inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-100 hover:text-slate-900 transition-colors cursor-pointer"
                      >
                        <span>{item.actionLabel}</span>
                        <ArrowUpRight className="h-3 w-3 text-slate-500" />
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>

            {/* 4. Available Procurement Opportunities */}
            <SectionCard
              title="Available Procurement Opportunities"
              description="Recently published government tenders ready for technical and commercial bid participation."
              icon={FileText}
              action={
                <Link
                  href="/bidder/tenders"
                  className="text-xs font-bold text-emerald-700 hover:text-emerald-800 hover:underline inline-flex items-center gap-1"
                >
                  <span>View All Tenders ({totalTendersCount})</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
              }
            >
              {openTenders.length === 0 ? (
                <EmptyState
                  title="No open procurement tenders available"
                  description="New opportunities will automatically appear here once published by buying authorities."
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-600">
                    <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold uppercase tracking-wider text-slate-500 font-heading">
                      <tr>
                        <th className="px-4 py-3">Tender</th>
                        <th className="px-4 py-3">Department</th>
                        <th className="px-4 py-3">Submission Deadline</th>
                        <th className="px-4 py-3">Estimated Value</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {openTenders.map((t) => (
                        <tr key={t.id} className="hover:bg-slate-50/60 transition-colors">
                          <td className="px-4 py-3.5">
                            <div className="flex flex-col">
                              <Link
                                href={`/bidder/tenders/${t.id}`}
                                className="font-heading font-bold text-slate-900 hover:text-emerald-700 transition-colors line-clamp-1"
                              >
                                {t.title}
                              </Link>
                              <span className="font-mono text-[11px] text-slate-500 mt-0.5">
                                {t.tender_number}
                              </span>
                            </div>
                          </td>

                          <td className="px-4 py-3.5 font-medium text-slate-700">
                            {t.department || "Procuring Authority"}
                          </td>

                          <td className="px-4 py-3.5 font-mono text-slate-700">
                            {formatDate(t.submission_end_date)}
                          </td>

                          <td className="px-4 py-3.5 font-mono font-medium text-slate-800">
                            {formatCurrency(t.estimated_value)}
                          </td>

                          <td className="px-4 py-3.5">
                            <StatusBadge status={t.status} size="sm" />
                          </td>

                          <td className="px-4 py-3.5 text-right">
                            <Link
                              href={`/bidder/tenders/${t.id}`}
                              className="btn-emerald-fintech rounded-lg px-3 py-1.5 text-[11px] font-bold text-white shadow-2xs inline-flex items-center gap-1 transition-all"
                            >
                              <span>View Tender</span>
                              <ArrowRight className="h-3 w-3" />
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>

            {/* 5. My Active Bids (Bids in Progress) */}
            <SectionCard
              title="My Active Bids"
              description="Track your draft bid packages in preparation and active submitted proposals."
              icon={Send}
              action={
                recentBids.length > 0 ? (
                  <Link
                    href="/bidder/bids"
                    className="text-xs font-bold text-emerald-700 hover:text-emerald-800 hover:underline inline-flex items-center gap-1"
                  >
                    <span>View All Bids</span>
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                ) : undefined
              }
            >
              {recentBids.length === 0 ? (
                <EmptyState
                  title="No bids are currently in progress"
                  description="You have not created any draft proposals yet. Explore available tenders to start a new bid submission."
                  action={
                    <Link
                      href="/bidder/tenders"
                      className="btn-emerald-fintech rounded-lg px-3 py-1.5 text-xs font-bold text-white shadow-2xs inline-flex items-center gap-1.5 mt-2"
                    >
                      <Search className="h-3.5 w-3.5" />
                      <span>Browse Available Tenders</span>
                    </Link>
                  }
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-600">
                    <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold uppercase tracking-wider text-slate-500 font-heading">
                      <tr>
                        <th className="px-4 py-3">Bid Reference</th>
                        <th className="px-4 py-3">Tender Title</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">Last Updated</th>
                        <th className="px-4 py-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {recentBids.map((b) => (
                        <tr key={b.id} className="hover:bg-slate-50/60 transition-colors">
                          <td className="px-4 py-3.5 font-mono font-bold text-slate-900">
                            {b.bid_number}
                          </td>

                          <td className="px-4 py-3.5">
                            <div className="flex flex-col">
                              <span className="font-medium text-slate-800 line-clamp-1">
                                {b.tender_title || "Procurement Tender"}
                              </span>
                              <span className="font-mono text-[11px] text-slate-400">
                                {b.tender_number || "—"}
                              </span>
                            </div>
                          </td>

                          <td className="px-4 py-3.5">
                            <StatusBadge status={b.status} size="sm" />
                          </td>

                          <td className="px-4 py-3.5 font-mono text-slate-600">
                            {formatDate(b.updated_at || b.created_at)}
                          </td>

                          <td className="px-4 py-3.5 text-right">
                            <Link
                              href={`/bidder/bids/${b.id}`}
                              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-bold text-slate-700 hover:bg-slate-50 hover:text-slate-900 shadow-2xs inline-flex items-center gap-1 transition-colors"
                            >
                              <span>{b.status === "DRAFT" ? "Continue Bid" : "View Submission"}</span>
                              <ArrowRight className="h-3 w-3 text-slate-400" />
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
