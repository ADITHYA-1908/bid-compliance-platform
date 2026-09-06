"use client";

import React, { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  MessageSquare,
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
  ShieldAlert,
  Send,
  Sparkles,
} from "lucide-react";
import {
  ClarificationPriority,
  ClarificationRequestListItemResponse,
  ClarificationStatus,
  ClarificationSummaryResponse,
} from "@/types/clarification";
import { bidderClarificationsApi } from "@/lib/api/clarifications";
import { ClarificationDetailDrawer } from "@/components/clarifications/ClarificationDetailDrawer";

const STATUS_CONFIG: Record<
  ClarificationStatus,
  { label: string; bg: string; text: string; border: string; icon: React.ElementType }
> = {
  DRAFT: { label: "Draft", bg: "bg-slate-100", text: "text-slate-700", border: "border-slate-200", icon: Clock },
  SENT: { label: "Action Required", bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200", icon: AlertTriangle },
  VIEWED: { label: "Action Required", bg: "bg-amber-50", text: "text-amber-800", border: "border-amber-200", icon: AlertTriangle },
  RESPONDED: { label: "Responded", bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200", icon: Clock },
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

export default function BidderClarificationsPage() {
  const [items, setItems] = useState<ClarificationRequestListItemResponse[]>([]);
  const [summary, setSummary] = useState<ClarificationSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusTab, setStatusTab] = useState<"ALL" | "ACTION_REQUIRED" | "RESPONDED" | "RESOLVED" | "OVERDUE">("ALL");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [selectedClarificationId, setSelectedClarificationId] = useState<string | null>(null);

  const fetchClarifications = async () => {
    setLoading(true);
    try {
      let statusParam: string | undefined = undefined;
      if (statusTab === "RESPONDED") statusParam = "RESPONDED";
      if (statusTab === "RESOLVED") statusParam = "RESOLVED";

      const [listRes, summaryRes] = await Promise.all([
        bidderClarificationsApi.listClarifications({
          status_filter: statusParam,
          priority_filter: priorityFilter || undefined,
          search: search || undefined,
          page_size: 50,
        }),
        bidderClarificationsApi.getSummary(),
      ]);

      let filteredItems = listRes.items;
      if (statusTab === "ACTION_REQUIRED") {
        filteredItems = filteredItems.filter((i) => i.status === "SENT" || i.status === "VIEWED");
      } else if (statusTab === "OVERDUE") {
        filteredItems = filteredItems.filter((i) => i.is_overdue);
      }

      setItems(filteredItems);
      setSummary(summaryRes);
    } catch (err) {
      console.error("Failed to load bidder clarifications:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClarifications();
  }, [statusTab, priorityFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchClarifications();
  };

  const getDueCountdown = (dueDateStr?: string | null, isOverdue?: boolean) => {
    if (!dueDateStr) return null;
    const due = new Date(dueDateStr);
    const now = new Date();
    const diffHours = Math.round((due.getTime() - now.getTime()) / (1000 * 60 * 60));

    if (diffHours < 0 || isOverdue) {
      const daysOverdue = Math.abs(Math.round(diffHours / 24));
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-bold text-rose-800 border border-rose-200">
          <AlertCircle className="h-3 w-3 text-rose-600" /> Overdue {daysOverdue > 0 ? `by ${daysOverdue}d` : "today"}
        </span>
      );
    }

    if (diffHours <= 24) {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-bold text-rose-700 border border-rose-200">
          <Clock className="h-3 w-3 text-rose-600" /> Due in {diffHours}h
        </span>
      );
    }

    const daysLeft = Math.round(diffHours / 24);
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-800 border border-amber-200">
        <Clock className="h-3 w-3 text-amber-600" /> {daysLeft} days left
      </span>
    );
  };

  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title="Buyer Clarifications & Queries"
      description="Respond to formal clarification requests and submit supplementary or replacement evidence to the evaluation committee."
      breadcrumbs={[
        { label: "Bidder", href: "/bidder" },
        { label: "Clarifications" },
      ]}
    >
      <div className="space-y-6">
        {/* KPI Cards Grid */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 block">Total Inquiries</span>
            <div className="text-2xl font-black text-slate-900 mt-1">{summary?.total ?? 0}</div>
            <span className="text-[11px] text-slate-400">All formal notices</span>
          </div>

          <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-4 shadow-xs">
            <span className="text-xs font-semibold text-rose-700 block">Action Required</span>
            <div className="text-2xl font-black text-rose-900 mt-1">
              {(summary?.sent ?? 0) + (summary?.viewed ?? 0)}
            </div>
            <span className="text-[11px] text-rose-600">Pending your reply</span>
          </div>

          <div className="rounded-2xl border border-rose-300 bg-rose-100/60 p-4 shadow-xs">
            <span className="text-xs font-semibold text-rose-800 block">Overdue Requests</span>
            <div className="text-2xl font-black text-rose-950 mt-1">{summary?.overdue ?? 0}</div>
            <span className="text-[11px] text-rose-700 font-medium">Passed due deadline</span>
          </div>

          <div className="rounded-2xl border border-blue-200 bg-blue-50/50 p-4 shadow-xs">
            <span className="text-xs font-semibold text-blue-700 block">Under Review</span>
            <div className="text-2xl font-black text-blue-900 mt-1">
              {(summary?.responded ?? 0) + (summary?.under_review ?? 0)}
            </div>
            <span className="text-[11px] text-blue-600">Officer evaluating reply</span>
          </div>

          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-4 shadow-xs">
            <span className="text-xs font-semibold text-emerald-700 block">Resolved / Closed</span>
            <div className="text-2xl font-black text-emerald-900 mt-1">
              {(summary?.resolved ?? 0) + (summary?.closed ?? 0)}
            </div>
            <span className="text-[11px] text-emerald-600">Findings concluded</span>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-xs">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 md:pb-0">
            {[
              { id: "ALL", label: "All" },
              { id: "ACTION_REQUIRED", label: "Action Required" },
              { id: "RESPONDED", label: "Responded / Review" },
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

          {/* Search and Priority filters */}
          <div className="flex items-center gap-2">
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
                placeholder="Search subject or tender..."
                className="w-48 sm:w-64 rounded-xl border border-slate-200 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-hidden"
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
            <h3 className="text-sm font-bold text-slate-900">No Clarification Requests</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              There are no clarification inquiries matching your current status filter.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {items.map((item) => {
              const statusInfo = STATUS_CONFIG[item.status] || STATUS_CONFIG.DRAFT;
              const priorityInfo = PRIORITY_CONFIG[item.priority] || PRIORITY_CONFIG.NORMAL;
              const isActionRequired = item.status === "SENT" || item.status === "VIEWED";

              return (
                <div
                  key={item.id}
                  onClick={() => setSelectedClarificationId(item.id)}
                  className={`group rounded-2xl border p-5 transition-all cursor-pointer bg-white hover:shadow-md ${
                    item.is_overdue
                      ? "border-rose-300 ring-1 ring-rose-300/50"
                      : isActionRequired
                      ? "border-indigo-200 ring-1 ring-indigo-200/50"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      {/* Top tags row */}
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
                        {getDueCountdown(item.due_date, item.is_overdue)}
                      </div>

                      {/* Subject */}
                      <h3 className="text-base font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                        {item.subject}
                      </h3>

                      {/* Tender & Context subtitle */}
                      <div className="flex flex-wrap items-center gap-y-1 gap-x-4 text-xs text-slate-500">
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
                        {item.related_document_name && (
                          <span className="inline-flex items-center gap-1 text-slate-700 bg-slate-100 px-2 py-0.5 rounded-md font-medium">
                            <FileText className="h-3 w-3" /> {item.related_document_name}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Right action button / chevron */}
                    <div className="flex items-center gap-3 shrink-0 pt-2 md:pt-0">
                      {item.responses_count > 0 && (
                        <span className="text-xs text-slate-500 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-xl">
                          {item.responses_count} {item.responses_count === 1 ? "Response" : "Responses"}
                        </span>
                      )}

                      <button className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 group-hover:bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-xs transition-colors">
                        {isActionRequired ? (
                          <>
                            <Send className="h-3.5 w-3.5" />
                            Submit Response
                          </>
                        ) : (
                          <>
                            <Eye className="h-3.5 w-3.5" />
                            View Thread
                          </>
                        )}
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
        userRole="BIDDER"
        onUpdate={fetchClarifications}
      />
    </DashboardLayout>
  );
}
