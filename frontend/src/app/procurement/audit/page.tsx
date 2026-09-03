"use client";

import React, { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  AuditEventItem,
  AuditFilterParams,
  AuditKPIs,
} from "@/types/audit";
import { getAuditEvents } from "@/lib/api/audit";
import {
  ShieldCheck,
  History,
  Search,
  Filter,
  Calendar,
  Layers,
  User,
  Bot,
  Cpu,
  Eye,
  X,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  FileText,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  Info,
  Copy,
  Check,
} from "lucide-react";

export default function ProcurementAuditPage() {
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [kpis, setKpis] = useState<AuditKPIs>({
    total_events: 0,
    events_today: 0,
    decisions_recorded: 0,
    reviews_resolved: 0,
    ai_events: 0,
    system_events: 0,
  });
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState<string>("");
  const [eventTypeFilter, setEventTypeFilter] = useState<string>("");
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>("");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");

  // Selected event modal
  const [selectedEvent, setSelectedEvent] = useState<AuditEventItem | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const fetchEvents = async (pageNumber: number = page) => {
    setLoading(true);
    setError(null);
    try {
      const params: AuditFilterParams = {
        page: pageNumber,
        page_size: 15,
        search: search.trim() || undefined,
        event_type: eventTypeFilter || undefined,
        entity_type: entityTypeFilter || undefined,
        date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
        date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
      };

      const res = await getAuditEvents(params);
      setEvents(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
      setPage(res.page);
      setKpis(res.kpis);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Failed to load audit events.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents(1);
  }, [eventTypeFilter, entityTypeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchEvents(1);
  };

  const handleResetFilters = () => {
    setSearch("");
    setEventTypeFilter("");
    setEntityTypeFilter("");
    setDateFrom("");
    setDateTo("");
    setTimeout(() => fetchEvents(1), 0);
  };

  const copyMetadata = () => {
    if (selectedEvent) {
      navigator.clipboard.writeText(JSON.stringify(selectedEvent.metadata, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getActorBadge = (actor: AuditEventItem["actor"]) => {
    if (actor.source === "AI_SERVICE") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
          <Bot className="w-3 h-3 text-purple-600" />
          AI Service
        </span>
      );
    }
    if (actor.source === "SYSTEM") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
          <Cpu className="w-3 h-3 text-slate-500" />
          System
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-800 border border-blue-200">
        <User className="w-3 h-3 text-blue-600" />
        {actor.name || "Procurement Officer"}
      </span>
    );
  };

  const getEventTypeBadge = (eventType: string, label: string) => {
    const humanLabel =
      label && label !== eventType
        ? label
        : eventType
            .replace(/_/g, " ")
            .toLowerCase()
            .replace(/\b\w/g, (c) => c.toUpperCase());

    if (eventType.includes("DECISION")) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
          {humanLabel}
        </span>
      );
    }
    if (eventType.includes("REVIEW")) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200">
          {humanLabel}
        </span>
      );
    }
    if (eventType.includes("SHORTLIST")) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold bg-indigo-50 text-indigo-800 border border-indigo-200">
          {humanLabel}
        </span>
      );
    }
    if (eventType.includes("AI_")) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold bg-purple-50 text-purple-800 border border-purple-200">
          {humanLabel}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
        {humanLabel}
      </span>
    );
  };

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Audit Trail & Decision History"
      description="Tamper-resistant, immutable log of all procurement decisions, human reviews, AI syntheses, and lifecycle events."
      breadcrumbs={[
        { label: "Procurement", href: "/procurement" },
        { label: "Audit Trail" },
      ]}
      action={
        <button
          onClick={() => fetchEvents(page)}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg shadow-xs hover:bg-slate-50 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Log
        </button>
      }
    >
      <div className="space-y-6">
        {/* KPI Cards Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center gap-2 text-slate-500 mb-1">
              <History className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-semibold uppercase tracking-wider">Total Events</span>
            </div>
            <p className="text-2xl font-bold text-slate-900">{kpis.total_events.toLocaleString()}</p>
            <span className="text-[11px] text-slate-400">All lifecycle actions</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center gap-2 text-slate-500 mb-1">
              <Clock className="w-4 h-4 text-indigo-600" />
              <span className="text-xs font-semibold uppercase tracking-wider">Events Today</span>
            </div>
            <p className="text-2xl font-bold text-indigo-700">{kpis.events_today}</p>
            <span className="text-[11px] text-slate-400">Logged since 00:00 UTC</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center gap-2 text-slate-500 mb-1">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span className="text-xs font-semibold uppercase tracking-wider">Decisions</span>
            </div>
            <p className="text-2xl font-bold text-emerald-700">{kpis.decisions_recorded}</p>
            <span className="text-[11px] text-slate-400">Human determinations</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center gap-2 text-slate-500 mb-1">
              <ShieldCheck className="w-4 h-4 text-amber-600" />
              <span className="text-xs font-semibold uppercase tracking-wider">Reviews</span>
            </div>
            <p className="text-2xl font-bold text-amber-700">{kpis.reviews_resolved}</p>
            <span className="text-[11px] text-slate-400">Resolutions recorded</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center gap-2 text-slate-500 mb-1">
              <Bot className="w-4 h-4 text-purple-600" />
              <span className="text-xs font-semibold uppercase tracking-wider">AI Operations</span>
            </div>
            <p className="text-2xl font-bold text-purple-700">{kpis.ai_events}</p>
            <span className="text-[11px] text-slate-400">Advisory recommendations</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center gap-2 text-slate-500 mb-1">
              <Cpu className="w-4 h-4 text-slate-600" />
              <span className="text-xs font-semibold uppercase tracking-wider">System Rules</span>
            </div>
            <p className="text-2xl font-bold text-slate-700">{kpis.system_events}</p>
            <span className="text-[11px] text-slate-400">Deterministic engines</span>
          </div>
        </div>

        {/* Filter & Search Panel */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {/* Search Input */}
            <div className="md:col-span-2 relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search tender #, bid #, bidder, actor, summary..."
                className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white transition-colors"
              />
            </div>

            {/* Event Type Filter */}
            <div>
              <select
                value={eventTypeFilter}
                onChange={(e) => setEventTypeFilter(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors"
              >
                <option value="">All Event Types</option>
                <option value="BID_DECISION_CREATED">Final Decision Recorded</option>
                <option value="BID_DECISION_SUPERSEDED">Decision Superseded</option>
                <option value="BID_DECISION_STALE">Decision Flagged Stale</option>
                <option value="HUMAN_REVIEW_RESOLVED">Human Review Resolved</option>
                <option value="HUMAN_REVIEW_NOTE_ADDED">Review Note Added</option>
                <option value="BID_SHORTLISTED">Bid Shortlisted</option>
                <option value="BID_REMOVED_FROM_SHORTLIST">Removed from Shortlist</option>
                <option value="AI_RECOMMENDATION_GENERATED">AI Recommendation</option>
                <option value="COMPLIANCE_EVALUATED">Compliance Evaluated</option>
                <option value="SCORE_CALCULATED">Score Calculated</option>
                <option value="RISK_CALCULATED">Risk Calculated</option>
                <option value="BID_SUBMITTED">Bid Submitted</option>
                <option value="TENDER_CREATED">Tender Created</option>
              </select>
            </div>

            {/* Entity Type Filter */}
            <div>
              <select
                value={entityTypeFilter}
                onChange={(e) => setEntityTypeFilter(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors"
              >
                <option value="">All Entities</option>
                <option value="BID_DECISION">Bid Decision</option>
                <option value="HUMAN_REVIEW">Human Review</option>
                <option value="BID_SHORTLIST">Shortlist</option>
                <option value="AI_RECOMMENDATION">AI Recommendation</option>
                <option value="COMPLIANCE_RESULT">Compliance Result</option>
                <option value="SCORE_SNAPSHOT">Score Snapshot</option>
                <option value="RISK_SNAPSHOT">Risk Snapshot</option>
                <option value="BID">Bid Submission</option>
                <option value="TENDER">Tender</option>
              </select>
            </div>

            {/* Date From */}
            <div>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                placeholder="From Date"
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors"
              />
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                type="submit"
                className="flex-1 px-3.5 py-2 text-xs font-semibold text-white bg-blue-900 rounded-lg hover:bg-blue-800 transition-colors shadow-xs"
              >
                Filter
              </button>
              <button
                type="button"
                onClick={handleResetFilters}
                className="px-3 py-2 text-xs font-semibold text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
              >
                Reset
              </button>
            </div>
          </form>
        </div>

        {/* Audit Events Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          {error && (
            <div className="p-4 bg-red-50 border-b border-red-200 flex items-center gap-2 text-red-800 text-xs">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {loading ? (
            <div className="p-12 text-center text-slate-400 space-y-3">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-900" />
              <p className="text-xs font-semibold">Loading append-only audit trail...</p>
            </div>
          ) : events.length === 0 ? (
            <div className="p-12 text-center text-slate-500 space-y-2">
              <History className="w-10 h-10 mx-auto text-slate-300" />
              <p className="text-sm font-bold text-slate-700">No Audit Events Found</p>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                No historical actions match your search or filter parameters.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-slate-50/75 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px] tracking-wider">
                    <th className="py-3 px-4">Timestamp (UTC)</th>
                    <th className="py-3 px-4">Event Type</th>
                    <th className="py-3 px-4">Tender / Bid</th>
                    <th className="py-3 px-4">Actor</th>
                    <th className="py-3 px-4">Action & Summary</th>
                    <th className="py-3 px-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {events.map((e) => (
                    <tr
                      key={e.id}
                      onClick={() => setSelectedEvent(e)}
                      className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                    >
                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-500 font-mono text-[11px]">
                        {new Date(e.created_at).toLocaleString("en-US", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                          hour12: false,
                        })}
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {getEventTypeBadge(e.event_type, e.event_label)}
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex flex-col">
                          {e.tender_number ? (
                            <span className="font-semibold text-slate-800">{e.tender_number}</span>
                          ) : (
                            <span className="text-slate-400">Org Level</span>
                          )}
                          {e.bid_number && (
                            <span className="text-[11px] text-slate-500">
                              Bid: {e.bid_number} ({e.bidder_name || "Bidder"})
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {getActorBadge(e.actor)}
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="flex flex-col">
                          <span className="font-medium text-slate-800">{e.summary}</span>
                          <span className="text-[11px] text-slate-400">
                            Entity: {e.entity_type} ({e.action})
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <button
                          type="button"
                          onClick={(ev) => {
                            ev.stopPropagation();
                            setSelectedEvent(e);
                          }}
                          className="p-1.5 text-slate-400 hover:text-blue-900 hover:bg-blue-50 rounded-md transition-colors"
                          title="View metadata payload"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Footer */}
          {!loading && events.length > 0 && (
            <div className="px-5 py-3.5 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs">
              <span className="text-slate-500">
                Showing <strong className="text-slate-800">{(page - 1) * 15 + 1}</strong> to{" "}
                <strong className="text-slate-800">{Math.min(page * 15, total)}</strong> of{" "}
                <strong className="text-slate-800">{total}</strong> events
              </span>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => fetchEvents(page - 1)}
                  className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-2 font-semibold text-slate-700">
                  Page {page} of {totalPages}
                </span>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => fetchEvents(page + 1)}
                  className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Selected Event Detail Modal */}
        {selectedEvent && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in-0 zoom-in-95">
              {/* Modal Header */}
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg text-blue-900">
                    <History className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">{selectedEvent.event_label}</h3>
                    <p className="text-[11px] text-slate-500 font-mono">Event ID: {selectedEvent.id}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedEvent(null)}
                  className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-6 overflow-y-auto space-y-5 text-xs">
                {/* Summary Box */}
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Summary</span>
                  <p className="text-xs font-semibold text-slate-800">{selectedEvent.summary}</p>
                </div>

                {/* Event Properties Grid */}
                <div className="grid grid-cols-2 gap-3 text-slate-600">
                  <div className="p-3 border border-slate-100 rounded-lg bg-slate-50/50">
                    <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Actor</span>
                    <div className="flex items-center gap-2">
                      {getActorBadge(selectedEvent.actor)}
                      {selectedEvent.actor.role && (
                        <span className="text-[11px] text-slate-500">({selectedEvent.actor.role})</span>
                      )}
                    </div>
                  </div>

                  <div className="p-3 border border-slate-100 rounded-lg bg-slate-50/50">
                    <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Timestamp</span>
                    <span className="font-mono font-medium text-slate-800">
                      {new Date(selectedEvent.created_at).toUTCString()}
                    </span>
                  </div>

                  <div className="p-3 border border-slate-100 rounded-lg bg-slate-50/50">
                    <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Entity Scope</span>
                    <span className="font-semibold text-slate-800">
                      {selectedEvent.entity_type} {selectedEvent.entity_id ? `(${selectedEvent.entity_id.slice(0, 8)}...)` : ""}
                    </span>
                  </div>

                  <div className="p-3 border border-slate-100 rounded-lg bg-slate-50/50">
                    <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Action Type</span>
                    <span className="font-semibold text-slate-800">{selectedEvent.action}</span>
                  </div>
                </div>

                {/* Structured JSON Metadata */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      Structured Telemetry & Metadata (JSON)
                    </span>
                    <button
                      type="button"
                      onClick={copyMetadata}
                      className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-blue-900 hover:text-blue-800"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="text-emerald-600">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy JSON</span>
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="p-4 bg-slate-900 text-slate-100 font-mono text-[11px] rounded-xl overflow-x-auto max-h-56">
                    {JSON.stringify(selectedEvent.metadata, null, 2)}
                  </pre>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
                <span className="text-[11px] text-slate-400">
                  Immutable record &middot; Append-only audit integrity guaranteed
                </span>
                <button
                  type="button"
                  onClick={() => setSelectedEvent(null)}
                  className="px-4 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
