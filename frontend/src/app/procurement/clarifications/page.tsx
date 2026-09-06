"use client";

import React, { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  MessageSquare,
  MessageSquarePlus,
  Clock,
  AlertTriangle,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertCircle,
  FileText,
  Eye,
  Calendar,
  Layers,
  ArrowRight,
  TrendingUp,
  Sparkles,
  Send,
  Building2,
  PieChart,
} from "lucide-react";
import {
  ClarificationAnalyticsResponse,
  ClarificationPriority,
  ClarificationRequestListItemResponse,
  ClarificationStatus,
  ClarificationSummaryResponse,
} from "@/types/clarification";
import { procurementClarificationsApi } from "@/lib/api/clarifications";
import { ClarificationDetailDrawer } from "@/components/clarifications/ClarificationDetailDrawer";
import { CreateClarificationModal } from "@/components/clarifications/CreateClarificationModal";

const STATUS_CONFIG: Record<
  ClarificationStatus,
  { label: string; bg: string; text: string; border: string; icon: React.ElementType }
> = {
  DRAFT: { label: "Draft", bg: "bg-slate-100", text: "text-slate-700", border: "border-slate-200", icon: Clock },
  SENT: { label: "Awaiting Bidder", bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200", icon: Clock },
  VIEWED: { label: "Viewed by Bidder", bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-200", icon: Clock },
  RESPONDED: { label: "Responded (Action)", bg: "bg-amber-50", text: "text-amber-800", border: "border-amber-200", icon: AlertTriangle },
  UNDER_REVIEW: { label: "Under Review", bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200", icon: Clock },
  RESOLVED: { label: "Resolved", bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200", icon: CheckCircle2 },
  CLOSED: { label: "Closed", bg: "bg-slate-100", text: "text-slate-600", border: "border-slate-200", icon: Clock },
  EXPIRED: { label: "Expired", bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200", icon: XCircle },
  CANCELLED: { label: "Cancelled", bg: "bg-slate-100", text: "text-slate-500", border: "border-slate-200", icon: XCircle },
};

const PRIORITY_CONFIG: Record<
  ClarificationPriority,
  { label: string; bg: string }
> = {
  LOW: { label: "Low", bg: "bg-slate-100 text-slate-700 border-slate-200" },
  NORMAL: { label: "Normal", bg: "bg-blue-50 text-blue-700 border-blue-200" },
  HIGH: { label: "High", bg: "bg-amber-50 text-amber-800 border-amber-200" },
  URGENT: { label: "Urgent", bg: "bg-rose-50 text-rose-800 border-rose-200 font-bold" },
};

export default function ProcurementClarificationsPage() {
  const [items, setItems] = useState<ClarificationRequestListItemResponse[]>([]);
  const [summary, setSummary] = useState<ClarificationSummaryResponse | null>(null);
  const [analytics, setAnalytics] = useState<ClarificationAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusTab, setStatusTab] = useState<"ALL" | "DRAFT" | "AWAITING_BIDDER" | "RESPONDED" | "RESOLVED" | "OVERDUE">("ALL");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [selectedClarificationId, setSelectedClarificationId] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [showAnalyticsPanel, setShowAnalyticsPanel] = useState(false);

  const fetchClarifications = async () => {
    setLoading(true);
    try {
      let statusParam: string | undefined = undefined;
      if (statusTab === "DRAFT") statusParam = "DRAFT";
      if (statusTab === "RESPONDED") statusParam = "RESPONDED";
      if (statusTab === "RESOLVED") statusParam = "RESOLVED";

      const [listRes, summaryRes, analyticsRes] = await Promise.all([
        procurementClarificationsApi.listClarifications({
          status_filter: statusParam,
          priority_filter: priorityFilter || undefined,
          type_filter: typeFilter || undefined,
          search: search || undefined,
          page_size: 50,
        }),
        procurementClarificationsApi.getSummary(),
        procurementClarificationsApi.getAnalytics(),
      ]);

      let filteredItems = listRes.items;
      if (statusTab === "AWAITING_BIDDER") {
        filteredItems = filteredItems.filter((i) => i.status === "SENT" || i.status === "VIEWED");
      } else if (statusTab === "OVERDUE") {
        filteredItems = filteredItems.filter((i) => i.is_overdue);
      }

      setItems(filteredItems);
      setSummary(summaryRes);
      setAnalytics(analyticsRes);
    } catch (err) {
      console.error("Failed to load procurement clarifications:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClarifications();
  }, [statusTab, priorityFilter, typeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchClarifications();
  };

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Clarification Request Hub"
      description="Issue formal clarification notices, evaluate returned explanations, track response deadlines, and audit evidence."
      breadcrumbs={[
        { label: "Procurement", href: "/procurement" },
        { label: "Clarifications" },
      ]}
    >
      <div className="space-y-6">
        {/* Top Action & KPI Strip */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Evaluation Clarifications</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Auditable communication channel between evaluation committees and bidders.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowAnalyticsPanel(!showAnalyticsPanel)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-2xs transition-colors"
            >
              <PieChart className="h-4 w-4 text-slate-500" />
              {showAnalyticsPanel ? "Hide Analytics" : "View Analytics"}
            </button>

            <button
              onClick={() => setIsCreateOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:from-indigo-700 hover:to-blue-700 transition-all"
            >
              <MessageSquarePlus className="h-4 w-4" />
              New Clarification Request
            </button>
          </div>
        </div>

        {/* Analytics Telemetry Dropdown / Card */}
        {showAnalyticsPanel && analytics && (
          <div className="rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/50 via-white to-blue-50/50 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-indigo-100/60 pb-3">
              <div className="flex items-center gap-2 text-sm font-bold text-indigo-950">
                <TrendingUp className="h-4 w-4 text-indigo-600" /> Resolution & Efficiency Analytics
              </div>
              <span className="text-xs text-indigo-700/80">Part 13 & 16 Telemetry</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="rounded-xl bg-white border border-slate-200/80 p-3.5 shadow-2xs">
                <span className="text-xs text-slate-500 block">Avg Response Time</span>
                <div className="text-xl font-black text-slate-900 mt-1">
                  {analytics.avg_response_time_hours ? `${analytics.avg_response_time_hours}h` : "N/A"}
                </div>
                <span className="text-[10px] text-slate-400">Bidder turnaround</span>
              </div>

              <div className="rounded-xl bg-white border border-slate-200/80 p-3.5 shadow-2xs">
                <span className="text-xs text-slate-500 block">Avg Resolution Time</span>
                <div className="text-xl font-black text-slate-900 mt-1">
                  {analytics.avg_resolution_time_hours ? `${analytics.avg_resolution_time_hours}h` : "N/A"}
                </div>
                <span className="text-[10px] text-slate-400">Request to close</span>
              </div>

              <div className="rounded-xl bg-white border border-slate-200/80 p-3.5 shadow-2xs">
                <span className="text-xs text-slate-500 block">Total Inquiries</span>
                <div className="text-xl font-black text-indigo-600 mt-1">
                  {analytics.total_clarifications}
                </div>
                <span className="text-[10px] text-slate-400">Created across tenders</span>
              </div>

              <div className="rounded-xl bg-white border border-slate-200/80 p-3.5 shadow-2xs">
                <span className="text-xs text-slate-500 block">Resolution Rate</span>
                <div className="text-xl font-black text-emerald-600 mt-1">
                  {analytics.total_clarifications > 0
                    ? `${Math.round((analytics.resolved_clarifications / analytics.total_clarifications) * 100)}%`
                    : "100%"}
                </div>
                <span className="text-[10px] text-emerald-700">Concluded inquiries</span>
              </div>
            </div>
          </div>
        )}

        {/* KPI Cards Grid */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 block">Total Clarifications</span>
            <div className="text-2xl font-black text-slate-900 mt-1">{summary?.total ?? 0}</div>
            <span className="text-[11px] text-slate-400">Across tender submissions</span>
          </div>

          <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-4 shadow-xs">
            <span className="text-xs font-semibold text-amber-800 block">Pending Review</span>
            <div className="text-2xl font-black text-amber-950 mt-1">
              {(summary?.responded ?? 0) + (summary?.under_review ?? 0)}
            </div>
            <span className="text-[11px] text-amber-700">Bidder submitted reply</span>
          </div>

          <div className="rounded-2xl border border-blue-200 bg-blue-50/50 p-4 shadow-xs">
            <span className="text-xs font-semibold text-blue-700 block">Awaiting Bidder</span>
            <div className="text-2xl font-black text-blue-900 mt-1">
              {(summary?.sent ?? 0) + (summary?.viewed ?? 0)}
            </div>
            <span className="text-[11px] text-blue-600">Pending response</span>
          </div>

          <div className="rounded-2xl border border-rose-300 bg-rose-100/60 p-4 shadow-xs">
            <span className="text-xs font-semibold text-rose-800 block">Overdue Deadlines</span>
            <div className="text-2xl font-black text-rose-950 mt-1">{summary?.overdue ?? 0}</div>
            <span className="text-[11px] text-rose-700 font-medium">Surveillance alert</span>
          </div>

          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-4 shadow-xs">
            <span className="text-xs font-semibold text-emerald-700 block">Resolved</span>
            <div className="text-2xl font-black text-emerald-900 mt-1">{summary?.resolved ?? 0}</div>
            <span className="text-[11px] text-emerald-600">Findings concluded</span>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-xs">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 md:pb-0">
            {[
              { id: "ALL", label: "All" },
              { id: "DRAFT", label: "Drafts" },
              { id: "AWAITING_BIDDER", label: "Awaiting Bidder" },
              { id: "RESPONDED", label: "Pending Review" },
              { id: "RESOLVED", label: "Resolved" },
              { id: "OVERDUE", label: "Overdue" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatusTab(tab.id as any)}
                className={`rounded-xl px-3.5 py-1.5 text-xs font-bold transition-all whitespace-nowrap ${
                  statusTab === tab.id
                    ? "bg-slate-900 text-white shadow-xs"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
            >
              <option value="">All Categories</option>
              <option value="MISSING_DOCUMENT">Missing Document</option>
              <option value="UNCLEAR_DOCUMENT">Unclear Document</option>
              <option value="LOW_OCR_CONFIDENCE">Low OCR</option>
              <option value="VERIFICATION_MISMATCH">Verification Mismatch</option>
              <option value="COMPLIANCE_REVIEW">Compliance Review</option>
              <option value="DUPLICATE_REUSE_EXPLANATION">Duplicate Reuse</option>
              <option value="CERTIFICATE_VALIDITY">Certificate Validity</option>
            </select>

            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
            >
              <option value="">All Priorities</option>
              <option value="URGENT">Urgent</option>
              <option value="HIGH">High</option>
              <option value="NORMAL">Normal</option>
              <option value="LOW">Low</option>
            </select>

            <form onSubmit={handleSearchSubmit} className="relative">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search subject / bidder..."
                className="w-48 sm:w-56 rounded-xl border border-slate-200 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-hidden"
              />
              <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
            </form>
          </div>
        </div>

        {/* Requests List */}
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="h-8 w-8 animate-spin rounded-full border-3 border-indigo-600 border-t-transparent" />
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-12 text-center">
            <div className="mx-auto h-12 w-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
              <MessageSquare className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">No Clarifications Found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              No clarification requests match your current filters. Click &quot;New Clarification Request&quot; to issue a notice.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {items.map((item) => {
              const statusInfo = STATUS_CONFIG[item.status] || STATUS_CONFIG.DRAFT;
              const priorityInfo = PRIORITY_CONFIG[item.priority] || PRIORITY_CONFIG.NORMAL;
              const hasResponse = item.status === "RESPONDED" || item.status === "UNDER_REVIEW";

              return (
                <div
                  key={item.id}
                  onClick={() => setSelectedClarificationId(item.id)}
                  className={`group rounded-2xl border p-5 transition-all cursor-pointer bg-white hover:shadow-md ${
                    item.is_overdue
                      ? "border-rose-300 ring-1 ring-rose-300/50"
                      : hasResponse
                      ? "border-amber-300 ring-1 ring-amber-300/50"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      {/* Status / Priority tags */}
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-bold border ${statusInfo.bg} ${statusInfo.text} ${statusInfo.border}`}>
                          {statusInfo.icon && React.createElement(statusInfo.icon, { className: "h-3 w-3 shrink-0" })}
                          {statusInfo.label}
                        </span>
                        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${priorityInfo.bg}`}>
                          {priorityInfo.label}
                        </span>
                        <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-full">
                          {item.clarification_type.replace(/_/g, " ")}
                        </span>
                        {item.is_overdue && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-rose-600 px-2 py-0.5 text-[11px] font-bold text-white">
                            <Clock className="h-3 w-3" /> OVERDUE
                          </span>
                        )}
                      </div>

                      {/* Subject */}
                      <h3 className="text-base font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                        {item.subject}
                      </h3>

                      {/* Bidder & Tender Context */}
                      <div className="flex flex-wrap items-center gap-y-1 gap-x-4 text-xs text-slate-500">
                        <span>
                          Bidder: <strong className="text-slate-800">{item.bidder_organization_name}</strong>
                        </span>
                        <span>
                          Tender: <strong className="text-slate-700">{item.tender_title}</strong> ({item.tender_number})
                        </span>
                        <span>
                          Bid: <strong className="text-slate-700">{item.bid_number}</strong>
                        </span>
                        {item.related_requirement_code && (
                          <span className="inline-flex items-center gap-1 text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md font-semibold border border-indigo-200">
                            Rule [{item.related_requirement_code}]
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Right column */}
                    <div className="flex items-center gap-3 shrink-0 pt-2 md:pt-0">
                      {item.responses_count > 0 && (
                        <span className="text-xs font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-xl">
                          {item.responses_count} {item.responses_count === 1 ? "Response" : "Responses"}
                        </span>
                      )}

                      <button className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 group-hover:bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-xs transition-colors">
                        <Eye className="h-3.5 w-3.5" />
                        Inspect Thread
                        <ArrowRight className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Interactive Detail Drawer */}
      <ClarificationDetailDrawer
        isOpen={Boolean(selectedClarificationId)}
        onClose={() => setSelectedClarificationId(null)}
        clarificationId={selectedClarificationId}
        userRole="PROCUREMENT_OFFICER"
        onUpdate={fetchClarifications}
      />

      {/* Create Modal */}
      {isCreateOpen && (
        <CreateClarificationModal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          onSuccess={() => {
            fetchClarifications();
          }}
          tenderId=""
          bidId=""
          tenderTitle="Select during creation"
          bidNumber="N/A"
        />
      )}
    </DashboardLayout>
  );
}
