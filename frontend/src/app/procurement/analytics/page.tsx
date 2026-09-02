"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  BarChart2,
  BarChart3,
  Calendar,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  ExternalLink,
  Eye,
  FileCheck,
  FileSearch,
  FileText,
  Filter,
  Layers,
  PieChart,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { analyticsApi, AnalyticsFilterParams } from "@/lib/api/analytics";
import { getProcurementDashboardSummary } from "@/lib/api/procurement_dashboard";
import {
  BulkAnalytics,
  CommonFailureReason,
  ComplianceAnalytics,
  DocumentQualityAnalytics,
  DuplicateAnalytics,
  HumanReviewAndDecision,
  OverviewKPIs,
  RiskAnalytics,
  TimeSeriesPoint,
  VerificationAnalytics,
} from "@/types/analytics";
import { TenderEvaluationOverviewItem } from "@/types/procurement_dashboard";

type DateRangePreset = "7D" | "30D" | "90D" | "ALL";
type AnalyticsTab = "overview" | "compliance" | "risk" | "verification" | "reviews" | "bulk";

export default function ProcurementAnalyticsPage() {
  const { user } = useAuth();

  // Selected Tab & Filters
  const [activeTab, setActiveTab] = useState<AnalyticsTab>("overview");
  const [selectedTenderId, setSelectedTenderId] = useState<string>("");
  const [datePreset, setDatePreset] = useState<DateRangePreset>("30D");
  const [tenders, setTenders] = useState<TenderEvaluationOverviewItem[]>([]);

  // State Data
  const [kpis, setKpis] = useState<OverviewKPIs | null>(null);
  const [compliance, setCompliance] = useState<ComplianceAnalytics | null>(null);
  const [risk, setRisk] = useState<RiskAnalytics | null>(null);
  const [verification, setVerification] = useState<VerificationAnalytics | null>(null);
  const [quality, setQuality] = useState<DocumentQualityAnalytics | null>(null);
  const [duplicates, setDuplicates] = useState<DuplicateAnalytics | null>(null);
  const [bulk, setBulk] = useState<BulkAnalytics | null>(null);
  const [reviewsDecisions, setReviewsDecisions] = useState<HumanReviewAndDecision | null>(null);
  const [trends, setTrends] = useState<TimeSeriesPoint[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load available tenders for filter dropdown
  useEffect(() => {
    async function loadTenders() {
      try {
        const res = await getProcurementDashboardSummary();
        setTenders(res.tenders || []);
      } catch {
        // non-blocking
      }
    }
    loadTenders();
  }, []);

  // Compute filter dates from preset
  const getFilterParams = useCallback((): AnalyticsFilterParams => {
    const params: AnalyticsFilterParams = {};
    if (selectedTenderId) params.tender_id = selectedTenderId;

    if (datePreset !== "ALL") {
      const now = new Date();
      const days = datePreset === "7D" ? 7 : datePreset === "30D" ? 30 : 90;
      const start = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
      params.start_date = start.toISOString();
      params.end_date = now.toISOString();
      params.days = days;
    }
    return params;
  }, [selectedTenderId, datePreset]);

  // Fetch all analytics datasets
  const fetchAnalytics = useCallback(async () => {
    if (!user) return;
    setIsLoading(true);
    setError(null);
    const params = getFilterParams();

    try {
      const [
        kpisRes,
        complianceRes,
        riskRes,
        verifRes,
        qualityRes,
        dupRes,
        bulkRes,
        revDecRes,
        trendsRes,
      ] = await Promise.all([
        analyticsApi.getOverviewKPIs(params),
        analyticsApi.getComplianceAnalytics(params),
        analyticsApi.getRiskAnalytics(params),
        analyticsApi.getVerificationAnalytics(params),
        analyticsApi.getDocumentQualityAnalytics(params),
        analyticsApi.getDuplicateAnalytics(params),
        analyticsApi.getBulkAnalytics(params),
        analyticsApi.getHumanReviewsAndDecisions(params),
        analyticsApi.getActivityTrends(params),
      ]);

      setKpis(kpisRes);
      setCompliance(complianceRes);
      setRisk(riskRes);
      setVerification(verifRes);
      setQuality(qualityRes);
      setDuplicates(dupRes);
      setBulk(bulkRes);
      setReviewsDecisions(revDecRes);
      setTrends(trendsRes || []);
    } catch (err: any) {
      setError(err.message || "Failed to load procurement analytics telemetry.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [user, getFilterParams]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchAnalytics();
  };

  const formatPercent = (val?: number | null) => (val !== undefined && val !== null ? `${val.toFixed(1)}%` : "N/A");

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Procurement Analytics & Impact"
      description="Multi-dimensional procurement intelligence: statutory compliance, risk radar, verification rates, and time savings"
      breadcrumbs={[{ label: "Procurement", href: "/procurement" }, { label: "Analytics & Impact" }]}
    >
      <div className="space-y-6 pb-16">
        {/* Global Filter Toolbar */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs">
          <div className="flex flex-wrap items-center gap-3">
            {/* Tender Selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-500">Tender:</span>
              <select
                value={selectedTenderId}
                onChange={(e) => setSelectedTenderId(e.target.value)}
                className="rounded-lg border border-slate-200 bg-slate-50/50 py-1.5 px-3 text-xs font-semibold text-slate-800 focus:border-blue-900 focus:outline-hidden"
              >
                <option value="">All Tenders (Organization Scope)</option>
                {tenders.map((t) => (
                  <option key={t.tender_id} value={t.tender_id}>
                    {t.tender_number} — {t.title.slice(0, 35)}...
                  </option>
                ))}
              </select>
            </div>

            {/* Date Range Presets */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
              {(["7D", "30D", "90D", "ALL"] as DateRangePreset[]).map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setDatePreset(preset)}
                  className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors cursor-pointer ${
                    datePreset === preset
                      ? "bg-white text-blue-900 shadow-2xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {preset === "ALL" ? "All Time" : preset}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-2xs cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin text-blue-900" : "text-slate-500"}`} />
              <span>Refresh</span>
            </button>

            <a
              href={analyticsApi.getExportUrl(getFilterParams())}
              download
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-900 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-800 shadow-xs cursor-pointer"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Export CSV</span>
            </a>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-medium text-red-800 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Overview KPI Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
          {/* Active Tenders */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider">Tenders</span>
              <FileText className="h-4 w-4 text-blue-900" />
            </div>
            <p className="text-xl font-bold text-slate-900 tracking-tight">
              {kpis?.total_tenders || 0}
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              {kpis?.active_tenders || 0} Active / Published
            </p>
          </div>

          {/* Bids Evaluated */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider">Bids Evaluated</span>
              <Layers className="h-4 w-4 text-indigo-600" />
            </div>
            <p className="text-xl font-bold text-slate-900 tracking-tight">
              {kpis?.evaluated_bids || 0}{" "}
              <span className="text-xs font-normal text-slate-400">/ {kpis?.submitted_bids || 0}</span>
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Total Submitted Bids</p>
          </div>

          {/* Compliance Rate */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider">Compliance Rate</span>
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
            </div>
            <p className="text-xl font-bold text-emerald-600 tracking-tight">
              {formatPercent(kpis?.compliance_rate_percentage)}
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Statutory Rules Passed</p>
          </div>

          {/* High / Critical Risk */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider">Risk Level</span>
              <ShieldAlert className="h-4 w-4 text-rose-600" />
            </div>
            <p className="text-xl font-bold text-rose-600 tracking-tight">
              {kpis?.high_critical_risk_bids || 0}
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              Avg Score: {kpis?.average_risk_score !== null && kpis?.average_risk_score !== undefined ? `${kpis.average_risk_score}` : "N/A"}
            </p>
          </div>

          {/* Open Reviews Backlog */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider">Reviews Backlog</span>
              <Users className="h-4 w-4 text-amber-500" />
            </div>
            <p className="text-xl font-bold text-amber-600 tracking-tight">
              {kpis?.open_reviews_count || 0}
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Open & In-Review</p>
          </div>

          {/* Quality & Duplicate Alerts */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider">Quality & Dup</span>
              <Sparkles className="h-4 w-4 text-purple-600" />
            </div>
            <p className="text-xl font-bold text-purple-700 tracking-tight">
              {kpis?.poor_quality_documents_count || 0} <span className="text-xs font-normal text-slate-400">/ {kpis?.duplicate_alerts_count || 0}</span>
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Poor Quality / Duplicates</p>
          </div>
        </div>

        {/* Procurement Impact & Time Savings Banner */}
        {kpis?.procurement_impact && (
          <div className="rounded-2xl border border-emerald-200 bg-gradient-to-r from-emerald-50 via-teal-50 to-blue-50 p-5 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-xs">
                <Zap className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-emerald-950">
                    Empirical Procurement Impact & Time Acceleration
                  </h3>
                  <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-bold text-emerald-800">
                    {kpis.procurement_impact.measured_time_reduction_percentage}% Faster
                  </span>
                </div>
                <p className="text-xs text-emerald-800/80 mt-0.5">
                  Automated verification takes ~{(kpis.procurement_impact.avg_automated_time_ms / 1000).toFixed(2)}s per document vs {(kpis.procurement_impact.avg_manual_baseline_sec / 60).toFixed(1)} mins manual baseline (evaluated across {kpis.procurement_impact.total_validation_cases} ground-truth test cases).
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4 shrink-0 text-right">
              <div className="border-l border-emerald-200 pl-4 hidden sm:block">
                <p className="text-[10px] uppercase font-bold text-emerald-700">Automated Speed</p>
                <p className="text-sm font-bold text-emerald-900 font-mono">
                  {kpis.procurement_impact.avg_automated_time_ms.toFixed(1)} ms
                </p>
              </div>
              <div className="border-l border-emerald-200 pl-4 hidden sm:block">
                <p className="text-[10px] uppercase font-bold text-emerald-700">Manual Baseline</p>
                <p className="text-sm font-bold text-emerald-900 font-mono">
                  {(kpis.procurement_impact.avg_manual_baseline_sec / 60).toFixed(1)} mins
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tabbed Navigation Bar */}
        <div className="border-b border-slate-200">
          <nav className="flex space-x-6 overflow-x-auto pb-px text-xs font-semibold">
            {[
              { id: "overview", label: "Executive Overview & Trends", icon: TrendingUp },
              { id: "compliance", label: "Compliance & Root Causes", icon: ShieldCheck },
              { id: "risk", label: "Risk Radar & Overrides", icon: ShieldAlert },
              { id: "verification", label: "Verification & Document Quality", icon: FileCheck },
              { id: "reviews", label: "Review Workload & Decisions", icon: Users },
              { id: "bulk", label: "Batch Verification (Part 9)", icon: Layers },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id as AnalyticsTab)}
                  className={`flex items-center gap-2 border-b-2 py-3 px-1 transition-colors cursor-pointer whitespace-nowrap ${
                    isActive
                      ? "border-blue-900 text-blue-900 font-bold"
                      : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? "text-blue-900" : "text-slate-400"}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* ================================================================= */}
        {/* TAB 1: EXECUTIVE OVERVIEW & ACTIVITY TRENDS */}
        {/* ================================================================= */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Trends Chart & Breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Time Series Activity Bars */}
              <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Bid Submissions & Evaluations Timeline</h3>
                    <p className="text-xs text-slate-400">Daily activity trends across active procurement tenders</p>
                  </div>
                  <span className="text-xs font-semibold text-slate-500">{datePreset === "ALL" ? "All History" : `Last ${datePreset}`}</span>
                </div>

                {trends.length === 0 ? (
                  <div className="py-16 text-center text-xs text-slate-400">
                    No activity timeline data recorded for the selected filter range.
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="h-44 flex items-end gap-1.5 pt-4 overflow-x-auto">
                      {trends.slice(-14).map((pt) => {
                        const maxVal = Math.max(...trends.map((t) => Math.max(t.submitted_bids, t.evaluated_bids, 1)));
                        const subHeight = Math.max(4, Math.round((pt.submitted_bids / maxVal) * 120));
                        const evalHeight = Math.max(4, Math.round((pt.evaluated_bids / maxVal) * 120));

                        return (
                          <div key={pt.date} className="flex-1 flex flex-col items-center gap-1 min-w-[28px]" title={`${pt.date}: ${pt.submitted_bids} submitted, ${pt.evaluated_bids} evaluated`}>
                            <div className="w-full flex items-end justify-center gap-0.5 h-32">
                              <div className="w-2.5 rounded-t-sm bg-blue-900 transition-all" style={{ height: `${subHeight}px` }} />
                              <div className="w-2.5 rounded-t-sm bg-emerald-500 transition-all" style={{ height: `${evalHeight}px` }} />
                            </div>
                            <span className="text-[9px] text-slate-400 rotate-45 origin-left truncate">{pt.date.slice(5)}</span>
                          </div>
                        );
                      })}
                    </div>

                    <div className="flex items-center justify-center gap-6 pt-3 border-t border-slate-100 text-xs text-slate-600">
                      <div className="flex items-center gap-1.5">
                        <span className="h-3 w-3 rounded-xs bg-blue-900" />
                        <span>Submitted Bids</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="h-3 w-3 rounded-xs bg-emerald-500" />
                        <span>Evaluated Bids</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Quick Health Radar */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs flex flex-col justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 mb-1">Procurement Health Summary</h3>
                  <p className="text-xs text-slate-400 mb-4">Key indicators across the active pipeline</p>

                  <div className="space-y-3.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-600">Statutory Compliance Rate</span>
                      <span className="font-bold text-slate-900 font-mono">{formatPercent(kpis?.compliance_rate_percentage)}</span>
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-600">Document Quality Score</span>
                      <span className="font-bold text-slate-900 font-mono">
                        {kpis?.average_quality_score !== null && kpis?.average_quality_score !== undefined ? `${kpis.average_quality_score}/100` : "N/A"}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-600">Open Human Reviews</span>
                      <span className="font-bold text-amber-600 font-mono">{kpis?.open_reviews_count || 0}</span>
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-600">High / Critical Risk Bids</span>
                      <span className="font-bold text-rose-600 font-mono">{kpis?.high_critical_risk_bids || 0}</span>
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-600">Duplicate Alerts (Part 10)</span>
                      <span className="font-bold text-purple-700 font-mono">{kpis?.duplicate_alerts_count || 0}</span>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-slate-400">Total Bids Processed</span>
                  <span className="font-bold text-blue-900 font-mono">{kpis?.total_bids || 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 2: COMPLIANCE & ROOT CAUSE REASONS */}
        {/* ================================================================= */}
        {activeTab === "compliance" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Compliance Status Distribution */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-sm font-bold text-slate-900 mb-1">Compliance Status Distribution</h3>
                <p className="text-xs text-slate-400 mb-4">Rule-by-rule statutory determinations</p>

                <div className="space-y-3">
                  {[
                    { key: "PASS", label: "Passed Rules", color: "bg-emerald-500", text: "text-emerald-700", bg: "bg-emerald-50" },
                    { key: "FAIL", label: "Failed Rules", color: "bg-rose-500", text: "text-rose-700", bg: "bg-rose-50" },
                    { key: "REVIEW", label: "Review Required", color: "bg-amber-500", text: "text-amber-700", bg: "bg-amber-50" },
                    { key: "PENDING", label: "Pending Evaluation", color: "bg-slate-400", text: "text-slate-700", bg: "bg-slate-50" },
                  ].map((item) => {
                    const count = compliance?.distribution?.[item.key] || 0;
                    const tot = compliance?.total_evaluations || 1;
                    const pct = (count / tot) * 100;

                    return (
                      <div key={item.key} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-slate-700">{item.label}</span>
                          <span className="font-bold text-slate-900 font-mono">
                            {count} <span className="text-[10px] text-slate-400 font-normal">({pct.toFixed(1)}%)</span>
                          </span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                          <div className={`h-full rounded-full ${item.color}`} style={{ width: `${Math.max(1, pct)}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-slate-500">Mandatory Rule Failures</span>
                  <span className="font-bold text-rose-600 font-mono">{compliance?.mandatory_failures_count || 0}</span>
                </div>
              </div>

              {/* Common Failure Root Causes */}
              <div className="md:col-span-2 rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-sm font-bold text-slate-900 mb-1">Common Failure Reasons & Discrepancies</h3>
                <p className="text-xs text-slate-400 mb-4">Extracted from actual recorded rule evaluation justifications</p>

                {compliance?.common_failure_reasons.length === 0 ? (
                  <div className="py-12 text-center text-xs text-slate-400">
                    No compliance failures recorded in the current scope.
                  </div>
                ) : (
                  <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
                    {compliance?.common_failure_reasons.map((r, idx) => {
                      const maxFail = Math.max(...(compliance?.common_failure_reasons.map((c) => c.count) || [1]));
                      const pct = Math.round((r.count / maxFail) * 100);

                      return (
                        <div key={idx} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold text-slate-800">{r.reason}</span>
                            <span className="font-bold text-slate-900 font-mono">{r.count} cases</span>
                          </div>
                          <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                            <div className="h-full rounded-full bg-rose-500" style={{ width: `${Math.max(4, pct)}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Top Failed Requirements Table */}
            {compliance?.top_failed_requirements && compliance.top_failed_requirements.length > 0 && (
              <div className="rounded-2xl border border-slate-200 bg-white shadow-2xs overflow-hidden">
                <div className="border-b border-slate-200 bg-slate-50/75 px-5 py-3.5">
                  <h3 className="text-sm font-bold text-slate-900">Most Frequently Failed Tender Requirements</h3>
                </div>
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="border-b border-slate-200 bg-slate-50 text-[11px] font-semibold text-slate-700 uppercase">
                    <tr>
                      <th className="py-2.5 px-4">Code</th>
                      <th className="py-2.5 px-4">Requirement Title</th>
                      <th className="py-2.5 px-4">Category</th>
                      <th className="py-2.5 px-4 text-right">Failure Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {compliance.top_failed_requirements.map((req, i) => (
                      <tr key={i} className="hover:bg-slate-50">
                        <td className="py-2.5 px-4 font-mono font-bold text-slate-900">{req.requirement_code}</td>
                        <td className="py-2.5 px-4 font-medium text-slate-800">{req.title}</td>
                        <td className="py-2.5 px-4">
                          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                            {req.category}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-right font-mono font-bold text-rose-600">{req.fail_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 3: RISK RADAR & OVERRIDES */}
        {/* ================================================================= */}
        {activeTab === "risk" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[
                { key: "LOW", label: "Low Risk", color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200", badge: "0 – 29" },
                { key: "MEDIUM", label: "Medium Risk", color: "text-blue-700", bg: "bg-blue-50", border: "border-blue-200", badge: "30 – 59" },
                { key: "HIGH", label: "High Risk", color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200", badge: "60 – 79" },
                { key: "CRITICAL", label: "Critical Risk", color: "text-rose-700", bg: "bg-rose-50", border: "border-rose-200", badge: "80 – 100" },
              ].map((tier) => {
                const count = risk?.distribution?.[tier.key] || 0;
                const tot = risk?.total_risk_evaluated_bids || 1;
                const pct = (count / tot) * 100;

                return (
                  <div key={tier.key} className={`rounded-2xl border ${tier.border} ${tier.bg} p-4 shadow-2xs`}>
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className={`font-bold uppercase tracking-wider ${tier.color}`}>{tier.label}</span>
                      <span className="text-[10px] text-slate-500 font-mono">Score {tier.badge}</span>
                    </div>
                    <p className={`text-2xl font-bold tracking-tight ${tier.color}`}>
                      {count}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1">
                      {pct.toFixed(1)}% of evaluated bids
                    </p>
                  </div>
                );
              })}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Risk Summary Telemetry */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs space-y-4">
                <h3 className="text-sm font-bold text-slate-900">Deterministic Risk Telemetry (Part 7)</h3>

                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs border-b border-slate-100 pb-2">
                    <span className="text-slate-600">Total Risk Evaluated Bids</span>
                    <span className="font-bold text-slate-900 font-mono">{risk?.total_risk_evaluated_bids || 0}</span>
                  </div>

                  <div className="flex items-center justify-between text-xs border-b border-slate-100 pb-2">
                    <span className="text-slate-600">Average Risk Score</span>
                    <span className="font-bold text-blue-900 font-mono">
                      {risk?.average_risk_score !== null && risk?.average_risk_score !== undefined ? `${risk.average_risk_score} / 100` : "N/A"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-xs border-b border-slate-100 pb-2">
                    <span className="text-slate-600">Critical Overrides Applied (Debarment/Blacklist)</span>
                    <span className="font-bold text-rose-600 font-mono">{risk?.overrides_applied_count || 0}</span>
                  </div>
                </div>
              </div>

              {/* Risk Mitigation Guidance */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs space-y-3">
                <h3 className="text-sm font-bold text-slate-900">Officer Risk Policies</h3>
                <p className="text-xs text-slate-500">
                  • <strong>CRITICAL (80–100):</strong> Automatic recommendation for human review and mandatory disqualification assessment.
                </p>
                <p className="text-xs text-slate-500">
                  • <strong>HIGH (60–79):</strong> Requires manual review of statutory documentation and OEM warranty backing.
                </p>
                <p className="text-xs text-slate-500">
                  • <strong>LOW/MEDIUM (0–59):</strong> Eligible for streamlined procurement progression subject to mandatory rule clearance.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 4: MULTI-SOURCE VERIFICATION & DOCUMENT QUALITY */}
        {/* ================================================================= */}
        {activeTab === "verification" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Document Quality Distribution (Part 11) */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-sm font-bold text-slate-900 mb-1">Document Quality Tiers (Part 11)</h3>
                <p className="text-xs text-slate-400 mb-4">Deterministic image & scan diagnostics prior to OCR</p>

                <div className="space-y-3">
                  {[
                    { key: "GOOD", label: "GOOD (90–100)", color: "bg-emerald-500" },
                    { key: "ACCEPTABLE", label: "ACCEPTABLE (70–89)", color: "bg-blue-500" },
                    { key: "POOR", label: "POOR (40–69) - Review Required", color: "bg-amber-500" },
                    { key: "UNUSABLE", label: "UNUSABLE (0–39) - OCR Halting", color: "bg-rose-500" },
                  ].map((item) => {
                    const count = quality?.distribution?.[item.key] || 0;
                    const tot = quality?.total_documents_analyzed || 1;
                    const pct = (count / tot) * 100;

                    return (
                      <div key={item.key} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-slate-700">{item.label}</span>
                          <span className="font-bold text-slate-900 font-mono">
                            {count} <span className="text-[10px] text-slate-400 font-normal">({pct.toFixed(1)}%)</span>
                          </span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                          <div className={`h-full rounded-full ${item.color}`} style={{ width: `${Math.max(1, pct)}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="bg-slate-50 p-2 rounded-lg">
                    <p className="text-[10px] text-slate-400">Blurry Scans</p>
                    <p className="font-bold text-amber-600 font-mono">{quality?.diagnostics.blurry_documents || 0}</p>
                  </div>
                  <div className="bg-slate-50 p-2 rounded-lg">
                    <p className="text-[10px] text-slate-400">Blank Pages</p>
                    <p className="font-bold text-rose-600 font-mono">{quality?.diagnostics.blank_page_documents || 0}</p>
                  </div>
                  <div className="bg-slate-50 p-2 rounded-lg">
                    <p className="text-[10px] text-slate-400">Low Resolution</p>
                    <p className="font-bold text-slate-700 font-mono">{quality?.diagnostics.low_resolution_documents || 0}</p>
                  </div>
                </div>
              </div>

              {/* Duplicate & Reuse Detection (Part 10) */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-sm font-bold text-slate-900 mb-1">Duplicate & Reuse Telemetry (Part 10)</h3>
                <p className="text-xs text-slate-400 mb-4">Multi-signal cross-bid file and content matches</p>

                <div className="space-y-3">
                  {duplicates?.match_type_distribution &&
                    Object.entries(duplicates.match_type_distribution).map(([mtype, cnt]) => (
                      <div key={mtype} className="flex items-center justify-between text-xs border-b border-slate-100 pb-1.5">
                        <span className="font-semibold text-slate-700">{mtype.replace(/_/g, " ")}</span>
                        <span className="font-bold text-slate-900 font-mono">{cnt}</span>
                      </div>
                    ))}
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-slate-500">Total Duplicate / Reuse Alerts</span>
                  <span className="font-bold text-purple-700 font-mono">{duplicates?.total_duplicate_alerts || 0}</span>
                </div>
              </div>
            </div>

            {/* Verification Source Outcomes Table */}
            {verification?.source_breakdown && verification.source_breakdown.length > 0 && (
              <div className="rounded-2xl border border-slate-200 bg-white shadow-2xs overflow-hidden">
                <div className="border-b border-slate-200 bg-slate-50/75 px-5 py-3.5 flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900">External Verification Source Breakdown (Part 5)</h3>
                  <span className="text-xs text-slate-500 font-mono">{verification.total_verifications} total checks</span>
                </div>
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="border-b border-slate-200 bg-slate-50 text-[11px] font-semibold text-slate-700 uppercase">
                    <tr>
                      <th className="py-2.5 px-4">Verification Type / Source</th>
                      <th className="py-2.5 px-4 text-center">Total Checks</th>
                      <th className="py-2.5 px-4 text-center">Verified</th>
                      <th className="py-2.5 px-4 text-center">Failed / Unverified</th>
                      <th className="py-2.5 px-4 text-center">Review Required</th>
                      <th className="py-2.5 px-4 text-right">Success Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {verification.source_breakdown.map((src, i) => (
                      <tr key={i} className="hover:bg-slate-50">
                        <td className="py-2.5 px-4 font-bold text-slate-900">{src.verification_type}</td>
                        <td className="py-2.5 px-4 text-center font-mono">{src.total}</td>
                        <td className="py-2.5 px-4 text-center font-mono font-bold text-emerald-600">{src.verified}</td>
                        <td className="py-2.5 px-4 text-center font-mono font-bold text-rose-600">{src.failed}</td>
                        <td className="py-2.5 px-4 text-center font-mono font-bold text-amber-600">{src.review_required}</td>
                        <td className="py-2.5 px-4 text-right font-mono font-bold text-blue-900">{src.success_rate.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 5: WORKLOAD & FINAL HUMAN DECISIONS */}
        {/* ================================================================= */}
        {activeTab === "reviews" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Human Review Queue (Part 8C) */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-sm font-bold text-slate-900 mb-1">Human Review Workload Queue (Part 8C)</h3>
                <p className="text-xs text-slate-400 mb-4">Officer review backlog across flagged items</p>

                <div className="grid grid-cols-3 gap-2 text-center text-xs mb-4">
                  <div className="bg-amber-50 border border-amber-200 p-3 rounded-xl">
                    <p className="text-[10px] text-amber-700 font-bold uppercase">Open</p>
                    <p className="text-lg font-bold text-amber-900 mt-0.5 font-mono">{reviewsDecisions?.review_status_distribution.OPEN || 0}</p>
                  </div>
                  <div className="bg-blue-50 border border-blue-200 p-3 rounded-xl">
                    <p className="text-[10px] text-blue-700 font-bold uppercase">In Review</p>
                    <p className="text-lg font-bold text-blue-900 mt-0.5 font-mono">{reviewsDecisions?.review_status_distribution.IN_REVIEW || 0}</p>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 p-3 rounded-xl">
                    <p className="text-[10px] text-emerald-700 font-bold uppercase">Resolved</p>
                    <p className="text-lg font-bold text-emerald-900 mt-0.5 font-mono">{reviewsDecisions?.review_status_distribution.RESOLVED || 0}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-xs font-bold text-slate-700">Review Reasons Breakdown:</p>
                  {reviewsDecisions?.review_types_breakdown &&
                    reviewsDecisions.review_types_breakdown.map((rt) => (
                      <div key={rt.review_type} className="flex items-center justify-between text-xs border-b border-slate-100 pb-1">
                        <span className="text-slate-600">{rt.review_type.replace(/_/g, " ")}</span>
                        <span className="font-bold text-slate-900 font-mono">{rt.count}</span>
                      </div>
                    ))}
                </div>
              </div>

              {/* Authoritative Human Qualification Decisions (Part 8D) */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-sm font-bold text-slate-900 mb-1">Final Human Qualification Decisions (Part 8D)</h3>
                <p className="text-xs text-slate-400 mb-4">Officer determinations on bid submissions</p>

                <div className="grid grid-cols-2 gap-2 text-center text-xs mb-4">
                  <div className="bg-emerald-50 border border-emerald-200 p-3 rounded-xl">
                    <p className="text-[10px] text-emerald-700 font-bold uppercase">Qualified</p>
                    <p className="text-lg font-bold text-emerald-900 mt-0.5 font-mono">
                      {reviewsDecisions?.decision_status_distribution.QUALIFIED || 0}
                    </p>
                  </div>
                  <div className="bg-rose-50 border border-rose-200 p-3 rounded-xl">
                    <p className="text-[10px] text-rose-700 font-bold uppercase">Disqualified</p>
                    <p className="text-lg font-bold text-rose-900 mt-0.5 font-mono">
                      {reviewsDecisions?.decision_status_distribution.DISQUALIFIED || 0}
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-xs font-bold text-slate-700">Disqualification Categories:</p>
                  {reviewsDecisions?.disqualification_categories && reviewsDecisions.disqualification_categories.length > 0 ? (
                    reviewsDecisions.disqualification_categories.map((dc) => (
                      <div key={dc.category} className="flex items-center justify-between text-xs border-b border-slate-100 pb-1">
                        <span className="text-slate-600">{dc.category.replace(/_/g, " ")}</span>
                        <span className="font-bold text-rose-600 font-mono">{dc.count}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-slate-400 italic">No disqualifications recorded yet.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 6: BATCH EVALUATION OPERATIONS (PART 9) */}
        {/* ================================================================= */}
        {activeTab === "bulk" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-sm font-bold text-slate-900 mb-1">Bulk Jobs Overview</h3>
                <p className="text-xs text-slate-400 mb-4">Part 9 multi-bid automated batch pipelines</p>

                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs border-b border-slate-100 pb-2">
                    <span className="text-slate-600">Total Bulk Jobs Created</span>
                    <span className="font-bold text-slate-900 font-mono">{bulk?.total_jobs || 0}</span>
                  </div>

                  <div className="flex items-center justify-between text-xs border-b border-slate-100 pb-2">
                    <span className="text-slate-600">Total Bids Processed in Batch</span>
                    <span className="font-bold text-blue-900 font-mono">{bulk?.total_bids_processed || 0}</span>
                  </div>

                  <div className="flex items-center justify-between text-xs border-b border-slate-100 pb-2">
                    <span className="text-slate-600">Job Success Rate</span>
                    <span className="font-bold text-emerald-600 font-mono">{formatPercent(bulk?.job_success_rate)}</span>
                  </div>
                </div>
              </div>

              <div className="md:col-span-2 rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
                <h3 className="text-sm font-bold text-slate-900 mb-1">Job Status Distribution</h3>
                <p className="text-xs text-slate-400 mb-4">Pipeline completion status across batch jobs</p>

                <div className="space-y-3">
                  {bulk?.status_distribution &&
                    Object.entries(bulk.status_distribution).map(([st, cnt]) => (
                      <div key={st} className="flex items-center justify-between text-xs border-b border-slate-100 pb-1.5">
                        <span className="font-semibold text-slate-700">{st.replace(/_/g, " ")}</span>
                        <span className="font-bold text-slate-900 font-mono">{cnt} jobs</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
