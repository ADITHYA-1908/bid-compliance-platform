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
      description="Executive overview of your GeM procurement participation, statutory readiness, and proposal submissions."
      breadcrumbs={[{ label: "Bidder Portal", href: "/bidder" }, { label: "Dashboard" }]}
    >
      <div className="space-y-6">
        {/* Welcome & Account Summary Card */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 border border-emerald-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-600"></span>
                  Authenticated Bidder Session
                </span>
                <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-800 border border-blue-200">
                  GeM BIDDER
                </span>
              </div>
              <h2 className="text-xl font-bold text-slate-900">
                Welcome back, {user?.full_name}
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Organization:{" "}
                <span className="font-semibold text-slate-800">
                  {profileData?.profile.organization?.name || user?.organization || "Enterprise Vendor"}
                </span>{" "}
                • Email: <span className="font-mono text-slate-700">{user?.email}</span>
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              <Link
                href="/bidder/tenders"
                className="inline-flex items-center gap-1.5 rounded-md bg-blue-700 px-3.5 py-2 text-xs font-semibold text-white hover:bg-blue-800 transition-colors shadow-xs"
              >
                <Briefcase className="h-3.5 w-3.5" />
                Browse Tenders
              </Link>
              <Link
                href="/bidder/bids"
                className="inline-flex items-center gap-1.5 rounded-md bg-slate-100 px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200 transition-colors"
              >
                <Layers className="h-3.5 w-3.5" />
                My Proposals
              </Link>
              <Link
                href="/bidder/organization"
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-xs"
              >
                <Building2 className="h-3.5 w-3.5 text-slate-500" />
                Organization
              </Link>
            </div>
          </div>
        </div>

        {/* Profile Statutory Readiness Card */}
        {completion && (
          <div
            className={`rounded-xl border p-5 transition-all shadow-xs ${
              completion.is_complete
                ? "border-emerald-200 bg-emerald-50/50"
                : "border-blue-200 bg-blue-50/40"
            }`}
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-3.5">
                <div
                  className={`rounded-xl p-2.5 shrink-0 ${
                    completion.is_complete
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-blue-100 text-blue-800"
                  }`}
                >
                  {completion.is_complete ? (
                    <CheckCircle2 className="h-5 w-5" />
                  ) : (
                    <Sparkles className="h-5 w-5" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-slate-900">
                      Organization Profile & Statutory Readiness Gate
                    </h3>
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold border ${
                        completion.is_complete
                          ? "bg-emerald-100 text-emerald-800 border-emerald-300"
                          : "bg-amber-100 text-amber-800 border-amber-300"
                      }`}
                    >
                      {completion.completion_percentage}% Ready
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1">
                    {completion.is_complete
                      ? "Your statutory registration identifiers, GSTIN, PAN, and signatory credentials are 100% verified. You are eligible to submit bids for all open GeM tenders."
                      : `You have ${completion.missing_required_fields.length} mandatory registration item(s) pending (${completion.missing_required_fields.join(
                          ", "
                        )}) before your profile satisfies statutory submission requirements.`}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0 self-end md:self-center">
                {!completion.is_complete ? (
                  <Link
                    href="/bidder/organization"
                    className="inline-flex items-center gap-1.5 rounded-md bg-blue-700 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-800 transition-colors shadow-xs"
                  >
                    Complete Organization Profile
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700">
                    <CheckCircle2 className="h-4 w-4" />
                    Statutory Compliant
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Real Dynamic Metrics Grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Open GeM Tenders
              </span>
              <div className="rounded-lg bg-blue-50 p-2 text-blue-800 border border-blue-100">
                <Briefcase className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">
              {loading ? "..." : totalTendersCount}
            </p>
            <p className="mt-1 text-[11px] text-slate-500">
              Available for immediate participation
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Draft Workspaces
              </span>
              <div className="rounded-lg bg-amber-50 p-2 text-amber-700 border border-amber-100">
                <FileText className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">
              {loading ? "..." : draftBidsCount}
            </p>
            <p className="mt-1 text-[11px] text-slate-500">
              In-progress proposal workspaces
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Submitted Proposals
              </span>
              <div className="rounded-lg bg-emerald-50 p-2 text-emerald-700 border border-emerald-100">
                <Send className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">
              {loading ? "..." : submittedBidsCount}
            </p>
            <p className="mt-1 text-[11px] text-slate-500">
              Officially sealed and acknowledged
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Statutory Readiness
              </span>
              <div className="rounded-lg bg-purple-50 p-2 text-purple-700 border border-purple-100">
                <TrendingUp className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">
              {loading ? "..." : `${completion?.completion_percentage || 0}%`}
            </p>
            <p className="mt-1 text-[11px] text-slate-500">
              {completion?.is_complete ? "100% statutory compliant" : "Pending registration items"}
            </p>
          </div>
        </div>

        {/* Two-Column Grid: Recent Bids & Available Opportunities */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Bid Proposals */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-blue-700" />
                <h3 className="text-sm font-bold text-slate-900">
                  Recent Bid Proposals
                </h3>
              </div>
              <Link
                href="/bidder/bids"
                className="text-xs font-semibold text-blue-700 hover:text-blue-800 flex items-center gap-1"
              >
                View All
                <ChevronRight className="h-3 w-3" />
              </Link>
            </div>

            <div className="p-5">
              {loading ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  Loading recent proposals...
                </div>
              ) : recentBids.length === 0 ? (
                <div className="py-8 text-center">
                  <FileText className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-xs font-medium text-slate-700">No bid proposals yet</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Browse open tenders to initiate your first procurement proposal.
                  </p>
                  <Link
                    href="/bidder/tenders"
                    className="inline-flex items-center gap-1.5 mt-3 rounded-md bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800 transition-colors shadow-xs"
                  >
                    Discover Tenders
                  </Link>
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {recentBids.map((bid) => (
                    <div
                      key={bid.id}
                      className="py-3 first:pt-0 last:pb-0 flex items-center justify-between gap-4"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-slate-900">
                            {bid.bid_number}
                          </span>
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold border ${
                              bid.status === "SUBMITTED"
                                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                                : "bg-amber-50 text-amber-800 border-amber-200"
                            }`}
                          >
                            {bid.status}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 truncate mt-0.5 font-medium">
                          {bid.tender_title || "Tender Proposal"}
                        </p>
                        <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                          Quoted: {formatCurrency(bid.quoted_amount)}
                        </p>
                      </div>

                      <Link
                        href={`/bidder/bids/${bid.id}`}
                        className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-200 transition-colors shrink-0"
                      >
                        {bid.status === "SUBMITTED" ? "View Receipt" : "Edit Draft"}
                        <ChevronRight className="h-3 w-3" />
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Active Opportunities (Open GeM Tenders) */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div className="flex items-center gap-2">
                <Briefcase className="h-4 w-4 text-emerald-700" />
                <h3 className="text-sm font-bold text-slate-900">
                  Featured Open Tenders
                </h3>
              </div>
              <Link
                href="/bidder/tenders"
                className="text-xs font-semibold text-blue-700 hover:text-blue-800 flex items-center gap-1"
              >
                Browse All ({totalTendersCount})
                <ChevronRight className="h-3 w-3" />
              </Link>
            </div>

            <div className="p-5">
              {loading ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  Loading open tenders...
                </div>
              ) : openTenders.length === 0 ? (
                <div className="py-8 text-center">
                  <Briefcase className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-xs font-medium text-slate-700">No open tenders found</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Check back soon for newly published GeM procurement opportunities.
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {openTenders.map((t) => (
                    <div
                      key={t.id}
                      className="py-3 first:pt-0 last:pb-0 flex items-center justify-between gap-4"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-slate-900">
                            {t.tender_number}
                          </span>
                          <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700 border border-blue-100">
                            {t.category}
                          </span>
                        </div>
                        <p className="text-xs text-slate-700 truncate mt-0.5 font-medium">
                          {t.title}
                        </p>
                        <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-0.5">
                          <span className="font-mono text-slate-700 font-medium">
                            Est: {formatCurrency(t.estimated_value)}
                          </span>
                          <span className="flex items-center gap-1 text-slate-500">
                            <Clock className="h-3 w-3" />
                            Deadline: {formatDate(t.submission_end_date)}
                          </span>
                        </div>
                      </div>

                      <Link
                        href={`/bidder/tenders/${t.id}`}
                        className="inline-flex items-center gap-1 rounded-md bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-1.5 text-xs font-semibold hover:bg-blue-100 transition-colors shrink-0"
                      >
                        Participate
                        <ChevronRight className="h-3 w-3" />
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
