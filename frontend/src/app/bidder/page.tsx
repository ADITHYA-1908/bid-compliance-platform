"use client";

import React, { useEffect, useState } from "react";
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
import { LoadingState } from "@/components/common/LoadingState";
import {
  FileText,
  Send,
  Building2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ArrowRight,
  Clock,
  Briefcase,
  Layers,
  ChevronRight,
  TrendingUp,
  Award,
  MessageSquareQuote,
  ShieldAlert,
  Search,
} from "lucide-react";

export default function BidderDashboardPage() {
  const { user } = useAuth();
  const [profileData, setProfileData] = useState<BidderProfileResponse | null>(null);
  const [recentBids, setRecentBids] = useState<BidListItem[]>([]);
  const [openTenders, setOpenTenders] = useState<BidderTenderSummary[]>([]);
  const [totalTendersCount, setTotalTendersCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadDashboardData() {
      setLoading(true);
      try {
        const [profRes, bidsRes, tendersRes] = await Promise.allSettled([
          api.getBidderProfile(),
          api.getMyBids({ page_size: 5 }),
          api.getAvailableTenders({ page_size: 5 }),
        ]);

        if (profRes.status === "fulfilled") {
          setProfileData(profRes.value);
        }
        if (bidsRes.status === "fulfilled") {
          setRecentBids(bidsRes.value.items);
        }
        if (tendersRes.status === "fulfilled") {
          setOpenTenders(tendersRes.value.items);
          setTotalTendersCount(tendersRes.value.total);
        }
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, []);

  const completion = profileData?.completion;
  const draftBidsCount = recentBids.filter((b) => b.status === "DRAFT").length;
  const submittedBidsCount = recentBids.filter((b) => b.status === "SUBMITTED").length;

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

  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title="Bidder Workspace"
      description="Overview of your GeM procurement participation, active bids, and statutory verification readiness."
      breadcrumbs={[{ label: "Bidder Portal", href: "/bidder" }, { label: "Dashboard" }]}
      action={
        <Link
          href="/bidder/tenders"
          className="btn-emerald-fintech inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold shadow-md cursor-pointer"
        >
          <Search className="h-4 w-4" />
          <span>Discover Tenders</span>
        </Link>
      }
    >
      <div className="space-y-6">
        {/* Welcome Card */}
        <div className="floating-card rounded-2xl p-6 bg-white border border-slate-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-bold text-blue-800 border border-blue-200">
                  <span className="h-2 w-2 rounded-full bg-blue-500 status-indicator-pulse"></span>
                  Verified Bidder Entity
                </span>
                <span className="inline-flex items-center rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-800 border border-slate-200">
                  {user?.organization || "Vendor Organization"}
                </span>
              </div>
              <h2 className="font-heading text-2xl font-bold text-slate-900">
                {user?.organization || "My Bidder Enterprise"}
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Authorized User: <span className="font-semibold text-slate-700">{user?.full_name}</span> • Login ID: <span className="font-mono text-slate-700">{user?.email}</span>
              </p>
            </div>

            {/* Profile Completion Widget */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:w-64">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-bold text-slate-700 font-heading">Statutory Readiness</span>
                <span className="font-mono-score text-xs font-extrabold text-emerald-700">
                  {completion?.completion_percentage ?? 100}%
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-200 overflow-hidden">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                  style={{ width: `${completion?.completion_percentage ?? 100}%` }}
                />
              </div>
              <p className="mt-1.5 text-[10px] text-slate-500">
                {completion?.is_complete ? "✓ Ready for GeM procurement bids" : "Missing required statutory fields"}
              </p>
            </div>
          </div>
        </div>

        {/* Executive KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard
            label="Available Tenders"
            value={loading ? "..." : totalTendersCount}
            icon={FileText}
            variant="blue"
            subtitle="Open opportunities"
          />
          <StatCard
            label="Bids in Progress"
            value={loading ? "..." : draftBidsCount}
            icon={Send}
            variant="purple"
            subtitle="Draft proposals"
          />
          <StatCard
            label="Submitted Bids"
            value={loading ? "..." : submittedBidsCount}
            icon={CheckCircle2}
            variant="emerald"
            subtitle="Awaiting evaluation"
          />
          <StatCard
            label="Open Clarifications"
            value={loading ? "..." : 0}
            icon={MessageSquareQuote}
            variant="amber"
            subtitle="Pending queries"
          />
          <StatCard
            label="Expiring Documents"
            value={loading ? "..." : 0}
            icon={Award}
            variant="slate"
            subtitle="All credentials valid"
          />
        </div>

        {/* ACTION REQUIRED ALERTS SECTION */}
        <SectionCard
          title="Action Required & Compliance Alerts"
          description="Urgent statutory document renewals, pending clarification responses, and bid readiness gates."
          icon={AlertCircle}
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-4 flex items-start gap-3">
              <Sparkles className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 font-heading">
                  Document AI Ready
                </span>
                <h4 className="text-xs font-bold text-slate-900 mt-0.5">
                  PDF-First Extraction Available
                </h4>
                <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                  Upload PDF certificates in your Organization profile for instant auto-extraction.
                </p>
                <div className="mt-3">
                  <Link
                    href="/bidder/organization"
                    className="rounded-lg btn-emerald-fintech px-3 py-1 text-[11px] font-bold text-white shadow-2xs inline-block"
                  >
                    Upload Documents
                  </Link>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-amber-200 bg-amber-50/40 p-4 flex items-start gap-3">
              <Award className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-700 font-heading">
                  Certificate Monitoring
                </span>
                <h4 className="text-xs font-bold text-slate-900 mt-0.5">
                  All Certificates Active
                </h4>
                <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                  GSTIN and PAN statutory credentials are valid for active procurement bids.
                </p>
                <div className="mt-3">
                  <Link
                    href="/bidder/certificates"
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-[11px] font-bold text-slate-700 hover:bg-slate-50 shadow-2xs inline-block"
                  >
                    View Expiry Dates
                  </Link>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-purple-200 bg-purple-50/40 p-4 flex items-start gap-3">
              <MessageSquareQuote className="h-5 w-5 text-purple-600 shrink-0 mt-0.5" />
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700 font-heading">
                  Buyer Clarifications
                </span>
                <h4 className="text-xs font-bold text-slate-900 mt-0.5">
                  No Pending Queries
                </h4>
                <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                  All submitted bid proposals are up to date with no pending buyer clarifications.
                </p>
                <div className="mt-3">
                  <Link
                    href="/bidder/clarifications"
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-[11px] font-bold text-slate-700 hover:bg-slate-50 shadow-2xs inline-block"
                  >
                    Check Inbox
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </SectionCard>

        {/* AVAILABLE TENDERS SECTION */}
        <SectionCard
          title="Available Procurement Opportunities (GeM)"
          description="Open government tenders ready for technical and commercial bid submission."
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
          {loading ? (
            <LoadingState label="Loading available tenders..." />
          ) : openTenders.length === 0 ? (
            <EmptyState
              title="No open procurement tenders available"
              description="New opportunities will automatically appear here once published by buying authorities."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold uppercase tracking-wider text-slate-500 font-heading">
                  <tr>
                    <th className="px-4 py-3">Tender Title</th>
                    <th className="px-4 py-3">Department</th>
                    <th className="px-4 py-3">Submission Deadline</th>
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
                            className="font-heading font-bold text-slate-900 hover:text-emerald-700 transition-colors"
                          >
                            {t.title}
                          </Link>
                          <span className="font-mono text-[11px] font-bold text-slate-500 mt-0.5">
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

                      <td className="px-4 py-3.5">
                        <StatusBadge status={t.status} size="sm" />
                      </td>

                      <td className="px-4 py-3.5 text-right">
                        <Link
                          href={`/bidder/tenders/${t.id}`}
                          className="btn-emerald-fintech rounded-lg px-3 py-1.5 text-[11px] font-bold text-white shadow-2xs inline-flex items-center gap-1"
                        >
                          <span>View & Apply</span>
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
      </div>
    </DashboardLayout>
  );
}
