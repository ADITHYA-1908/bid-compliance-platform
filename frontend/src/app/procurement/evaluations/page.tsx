"use client";

import React, { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  BidEvaluationSummaryResponse,
  CategoryScoreItem,
} from "@/types/evaluation";
import {
  getProcurementBidEvaluationSummary,
  refreshProcurementBidEvaluation,
  regenerateProcurementBidAIEvaluation,
} from "@/lib/api/evaluation";
import { askProcurementBidAIQuestion } from "@/lib/api/ai";
import { AIQuestionResponse } from "@/types/ai";
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  MinusCircle,
  RefreshCw,
  Search,
  FileText,
  AlertOctagon,
  Eye,
  Info,
  Layers,
  Award,
  Sliders,
  Activity,
  AlertCircle,
  Sparkles,
  Bot,
  MessageSquare,
  Send,
  CornerDownRight,
  HelpCircle,
  Check,
  Zap,
} from "lucide-react";

export default function ProcurementEvaluationsPage() {
  const [bidIdInput, setBidIdInput] = useState<string>("");
  const [activeBidId, setActiveBidId] = useState<string>("");
  const [evaluation, setEvaluation] = useState<BidEvaluationSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [generatingAI, setGeneratingAI] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "compliance" | "scoring_risk" | "ai_assistant">("summary");

  // Q&A Console state
  const [questionInput, setQuestionInput] = useState<string>("");
  const [isAsking, setIsAsking] = useState<boolean>(false);
  const [qaHistory, setQaHistory] = useState<AIQuestionResponse[]>([]);

  const loadEvaluation = async (id: string) => {
    if (!id.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getProcurementBidEvaluationSummary(id.trim());
      setEvaluation(data);
      setActiveBidId(id.trim());
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Failed to load bid evaluation.");
      setEvaluation(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    if (!activeBidId) return;
    setRefreshing(true);
    try {
      const data = await refreshProcurementBidEvaluation(activeBidId, false);
      setEvaluation(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Failed to refresh score and risk.");
    } finally {
      setRefreshing(false);
    }
  };

  const handleRegenerateAI = async () => {
    if (!activeBidId) return;
    setGeneratingAI(true);
    try {
      const data = await regenerateProcurementBidAIEvaluation(activeBidId);
      setEvaluation(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Failed to regenerate AI analysis.");
    } finally {
      setGeneratingAI(false);
    }
  };

  const handleAskQuestion = async (qText?: string) => {
    const query = qText || questionInput;
    if (!query.trim() || !activeBidId || isAsking) return;

    setIsAsking(true);
    try {
      const resp = await askProcurementBidAIQuestion(activeBidId, query.trim());
      setQaHistory((prev) => [resp, ...prev]);
      if (!qText) setQuestionInput("");
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Failed to get AI answer.");
    } finally {
      setIsAsking(false);
    }
  };

  const getRiskBadge = (level?: string | null) => {
    switch (level?.toUpperCase()) {
      case "LOW":
        return {
          bg: "bg-emerald-50 text-emerald-700 border-emerald-200",
          dot: "bg-emerald-500",
          label: "LOW RISK",
        };
      case "MEDIUM":
        return {
          bg: "bg-amber-50 text-amber-700 border-amber-200",
          dot: "bg-amber-500",
          label: "MEDIUM RISK",
        };
      case "HIGH":
        return {
          bg: "bg-orange-50 text-orange-700 border-orange-200",
          dot: "bg-orange-500",
          label: "HIGH RISK",
        };
      case "CRITICAL":
        return {
          bg: "bg-rose-50 text-rose-700 border-rose-200",
          dot: "bg-rose-500",
          label: "CRITICAL RISK",
        };
      default:
        return {
          bg: "bg-slate-50 text-slate-700 border-slate-200",
          dot: "bg-slate-500",
          label: level || "UNKNOWN",
        };
    }
  };

  const getRecommendationBadge = (rec?: string | null) => {
    switch (rec) {
      case "PROCEED":
        return {
          bg: "bg-emerald-500/10 text-emerald-700 border-emerald-300",
          icon: CheckCircle2,
          label: "PROCEED",
        };
      case "PROCEED_WITH_REVIEW":
        return {
          bg: "bg-amber-500/10 text-amber-700 border-amber-300",
          icon: AlertTriangle,
          label: "PROCEED WITH REVIEW",
        };
      case "REVIEW_REQUIRED":
        return {
          bg: "bg-amber-500/10 text-amber-700 border-amber-300",
          icon: AlertTriangle,
          label: "REVIEW REQUIRED",
        };
      case "DO_NOT_PROCEED_WITHOUT_REVIEW":
        return {
          bg: "bg-rose-500/10 text-rose-700 border-rose-300",
          icon: XCircle,
          label: "DO NOT PROCEED WITHOUT REVIEW",
        };
      case "INSUFFICIENT_EVIDENCE":
        return {
          bg: "bg-slate-500/10 text-slate-700 border-slate-300",
          icon: Clock,
          label: "INSUFFICIENT EVIDENCE",
        };
      default:
        return {
          bg: "bg-slate-100 text-slate-700 border-slate-300",
          icon: Clock,
          label: rec || "PENDING",
        };
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER"]}
      title="Unified Bid Evaluation"
      description="Integrated, auditable evaluation output combining Compliance, Category Scores, Risk Overrides, and Grounded AI Recommendations."
      breadcrumbs={[
        { label: "Procurement", href: "/procurement" },
        { label: "Evaluations" },
      ]}
    >
      <div className="space-y-6 pb-12">
        {/* Bid Lookup & Action Bar */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex-1 flex items-center gap-3">
              <div className="relative flex-1 max-w-md">
                <input
                  type="text"
                  placeholder="Enter Bid ID (UUID)..."
                  value={bidIdInput}
                  onChange={(e) => setBidIdInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && loadEvaluation(bidIdInput)}
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl text-sm border border-slate-300 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all font-mono"
                />
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              </div>
              <button
                onClick={() => loadEvaluation(bidIdInput)}
                disabled={loading || !bidIdInput.trim()}
                className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold transition-colors flex items-center gap-2 shadow-sm"
              >
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
                Load Evaluation
              </button>
            </div>

            {evaluation && (
              <div className="flex items-center gap-2.5">
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors flex items-center gap-1.5 border border-slate-200"
                  title="Recalculate deterministic scoring and risk"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
                  {refreshing ? "Refreshing Score & Risk..." : "Refresh Score & Risk"}
                </button>

                <button
                  onClick={handleRegenerateAI}
                  disabled={generatingAI}
                  className="px-3.5 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold transition-colors flex items-center gap-1.5 border border-indigo-200"
                  title="Re-index vector knowledge and synthesize AI recommendation"
                >
                  <Sparkles className={`w-3.5 h-3.5 ${generatingAI ? "animate-spin" : ""}`} />
                  {generatingAI ? "Analyzing available evidence..." : "Regenerate AI Analysis"}
                </button>
              </div>
            )}
          </div>

          {error && (
            <div className="mt-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Main Evaluation View */}
        {evaluation ? (
          <div className="space-y-6">
            {/* Bid Overview Header & Staleness Banner */}
            <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-6 text-white shadow-md">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold font-mono">{evaluation.bid_number}</h2>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white/10 text-indigo-200 border border-white/20">
                      {evaluation.bid_status}
                    </span>
                    {evaluation.evaluation_complete ? (
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                        <Check className="w-3 h-3" /> Evaluation Complete
                      </span>
                    ) : (
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                        <Clock className="w-3 h-3" /> Provisional Evaluation
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-indigo-200/80 mt-1">
                    Tender: <strong className="text-white">{evaluation.tender_number}</strong> — {evaluation.tender_title}
                  </p>
                  <p className="text-xs text-slate-300 mt-0.5">
                    Bidder Organization: <strong className="text-white">{evaluation.bidder_name}</strong>
                  </p>
                </div>

                <div className="text-right">
                  <span className="text-[11px] text-slate-400 block">Generated At (UTC)</span>
                  <span className="text-xs font-mono text-slate-200">
                    {new Date(evaluation.generated_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Stale Components Alert */}
              {evaluation.stale_components && evaluation.stale_components.length > 0 && (
                <div className="mt-4 p-3 rounded-xl bg-amber-500/20 border border-amber-400/40 text-amber-200 text-xs flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-300 shrink-0" />
                    <span>
                      <strong>Upstream State Changed</strong>: The following evaluation components are outdated:{" "}
                      <strong>{evaluation.stale_components.join(", ")}</strong>. Click <em>Refresh Score & Risk</em> or <em>Regenerate AI Analysis</em> to update.
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Top Metric Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {/* Compliance Score */}
              <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-sm flex flex-col justify-between">
                <span className="text-xs font-semibold text-slate-500">Overall Compliance</span>
                <div className="my-2">
                  <span className="text-3xl font-extrabold text-slate-900">
                    {evaluation.score.overall_compliance_score !== null
                      ? `${evaluation.score.overall_compliance_score.toFixed(1)}%`
                      : "N/A"}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-500">
                  <span className="capitalize">{evaluation.score.score_type.toLowerCase()}</span>
                  <span>{evaluation.score.earned_weight.toFixed(1)} / {evaluation.score.eligible_weight.toFixed(1)} pts</span>
                </div>
              </div>

              {/* Adjusted Risk */}
              <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-sm flex flex-col justify-between">
                <span className="text-xs font-semibold text-slate-500">Adjusted Risk Level</span>
                <div className="my-2">
                  {(() => {
                    const badge = getRiskBadge(evaluation.risk.adjusted_risk_level);
                    return (
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${badge.bg}`}>
                        <span className={`w-2 h-2 rounded-full ${badge.dot}`} />
                        {badge.label}
                      </span>
                    );
                  })()}
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-500">
                  <span>Score: {evaluation.risk.adjusted_risk_score?.toFixed(1) || "0.0"}/100</span>
                  {evaluation.risk.override_applied && (
                    <span className="text-rose-600 font-semibold">Override Floor</span>
                  )}
                </div>
              </div>

              {/* Mandatory Failures */}
              <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-sm flex flex-col justify-between">
                <span className="text-xs font-semibold text-slate-500">Mandatory Failures</span>
                <div className="my-2">
                  <span className={`text-3xl font-extrabold ${evaluation.compliance.mandatory_failures_count > 0 ? "text-rose-600" : "text-slate-900"}`}>
                    {evaluation.compliance.mandatory_failures_count}
                  </span>
                </div>
                <span className="text-[11px] text-slate-500">
                  {evaluation.compliance.fail_count} total failed rules
                </span>
              </div>

              {/* Critical Failures */}
              <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-sm flex flex-col justify-between">
                <span className="text-xs font-semibold text-slate-500">Critical Failures</span>
                <div className="my-2">
                  <span className={`text-3xl font-extrabold ${evaluation.compliance.critical_failures_count > 0 ? "text-rose-600" : "text-slate-900"}`}>
                    {evaluation.compliance.critical_failures_count}
                  </span>
                </div>
                <span className="text-[11px] text-slate-500">
                  {evaluation.critical_summary.critical_failure_present ? "Severe defect present" : "Zero critical defects"}
                </span>
              </div>

              {/* Review Items */}
              <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-sm flex flex-col justify-between">
                <span className="text-xs font-semibold text-slate-500">Officer Review Items</span>
                <div className="my-2">
                  <span className={`text-3xl font-extrabold ${evaluation.review_summary.total_review_items > 0 ? "text-amber-600" : "text-slate-900"}`}>
                    {evaluation.review_summary.total_review_items}
                  </span>
                </div>
                <span className="text-[11px] text-slate-500">
                  {evaluation.human_review_required ? "Officer action required" : "No pending review"}
                </span>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex border-b border-slate-200 space-x-8">
              <button
                onClick={() => setActiveTab("summary")}
                className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
                  activeTab === "summary"
                    ? "border-indigo-600 text-indigo-600"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                <Layers className="w-4 h-4" />
                Executive Summary
              </button>

              <button
                onClick={() => setActiveTab("compliance")}
                className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
                  activeTab === "compliance"
                    ? "border-indigo-600 text-indigo-600"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                <CheckCircle2 className="w-4 h-4" />
                Rule Compliance Matrix
              </button>

              <button
                onClick={() => setActiveTab("scoring_risk")}
                className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
                  activeTab === "scoring_risk"
                    ? "border-indigo-600 text-indigo-600"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                <Award className="w-4 h-4" />
                Scoring & Risk Audit
              </button>

              <button
                onClick={() => setActiveTab("ai_assistant")}
                className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
                  activeTab === "ai_assistant"
                    ? "border-indigo-600 text-indigo-600"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                <Sparkles className="w-4 h-4" />
                AI Recommendation & Q&A
              </button>
            </div>

            {/* TAB 1: EXECUTIVE SUMMARY */}
            {activeTab === "summary" && (
              <div className="space-y-6">
                {/* Critical Findings Panel */}
                {evaluation.critical_summary.critical_failure_present && (
                  <div className="p-5 rounded-2xl bg-rose-50/60 border border-rose-200 space-y-3">
                    <div className="flex items-center gap-2 text-rose-900 font-bold text-sm">
                      <AlertOctagon className="w-5 h-5 text-rose-600" />
                      <h3>Critical Findings & Risk Escalations</h3>
                    </div>
                    <p className="text-xs text-rose-800">
                      The following critical criteria failed authoritative verification or triggered mandatory risk escalation floors:
                    </p>
                    <div className="space-y-2">
                      {evaluation.critical_summary.critical_findings.map((item, idx) => (
                        <div key={idx} className="p-3 bg-white rounded-xl border border-rose-200 flex flex-col md:flex-row md:items-center justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-rose-100 text-rose-800">
                                {item.requirement_code}
                              </span>
                              <span className="text-xs font-bold text-slate-900">{item.requirement_name}</span>
                              <span className="text-[10px] text-slate-500 uppercase">({item.category})</span>
                            </div>
                            <p className="text-xs text-slate-600 mt-1">{item.finding_reason}</p>
                          </div>
                          {item.risk_override && (
                            <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-600 text-white shrink-0">
                              {item.risk_override}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Category Scores Overview Grid */}
                <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <Award className="w-4 h-4 text-indigo-600" />
                      Category Compliance Scores ({Object.keys(evaluation.score.category_scores || {}).length})
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
                    {Object.entries(evaluation.score.category_scores || {}).map(([catKey, catData]: [string, any]) => {
                      const scoreVal = catData?.score !== undefined ? catData.score : null;
                      return (
                        <div key={catKey} className="p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/70 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-800 capitalize">
                              {catKey.toLowerCase().replace(/_/g, " ")}
                            </span>
                            <span className="text-xs font-extrabold text-slate-900 font-mono">
                              {scoreVal !== null ? `${scoreVal.toFixed(1)}%` : "N/A"}
                            </span>
                          </div>
                          <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                            <div
                              className={`h-2 rounded-full transition-all ${
                                scoreVal === null
                                  ? "bg-slate-300"
                                  : scoreVal >= 80
                                  ? "bg-emerald-500"
                                  : scoreVal >= 50
                                  ? "bg-amber-500"
                                  : "bg-rose-500"
                              }`}
                              style={{ width: `${scoreVal || 0}%` }}
                            />
                          </div>
                          <div className="flex items-center justify-between text-[10px] text-slate-500">
                            <span>{catData?.passed_count || 0} passed / {catData?.rule_count || 0} rules</span>
                            <span>{catData?.earned_weight?.toFixed(1) || 0}/{catData?.eligible_weight?.toFixed(1) || 0} pts</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Review Items Summary */}
                {evaluation.review_summary.review_reasons && evaluation.review_summary.review_reasons.length > 0 && (
                  <div className="p-5 rounded-2xl bg-amber-50/60 border border-amber-200 space-y-3">
                    <div className="flex items-center gap-2 text-amber-900 font-bold text-sm">
                      <AlertTriangle className="w-5 h-5 text-amber-600" />
                      <h3>Human Review Required ({evaluation.review_summary.review_reasons.length} Items)</h3>
                    </div>
                    <ul className="space-y-1.5 text-xs text-amber-950">
                      {evaluation.review_summary.review_reasons.map((reason, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-amber-600 font-bold">•</span>
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: RULE COMPLIANCE MATRIX */}
            {activeTab === "compliance" && (
              <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900">
                    Active Tender Requirements & Verified Outcomes ({evaluation.compliance.total_requirements})
                  </h3>
                  <span className="text-xs text-slate-500 font-mono">
                    Evaluation Version: v{evaluation.compliance.evaluation_version}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-xs text-slate-600 py-2 border-y border-slate-100">
                  <div>PASS: <strong className="text-emerald-700">{evaluation.compliance.pass_count}</strong></div>
                  <div>FAIL: <strong className="text-rose-700">{evaluation.compliance.fail_count}</strong></div>
                  <div>REVIEW: <strong className="text-amber-700">{evaluation.compliance.review_count}</strong></div>
                  <div>PENDING: <strong className="text-blue-700">{evaluation.compliance.pending_count}</strong></div>
                  <div>N/A: <strong className="text-slate-500">{evaluation.compliance.not_applicable_count}</strong></div>
                  <div>Mandatory Failures: <strong className="text-rose-700">{evaluation.compliance.mandatory_failures_count}</strong></div>
                </div>

                <p className="text-xs text-slate-500 italic">
                  To view rule-level parameter evaluations or trigger re-evaluations, use the Compliance Workspace under Procurement &gt; Compliance.
                </p>
              </div>
            )}

            {/* TAB 3: SCORING & RISK AUDIT */}
            {activeTab === "scoring_risk" && (
              <div className="space-y-6">
                {/* Scoring Details */}
                <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <Award className="w-4 h-4 text-indigo-600" />
                      Deterministic Scoring Formula & Weight Contributions
                    </h3>
                    <span className="text-xs text-slate-500 font-mono">
                      Formula: {evaluation.score.formula_version} | Version: v{evaluation.score.scoring_version}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <span className="text-slate-500 block">Total Earned Weight</span>
                      <strong className="text-sm text-slate-900">{evaluation.score.earned_weight.toFixed(4)} pts</strong>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <span className="text-slate-500 block">Total Eligible Weight</span>
                      <strong className="text-sm text-slate-900">{evaluation.score.eligible_weight.toFixed(4)} pts</strong>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <span className="text-slate-500 block">Scoring Completion Status</span>
                      <strong className={`text-sm ${evaluation.score.scoring_complete ? "text-emerald-700" : "text-amber-700"}`}>
                        {evaluation.score.scoring_complete ? "Complete" : "Provisional (Pending Rules)"}
                      </strong>
                    </div>
                  </div>
                </div>

                {/* Risk Breakdown & Applied Overrides */}
                <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <Activity className="w-4 h-4 text-indigo-600" />
                      Deterministic Risk Model & Override Adjustments
                    </h3>
                    <span className="text-xs text-slate-500 font-mono">
                      Risk Formula: {evaluation.risk.risk_formula_version} | Override Formula: {evaluation.risk.override_formula_version}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Base vs Adjusted Comparison */}
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                      <h4 className="text-xs font-bold text-slate-700">Base Risk Assessment (Part 7C)</h4>
                      <div className="flex items-center gap-3">
                        <span className="text-2xl font-extrabold text-slate-900">
                          {evaluation.risk.base_risk_score?.toFixed(1) || "0.0"}
                        </span>
                        <span className="text-xs font-semibold text-slate-600 uppercase">
                          ({evaluation.risk.base_risk_level || "LOW"})
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500">
                        Calculated purely from compliance deficit, failure rates, and uncertainty factors.
                      </p>
                    </div>

                    {/* Adjusted Risk */}
                    <div className="p-4 rounded-xl bg-indigo-50/50 border border-indigo-200 space-y-2">
                      <h4 className="text-xs font-bold text-indigo-900">Adjusted Risk Level (Part 7D Floor)</h4>
                      <div className="flex items-center gap-3">
                        <span className="text-2xl font-extrabold text-indigo-950">
                          {evaluation.risk.adjusted_risk_score?.toFixed(1) || "0.0"}
                        </span>
                        {(() => {
                          const badge = getRiskBadge(evaluation.risk.adjusted_risk_level);
                          return (
                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${badge.bg}`}>
                              {badge.label}
                            </span>
                          );
                        })()}
                      </div>
                      <p className="text-[11px] text-indigo-900/80">
                        {evaluation.risk.override_applied
                          ? "Adjusted upward due to one or more critical failure risk floors."
                          : "No critical overrides triggered. Adjusted risk equals base risk."}
                      </p>
                    </div>
                  </div>

                  {/* Applied Overrides Table */}
                  {evaluation.risk.applied_overrides && evaluation.risk.applied_overrides.length > 0 && (
                    <div className="space-y-2 mt-4">
                      <h4 className="text-xs font-bold text-slate-800">Applied Risk Floors ({evaluation.risk.applied_overrides.length})</h4>
                      <div className="space-y-1.5">
                        {evaluation.risk.applied_overrides.map((ov, idx) => (
                          <div key={idx} className="p-3 bg-rose-50/50 rounded-xl border border-rose-200 text-xs flex flex-col md:flex-row md:items-center justify-between gap-2">
                            <div>
                              <strong className="text-rose-900">{ov.override_type}</strong>
                              <p className="text-slate-600 text-[11px]">{ov.reason}</p>
                            </div>
                            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-600 text-white shrink-0">
                              Floor: {ov.risk_floor} ({ov.target_level})
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 4: AI ASSISTANT & Q&A */}
            {activeTab === "ai_assistant" && (
              <div className="space-y-6">
                {/* AI Recommendation Card */}
                <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm space-y-4">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Bot className="w-5 h-5 text-indigo-600" />
                      <h3 className="text-sm font-bold text-slate-900">AI-Assisted Evaluation Recommendation</h3>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      {evaluation.ai_recommendation.status === "CURRENT" ? (
                        <span className="px-2 py-0.5 rounded-full font-semibold bg-emerald-100 text-emerald-800">
                          Current
                        </span>
                      ) : evaluation.ai_recommendation.status === "STALE" ? (
                        <span className="px-2 py-0.5 rounded-full font-semibold bg-amber-100 text-amber-800">
                          Stale
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full font-semibold bg-slate-100 text-slate-700">
                          {evaluation.ai_recommendation.status}
                        </span>
                      )}
                      <span className="text-slate-500">
                        Provider: {evaluation.ai_recommendation.model_provider || "System"} ({evaluation.ai_recommendation.confidence_label || "HIGH"} confidence)
                      </span>
                    </div>
                  </div>

                  {evaluation.ai_recommendation.recommendation ? (
                    <div className="space-y-4">
                      {/* Recommendation Badge & Reason */}
                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                        {(() => {
                          const badge = getRecommendationBadge(evaluation.ai_recommendation.recommendation);
                          const Icon = badge.icon;
                          return (
                            <div className="flex items-center gap-2">
                              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${badge.bg}`}>
                                <Icon className="w-4 h-4" />
                                {badge.label}
                              </span>
                            </div>
                          );
                        })()}
                        <p className="text-xs text-slate-800 leading-relaxed">
                          {evaluation.ai_recommendation.recommendation_reason || evaluation.ai_recommendation.summary}
                        </p>
                      </div>

                      {/* Strengths and Concerns */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Strengths */}
                        <div className="p-4 rounded-xl bg-emerald-50/50 border border-emerald-200 space-y-2">
                          <h4 className="text-xs font-bold text-emerald-900 uppercase tracking-wider flex items-center gap-1.5">
                            <Check className="w-4 h-4 text-emerald-700" />
                            Verified Strengths ({evaluation.ai_recommendation.strengths?.length || 0})
                          </h4>
                          <ul className="space-y-1 text-xs text-emerald-950">
                            {evaluation.ai_recommendation.strengths?.map((str, idx) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <span className="text-emerald-600 font-bold">•</span>
                                <span>{str}</span>
                              </li>
                            ))}
                          </ul>
                        </div>

                        {/* Concerns */}
                        <div className="p-4 rounded-xl bg-rose-50/50 border border-rose-200 space-y-2">
                          <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wider flex items-center gap-1.5">
                            <AlertCircle className="w-4 h-4 text-rose-700" />
                            Verified Concerns ({evaluation.ai_recommendation.concerns?.length || 0})
                          </h4>
                          <ul className="space-y-1 text-xs text-rose-950">
                            {evaluation.ai_recommendation.concerns?.map((con, idx) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <span className="text-rose-600 font-bold">•</span>
                                <span>{con}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      {/* Evidence Citations */}
                      {evaluation.ai_recommendation.evidence_refs && evaluation.ai_recommendation.evidence_refs.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                            <FileText className="w-3.5 h-3.5 text-indigo-600" />
                            Grounded Citations ({evaluation.ai_recommendation.evidence_refs.length})
                          </h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {evaluation.ai_recommendation.evidence_refs.map((ref, idx) => (
                              <div key={idx} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                                <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
                                  <span className="font-bold text-slate-700">{ref.title}</span>
                                  <span className="font-mono text-[10px]">{ref.source_type}</span>
                                </div>
                                <p className="text-slate-600 text-[11px] italic">"{ref.summary}"</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-300">
                      <Sparkles className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                      <p className="text-xs text-slate-600 mb-3">No AI recommendation generated yet.</p>
                      <button
                        onClick={handleRegenerateAI}
                        disabled={generatingAI}
                        className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold shadow-sm"
                      >
                        {generatingAI ? "Analyzing..." : "Generate AI Recommendation"}
                      </button>
                    </div>
                  )}
                </div>

                {/* Interactive Q&A Console */}
                <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm space-y-4">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-indigo-600" />
                    <h3 className="text-sm font-bold text-slate-900">Ask AI Assistant About This Bid</h3>
                  </div>

                  {/* Suggested Prompts */}
                  <div className="flex flex-wrap gap-2">
                    {[
                      "Why did this bid fail local content?",
                      "Explain the financial turnover verification",
                      "Check active blacklisting and debarment status",
                      "Show all items requiring officer review",
                    ].map((prompt, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleAskQuestion(prompt)}
                        disabled={isAsking}
                        className="px-3 py-1 rounded-full text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors border border-slate-200 text-left"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>

                  {/* Input Box */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Ask a question about this bid's compliance, verification, or risk..."
                      value={questionInput}
                      onChange={(e) => setQuestionInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAskQuestion()}
                      className="flex-1 px-4 py-2.5 rounded-xl text-xs border border-slate-300 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    <button
                      onClick={() => handleAskQuestion()}
                      disabled={isAsking || !questionInput.trim()}
                      className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1.5"
                    >
                      {isAsking ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                      Ask
                    </button>
                  </div>

                  {/* Q&A History */}
                  {qaHistory.length > 0 && (
                    <div className="space-y-3 pt-2">
                      {qaHistory.map((item, idx) => (
                        <div key={idx} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                          <div className="flex items-start gap-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800">Q</span>
                            <strong className="text-xs text-slate-900">{item.question}</strong>
                          </div>
                          <div className="flex items-start gap-2 pl-4 border-l-2 border-indigo-400">
                            <p className="text-xs text-slate-800 leading-relaxed">{item.answer}</p>
                          </div>
                          {item.evidence_refs && item.evidence_refs.length > 0 && (
                            <div className="pl-4 pt-1 flex flex-wrap gap-1.5">
                              {item.evidence_refs.map((ref, rIdx) => (
                                <span key={rIdx} className="px-2 py-0.5 rounded text-[10px] bg-slate-200 text-slate-700">
                                  {ref.title}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Bottom Procurement Decision Boundary Banner (Part 8 Placeholder) */}
            <div className="p-4 rounded-2xl bg-slate-900 text-white flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-sm">
              <div className="flex items-center gap-3">
                <ShieldAlert className="w-5 h-5 text-indigo-400 shrink-0" />
                <div>
                  <span className="text-xs font-bold block">Final Procurement Decision</span>
                  <span className="text-[11px] text-slate-300">
                    Decision Status: <strong className="text-indigo-300 font-mono">{evaluation.final_decision_status}</strong>. Formal qualification or disqualification is executed by authorized officers in Part 8.
                  </span>
                </div>
              </div>
              <span className="text-[11px] text-slate-400 italic">
                Advisory only — AI never makes final decisions
              </span>
            </div>
          </div>
        ) : !loading && (
          <div className="bg-white rounded-2xl border border-slate-200/80 p-12 text-center shadow-sm space-y-3">
            <Layers className="w-12 h-12 text-slate-400 mx-auto" />
            <h3 className="text-base font-bold text-slate-900">No Bid Evaluation Loaded</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Enter a valid submitted Bid ID above to view the unified evaluation summary combining compliance findings, scoring contributions, risk overrides, and AI recommendations.
            </p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
