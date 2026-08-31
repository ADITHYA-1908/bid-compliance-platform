"use client";

import React, { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  BidEvaluationReportResponse,
  TenderReportResponse,
} from "@/types/procurement_report";
import {
  downloadBidReportPDF,
  downloadTenderReportPDF,
  getBidEvaluationReport,
  getTenderReport,
} from "@/lib/api/procurement_report";
import { getProcurementDashboardSummary } from "@/lib/api/procurement_dashboard";
import { ProcurementDashboardSummaryResponse, TenderEvaluationOverviewItem } from "@/types/procurement_dashboard";
import {
  BarChart3,
  FileText,
  Download,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  Bot,
  RefreshCw,
  Award,
  Layers,
  ChevronRight,
  Info,
  Sliders,
  Sparkles,
  Printer,
  History,
} from "lucide-react";

export default function ProcurementReportsPage() {
  const [reportType, setReportType] = useState<"TENDER_SUMMARY" | "BID_DOSSIER">("TENDER_SUMMARY");
  const [tenders, setTenders] = useState<TenderEvaluationOverviewItem[]>([]);
  const [selectedTenderId, setSelectedTenderId] = useState<string>("");
  const [selectedBidId, setSelectedBidId] = useState<string>("");

  const [tenderReport, setTenderReport] = useState<TenderReportResponse | null>(null);
  const [bidReport, setBidReport] = useState<BidEvaluationReportResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(false);
  const [downloading, setDownloading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load tenders on mount
  useEffect(() => {
    async function loadDashboard() {
      try {
        const dash = await getProcurementDashboardSummary();
        if (dash.tenders && dash.tenders.length > 0) {
          setTenders(dash.tenders);
          setSelectedTenderId(dash.tenders[0].tender_id);
        }
      } catch (err: any) {
        console.error("Failed to load tenders for reporting:", err);
      }
    }
    loadDashboard();
  }, []);

  // Fetch report when selection changes
  const fetchReport = async () => {
    if (!selectedTenderId) return;
    setLoading(true);
    setError(null);

    try {
      if (reportType === "TENDER_SUMMARY") {
        const rep = await getTenderReport(selectedTenderId);
        setTenderReport(rep);
        setBidReport(null);
      } else {
        if (!selectedBidId) {
          setError("Please select or enter a Bid ID to view its evaluation dossier.");
          setLoading(false);
          return;
        }
        const rep = await getBidEvaluationReport(selectedTenderId, selectedBidId);
        setBidReport(rep);
        setTenderReport(null);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Failed to load procurement report.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedTenderId && reportType === "TENDER_SUMMARY") {
      fetchReport();
    }
  }, [selectedTenderId, reportType]);

  const handleDownloadPDF = async () => {
    setDownloading(true);
    try {
      let result: { blob: Blob; filename: string };
      if (reportType === "TENDER_SUMMARY") {
        result = await downloadTenderReportPDF(selectedTenderId);
      } else {
        result = await downloadBidReportPDF(selectedTenderId, selectedBidId);
      }

      const url = window.URL.createObjectURL(result.blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", result.filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`PDF download failed: ${err.message || err}`);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Procurement Reports & Evaluation Dossiers"
      description="Publication-grade compliance summaries, audit dossiers, and vector PDF exports for evaluation committees."
      breadcrumbs={[
        { label: "Procurement", href: "/procurement" },
        { label: "Reports" },
      ]}
      action={
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchReport}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            type="button"
            onClick={handleDownloadPDF}
            disabled={downloading || (!tenderReport && !bidReport)}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-blue-900 rounded-lg hover:bg-blue-800 transition-colors shadow-xs disabled:opacity-50"
          >
            <Download className={`w-3.5 h-3.5 ${downloading ? "animate-bounce" : ""}`} />
            {downloading ? "Generating PDF..." : "Export Vector PDF"}
          </button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Report Selector Header */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setReportType("TENDER_SUMMARY")}
                className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors ${
                  reportType === "TENDER_SUMMARY"
                    ? "bg-blue-900 text-white shadow-xs"
                    : "text-slate-600 bg-slate-100 hover:bg-slate-200"
                }`}
              >
                Tender Evaluation Summary
              </button>
              <button
                type="button"
                onClick={() => setReportType("BID_DOSSIER")}
                className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors ${
                  reportType === "BID_DOSSIER"
                    ? "bg-blue-900 text-white shadow-xs"
                    : "text-slate-600 bg-slate-100 hover:bg-slate-200"
                }`}
              >
                Bid Compliance Dossier
              </button>
            </div>

            <span className="text-xs text-slate-400 font-medium">
              Read-only report synthesis &middot; No re-evaluation or LLM triggers
            </span>
          </div>

          {/* Tender / Bid Pickers */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5">
                Select Tender
              </label>
              <select
                value={selectedTenderId}
                onChange={(e) => setSelectedTenderId(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 font-medium"
              >
                {tenders.map((t) => (
                  <option key={t.tender_id} value={t.tender_id}>
                    {t.tender_number} — {t.title.slice(0, 45)}...
                  </option>
                ))}
              </select>
            </div>

            {reportType === "BID_DOSSIER" && (
              <div>
                <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5">
                  Bid ID / Proposal UUID
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={selectedBidId}
                    onChange={(e) => setSelectedBidId(e.target.value)}
                    placeholder="Enter bid UUID e.g. 550e8400..."
                    className="flex-1 px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 font-mono"
                  />
                  <button
                    type="button"
                    onClick={fetchReport}
                    className="px-3.5 py-2 text-xs font-bold text-white bg-blue-900 rounded-lg hover:bg-blue-800 transition-colors shadow-xs"
                  >
                    Load
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-800 text-xs">
            <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
            <span>{error}</span>
          </div>
        )}

        {loading && (
          <div className="p-16 text-center text-slate-400 bg-white rounded-xl border border-slate-200 space-y-3">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-900" />
            <p className="text-xs font-semibold">Compiling authoritative evaluation report...</p>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TENDER SUMMARY REPORT VIEW                                                */}
        {/* ========================================================================= */}
        {!loading && tenderReport && reportType === "TENDER_SUMMARY" && (
          <div className="space-y-6">
            {/* Header Document Banner */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-4">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-blue-900 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200">
                    GeM Official Evaluation Summary
                  </span>
                  <h2 className="text-lg font-bold text-slate-900 mt-2">{tenderReport.tender.title}</h2>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">
                    Tender Number: {tenderReport.tender.tender_number} &middot; Organization: {tenderReport.tender.organization_name}
                  </p>
                </div>

                <div className="text-right text-xs text-slate-500">
                  <span className="font-semibold block text-slate-700">Status: {tenderReport.tender.status}</span>
                  <span>Generated: {new Date(tenderReport.generated_at).toUTCString()}</span>
                </div>
              </div>

              {/* KPI Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Bids</span>
                  <p className="text-xl font-bold text-slate-900">{tenderReport.total_bids_submitted}</p>
                  <span className="text-[11px] text-slate-500">Evaluated: {tenderReport.total_bids_evaluated}</span>
                </div>

                <div className="p-3 bg-emerald-50/50 border border-emerald-200 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-emerald-700 block">Qualified</span>
                  <p className="text-xl font-bold text-emerald-700">{tenderReport.total_qualified}</p>
                  <span className="text-[11px] text-emerald-600">Human confirmed</span>
                </div>

                <div className="p-3 bg-red-50/50 border border-red-200 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-red-700 block">Disqualified</span>
                  <p className="text-xl font-bold text-red-700">{tenderReport.total_disqualified}</p>
                  <span className="text-[11px] text-red-600">Defects / non-compliant</span>
                </div>

                <div className="p-3 bg-amber-50/50 border border-amber-200 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-amber-700 block">Under Review</span>
                  <p className="text-xl font-bold text-amber-700">{tenderReport.total_under_review}</p>
                  <span className="text-[11px] text-amber-600">Pending officer decision</span>
                </div>

                <div className="p-3 bg-blue-50/50 border border-blue-200 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-blue-800 block">Avg Score</span>
                  <p className="text-xl font-bold text-blue-900">
                    {tenderReport.average_compliance_score !== null ? `${tenderReport.average_compliance_score}%` : "N/A"}
                  </p>
                  <span className="text-[11px] text-blue-700">All active bids</span>
                </div>

                <div className="p-3 bg-purple-50/50 border border-purple-200 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-purple-700 block">Shortlisted</span>
                  <p className="text-xl font-bold text-purple-800">{tenderReport.total_shortlisted}</p>
                  <span className="text-[11px] text-purple-600">For commercial stage</span>
                </div>
              </div>
            </div>

            {/* Submitted Proposals Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900">Submitted Proposals Roster & Deterministic Status</h3>
                <span className="text-xs text-slate-500">{tenderReport.bids.length} proposals registered</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px] tracking-wider">
                      <th className="py-3 px-4">Bid Number</th>
                      <th className="py-3 px-4">Bidder Name</th>
                      <th className="py-3 px-4 text-right">Quoted Amount</th>
                      <th className="py-3 px-4 text-center">Score</th>
                      <th className="py-3 px-4 text-center">Risk Level</th>
                      <th className="py-3 px-4 text-center">Decision Status</th>
                      <th className="py-3 px-4 text-center">Shortlist</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {tenderReport.bids.map((b) => (
                      <tr key={b.bid_id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 font-mono font-semibold text-slate-800">{b.bid_number}</td>
                        <td className="py-3 px-4 font-medium text-slate-800">{b.bidder_name}</td>
                        <td className="py-3 px-4 text-right font-mono text-slate-700">
                          {b.quoted_amount ? `₹${b.quoted_amount.toLocaleString()}` : "N/A"}
                        </td>
                        <td className="py-3 px-4 text-center">
                          {b.compliance_score !== null ? (
                            <span className="font-bold text-emerald-700">{b.compliance_score}%</span>
                          ) : (
                            <span className="text-slate-400">N/A</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`inline-flex px-2 py-0.5 rounded-md text-[11px] font-bold ${
                              b.adjusted_risk_level === "CRITICAL"
                                ? "bg-red-100 text-red-800"
                                : b.adjusted_risk_level === "HIGH"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-emerald-100 text-emerald-800"
                            }`}
                          >
                            {b.adjusted_risk_level}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`inline-flex px-2 py-0.5 rounded-md text-[11px] font-bold ${
                              b.human_decision_status === "QUALIFIED"
                                ? "bg-emerald-100 text-emerald-800"
                                : b.human_decision_status === "DISQUALIFIED"
                                ? "bg-red-100 text-red-800"
                                : b.human_decision_status === "UNDER_REVIEW"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {b.human_decision_status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          {b.is_shortlisted ? (
                            <span className="text-emerald-700 font-bold">Yes</span>
                          ) : (
                            <span className="text-slate-400">No</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedBidId(b.bid_id);
                              setReportType("BID_DOSSIER");
                              setTimeout(() => fetchReport(), 0);
                            }}
                            className="px-2.5 py-1 text-xs font-semibold text-blue-900 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
                          >
                            View Dossier
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* BID COMPLIANCE DOSSIER VIEW                                               */}
        {/* ========================================================================= */}
        {!loading && bidReport && reportType === "BID_DOSSIER" && (
          <div className="space-y-6">
            {/* Staleness Banner if applicable */}
            {bidReport.stale_warnings.length > 0 && (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-1 text-xs text-amber-900">
                <div className="flex items-center gap-2 font-bold text-amber-800">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  <span>Evaluation Staleness Notice</span>
                </div>
                {bidReport.stale_warnings.map((w, idx) => (
                  <p key={idx} className="pl-6">&bull; {w}</p>
                ))}
              </div>
            )}

            {/* Mock Verification Disclaimer if applicable */}
            {bidReport.mock_verification_disclaimer && (
              <div className="p-3.5 bg-slate-100 border border-slate-200 rounded-xl text-xs text-slate-600 flex items-start gap-2.5">
                <Info className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                <p>{bidReport.mock_verification_disclaimer}</p>
              </div>
            )}

            {/* Top Dossier Header Card */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-4">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-purple-900 bg-purple-50 px-2.5 py-1 rounded-md border border-purple-200">
                    Bid Compliance Dossier
                  </span>
                  <h2 className="text-lg font-bold text-slate-900 mt-2">
                    {bidReport.bidder.name} ({bidReport.bid.bid_number})
                  </h2>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">
                    PAN: {bidReport.bidder.pan_number || "N/A"} &middot; GSTIN: {bidReport.bidder.gstin || "N/A"} &middot; Udyam: {bidReport.bidder.udyam_number || "N/A"}
                  </p>
                </div>

                <div className="text-right text-xs text-slate-500">
                  <span className="font-semibold block text-slate-700">Tender: {bidReport.tender.tender_number}</span>
                  <span>Generated: {new Date(bidReport.generated_at).toUTCString()}</span>
                </div>
              </div>

              {/* Core Determination Badges */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Overall Compliance Score</span>
                  <p className="text-3xl font-bold text-emerald-700 mt-1">
                    {bidReport.score.overall_compliance_score !== null ? `${bidReport.score.overall_compliance_score}%` : "N/A"}
                  </p>
                  <span className="text-xs text-slate-500">
                    {bidReport.compliance.passed_count} Passed / {bidReport.compliance.failed_count} Failed
                  </span>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Deterministic Risk Level</span>
                  <p
                    className={`text-3xl font-bold mt-1 ${
                      bidReport.risk.adjusted_risk_level === "CRITICAL"
                        ? "text-red-700"
                        : bidReport.risk.adjusted_risk_level === "HIGH"
                        ? "text-amber-700"
                        : "text-emerald-700"
                    }`}
                  >
                    {bidReport.risk.adjusted_risk_level || "LOW"}
                  </p>
                  <span className="text-xs text-slate-500">
                    Overrides: {bidReport.risk.override_applied ? "Applied" : "None"}
                  </span>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Final Human Decision</span>
                  <p
                    className={`text-3xl font-bold mt-1 ${
                      bidReport.final_human_decision.decision === "QUALIFIED"
                        ? "text-emerald-700"
                        : bidReport.final_human_decision.decision === "DISQUALIFIED"
                        ? "text-red-700"
                        : "text-amber-700"
                    }`}
                  >
                    {bidReport.final_human_decision.decision}
                  </p>
                  <span className="text-xs text-slate-500">
                    By: {bidReport.final_human_decision.decided_by_name || "Pending Officer"}
                  </span>
                </div>
              </div>
            </div>

            {/* Authoritative Human Decision Section */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                <User className="w-4 h-4 text-blue-900" />
                <h3 className="text-sm font-bold text-slate-900">Authoritative Human Procurement Decision</h3>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Determination</span>
                    <span className="font-bold text-slate-800">{bidReport.final_human_decision.decision}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Deciding Officer</span>
                    <span className="font-medium text-slate-800">
                      {bidReport.final_human_decision.decided_by_name || "Not Decided"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Decision Date</span>
                    <span className="font-medium text-slate-800">
                      {bidReport.final_human_decision.decided_at
                        ? new Date(bidReport.final_human_decision.decided_at).toUTCString()
                        : "Pending"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Version</span>
                    <span className="font-mono text-slate-800">v{bidReport.final_human_decision.decision_version}</span>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Justification Reason</span>
                  <p className="text-xs text-slate-800 bg-white p-3 rounded-lg border border-slate-200">
                    {bidReport.final_human_decision.reason || "No final decision recorded yet."}
                  </p>
                </div>
              </div>

              {/* Decision Version History */}
              {bidReport.decision_history.length > 1 && (
                <div className="space-y-2 pt-2">
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Decision Version Ledger</h4>
                  <div className="space-y-2">
                    {bidReport.decision_history.map((dh) => (
                      <div key={dh.decision_version} className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs flex items-center justify-between">
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-800">v{dh.decision_version} &middot; {dh.decision}</span>
                            {dh.is_current && (
                              <span className="px-1.5 py-0.2 rounded-sm text-[10px] font-bold bg-emerald-100 text-emerald-800">
                                Current
                              </span>
                            )}
                          </div>
                          <p className="text-slate-500">{dh.reason}</p>
                        </div>
                        <span className="text-slate-400 text-[11px] font-mono whitespace-nowrap">
                          {new Date(dh.decided_at).toLocaleDateString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Category Compliance Scores */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                <Layers className="w-4 h-4 text-blue-900" />
                <h3 className="text-sm font-bold text-slate-900">Category Compliance Breakdown</h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {Object.entries(bidReport.score.category_scores).map(([cat, catData]: [string, any]) => (
                  <div key={cat} className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">
                      {cat.replace("_", " ")}
                    </span>
                    <p className="text-lg font-bold text-slate-900">
                      {catData.percentage_score !== undefined ? `${catData.percentage_score}%` : "N/A"}
                    </p>
                    <span className="text-[11px] text-slate-500">
                      Passed {catData.passed_count || 0} of {catData.total_count || 0} requirements
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Advisory AI Recommendation (Clearly Labeled Advisory) */}
            {bidReport.ai_recommendation && (
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-3">
                <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                  <Sparkles className="w-4 h-4 text-purple-600" />
                  <h3 className="text-sm font-bold text-slate-900">
                    AI-Assisted Evaluation Recommendation (Advisory Guidance Only)
                  </h3>
                </div>

                <div className="p-4 bg-purple-50/50 border border-purple-200 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-purple-900">
                      Recommendation: {bidReport.ai_recommendation.recommendation}
                    </span>
                    <span className="text-slate-500 font-mono text-[11px]">
                      Model: {bidReport.ai_recommendation.model_name || "Standard"}
                    </span>
                  </div>
                  <p className="text-slate-700">{bidReport.ai_recommendation.summary || bidReport.ai_recommendation.recommendation_reason}</p>
                  <p className="text-[11px] text-purple-700 italic border-t border-purple-100 pt-2">
                    {bidReport.ai_recommendation.advisory_disclaimer}
                  </p>
                </div>
              </div>
            )}

            {/* Audit Trail Timeline */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                <History className="w-4 h-4 text-blue-900" />
                <h3 className="text-sm font-bold text-slate-900">Chronological Procurement Audit Trail</h3>
              </div>

              <div className="space-y-2.5">
                {bidReport.audit_timeline.map((evt, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 border border-slate-100 rounded-lg text-xs flex items-center justify-between">
                    <div className="space-y-0.5">
                      <span className="font-bold text-slate-800">{evt.event_label}</span>
                      <p className="text-slate-600">{evt.summary}</p>
                    </div>
                    <div className="text-right text-[11px] text-slate-400 font-mono">
                      <span>{evt.actor_name} ({evt.actor_source})</span>
                      <span className="block">{new Date(evt.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
