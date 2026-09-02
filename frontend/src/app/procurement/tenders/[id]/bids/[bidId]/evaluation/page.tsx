"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
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
  BidDecision,
  BidDecisionHistoryItem,
  BidDecisionStatus,
  DisqualificationReasonCategory,
  RecordBidDecisionRequest,
} from "@/types/bid_decision";
import {
  getBidDecision,
  getBidDecisionHistory,
  recordBidDecision,
} from "@/lib/api/bid_decision";
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
  X,
  Zap,
  ArrowLeft,
  ChevronRight,
  Building2,
  ExternalLink,
} from "lucide-react";

export default function BidDetailEvaluationPage() {
  const params = useParams();
  const router = useRouter();
  const tenderId = params?.id as string;
  const bidId = params?.bidId as string;

  const [evaluation, setEvaluation] = useState<BidEvaluationSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [generatingAI, setGeneratingAI] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "compliance" | "scoring_risk" | "ai_assistant">("summary");

  // Q&A Console state
  const [questionInput, setQuestionInput] = useState<string>("");
  const [isAsking, setIsAsking] = useState<boolean>(false);
  const [qaHistory, setQaHistory] = useState<AIQuestionResponse[]>([]);

  // Part 8D: Final Human Decision State
  const [decisionData, setDecisionData] = useState<BidDecision | null>(null);
  const [decisionHistory, setDecisionHistory] = useState<BidDecisionHistoryItem[]>([]);
  const [loadingDecision, setLoadingDecision] = useState<boolean>(false);
  const [showDecisionModal, setShowDecisionModal] = useState<boolean>(false);
  const [selectedDecisionOutcome, setSelectedDecisionOutcome] = useState<BidDecisionStatus | null>(null);
  const [decisionReason, setDecisionReason] = useState<string>("");
  const [decisionSummary, setDecisionSummary] = useState<string>("");
  const [decisionCategory, setDecisionCategory] = useState<DisqualificationReasonCategory | "">("");
  const [submittingDecision, setSubmittingDecision] = useState<boolean>(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [showHistoryDrawer, setShowHistoryDrawer] = useState<boolean>(false);

  const loadDecision = async () => {
    if (!tenderId || !bidId) return;
    setLoadingDecision(true);
    try {
      const [dec, hist] = await Promise.all([
        getBidDecision(tenderId, bidId),
        getBidDecisionHistory(tenderId, bidId),
      ]);
      setDecisionData(dec);
      setDecisionHistory(hist);
    } catch (err: any) {
      console.warn("Failed to load decision data:", err);
    } finally {
      setLoadingDecision(false);
    }
  };

  const loadEvaluation = async () => {
    if (!bidId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getProcurementBidEvaluationSummary(bidId);
      setEvaluation(data);
      if (tenderId) {
        loadDecision();
      }
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err.message ||
          "Failed to load bid evaluation summary."
      );
      setEvaluation(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvaluation();
  }, [bidId, tenderId]);

  const handleOpenDecisionModal = (outcome: BidDecisionStatus) => {
    setSelectedDecisionOutcome(outcome);
    setDecisionReason("");
    setDecisionSummary("");
    setDecisionCategory("");
    setDecisionError(null);
    setShowDecisionModal(true);
  };

  const handleSubmitDecision = async () => {
    if (!tenderId || !bidId || !selectedDecisionOutcome) return;
    if (decisionReason.trim().length < 10) {
      setDecisionError("A factual justification of at least 10 characters is required.");
      return;
    }

    setSubmittingDecision(true);
    setDecisionError(null);
    try {
      const payload: RecordBidDecisionRequest = {
        decision: selectedDecisionOutcome,
        reason: decisionReason.trim(),
        decision_summary: decisionSummary.trim() || undefined,
        category: (selectedDecisionOutcome === "DISQUALIFIED" && decisionCategory) ? (decisionCategory as DisqualificationReasonCategory) : undefined,
      };

      const updatedDec = await recordBidDecision(tenderId, bidId, payload);
      setDecisionData(updatedDec);
      setShowDecisionModal(false);
      // Reload history and evaluation
      const hist = await getBidDecisionHistory(tenderId, bidId);
      setDecisionHistory(hist);
      const evalData = await getProcurementBidEvaluationSummary(bidId);
      setEvaluation(evalData);
    } catch (err: any) {
      setDecisionError(
        err?.response?.data?.detail ||
          err.message ||
          "Failed to record bid qualification decision."
      );
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleRefresh = async () => {
    if (!bidId) return;
    setRefreshing(true);
    try {
      const data = await refreshProcurementBidEvaluation(bidId, false);
      setEvaluation(data);
      if (tenderId) {
        loadDecision();
      }
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err.message ||
          "Failed to refresh score and risk."
      );
    } finally {
      setRefreshing(false);
    }
  };

  const handleRegenerateAI = async () => {
    if (!bidId) return;
    setGeneratingAI(true);
    try {
      const data = await regenerateProcurementBidAIEvaluation(bidId);
      setEvaluation(data);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err.message ||
          "Failed to regenerate AI analysis."
      );
    } finally {
      setGeneratingAI(false);
    }
  };

  const handleAskQuestion = async (qText?: string) => {
    const query = (qText || questionInput).trim();
    if (!query || !bidId) return;

    setIsAsking(true);
    try {
      const resp = await askProcurementBidAIQuestion(bidId, query);
      setQaHistory((prev) => [resp, ...prev]);
      if (!qText) setQuestionInput("");
    } catch (err: any) {
      alert(
        err?.response?.data?.detail ||
          err.message ||
          "Failed to retrieve grounded AI answer."
      );
    } finally {
      setIsAsking(false);
    }
  };

  const getRiskBadge = (level?: string | null, score?: number | null) => {
    if (!level) return <span className="text-slate-400 font-mono">—</span>;
    const scoreStr = score !== null && score !== undefined ? ` (${score.toFixed(1)})` : "";
    switch (level.toUpperCase()) {
      case "LOW":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-800 border border-emerald-200">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
            LOW{scoreStr}
          </span>
        );
      case "MEDIUM":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-800 border border-blue-200">
            <ShieldCheck className="h-3.5 w-3.5 text-blue-600" />
            MEDIUM{scoreStr}
          </span>
        );
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-800 border border-amber-200">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
            HIGH{scoreStr}
          </span>
        );
      case "CRITICAL":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2.5 py-1 text-xs font-bold text-rose-800 border border-rose-200">
            <ShieldAlert className="h-3.5 w-3.5 text-rose-600" />
            CRITICAL{scoreStr}
          </span>
        );
      default:
        return <span className="text-slate-700 font-mono text-xs">{level}</span>;
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Unified Bid Evaluation Dossier"
      description="Inspect deterministic compliance, category scoring, base & adjusted risk overrides, and grounded AI insights."
      breadcrumbs={[
        { label: "Procurement Portal", href: "/procurement" },
        { label: "Tenders", href: "/procurement/tenders" },
        { label: evaluation?.tender_number || "Tender", href: `/procurement/tenders/${tenderId}/evaluation` },
        { label: evaluation?.bidder_name || "Bid Evaluation" },
      ]}
    >
      <div className="space-y-6">
        {/* Navigation & Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <Link
            href={`/procurement/tenders/${tenderId}/evaluation`}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-purple-900 hover:text-purple-700 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Tender Bid Evaluation Matrix
          </Link>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={refreshing || loading}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors shadow-xs disabled:opacity-50"
              title="Recalculates deterministic score & risk without calling LLMs"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin text-purple-600" : ""}`} />
              Refresh Score & Risk
            </button>
            <button
              onClick={handleRegenerateAI}
              disabled={generatingAI || loading}
              className="inline-flex items-center gap-1.5 rounded-md bg-purple-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-purple-800 transition-colors shadow-xs disabled:opacity-50"
              title="Forces fresh knowledge indexing and AI recommendation generation"
            >
              <Sparkles className={`h-3.5 w-3.5 ${generatingAI ? "animate-spin text-purple-200" : ""}`} />
              Regenerate AI Analysis
            </button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
            <div className="flex-1 text-xs text-red-800">
              <p className="font-bold">Evaluation Dossier Error</p>
              <p className="mt-0.5">{error}</p>
            </div>
            <button
              onClick={loadEvaluation}
              className="text-xs font-semibold text-red-700 underline hover:text-red-900"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-slate-400">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto text-purple-600 mb-3" />
            <p className="text-sm font-semibold text-slate-700">Loading comprehensive evaluation dossier...</p>
            <p className="text-xs text-slate-400 mt-1">Aggregating compliance rules, scoring matrices, and risk features</p>
          </div>
        ) : evaluation ? (
          <>
            {/* Bid Summary Header Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2 mb-1.5">
                    <span className="font-mono text-xs font-bold text-purple-900 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                      {evaluation.bid_number}
                    </span>
                    <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 border border-slate-200">
                      {evaluation.bid_status}
                    </span>
                    {evaluation.evaluation_complete ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 border border-emerald-200">
                        <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                        Deterministic Evaluation Complete
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-800 border border-indigo-200">
                        <Clock className="h-3 w-3 text-indigo-600" />
                        Evaluation Incomplete / Pending Checks
                      </span>
                    )}
                    {evaluation.human_review_required && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-bold text-amber-800 border border-amber-200">
                        <AlertCircle className="h-3 w-3 text-amber-600" />
                        Human Review Required
                      </span>
                    )}
                  </div>

                  <h2 className="text-xl font-bold text-slate-900">
                    {evaluation.bidder_name}
                  </h2>
                  <p className="text-xs text-slate-500 mt-1">
                    Tender: <span className="font-semibold text-slate-700">{evaluation.tender_title}</span> • Ref: <span className="font-mono text-slate-700">{evaluation.tender_number}</span>
                  </p>
                </div>

                <div className="text-right text-xs text-slate-500">
                  <p>Evaluated At: <span className="font-mono text-slate-700">{new Date(evaluation.generated_at).toLocaleString()}</span></p>
                  <p className="mt-0.5">Decision Status: <span className="font-bold text-slate-800 font-mono">{evaluation.final_decision_status}</span></p>
                </div>
              </div>
            </div>

            {/* Staleness Alerts if any */}
            {evaluation.stale_components && evaluation.stale_components.length > 0 && (
              <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                <div className="flex-1 text-xs text-amber-900">
                  <p className="font-bold">Evaluation Invalidation Detected</p>
                  <p className="mt-0.5">
                    Upstream data changes have invalidated: <span className="font-mono font-bold text-amber-950">{evaluation.stale_components.join(", ")}</span>.
                    Click &quot;Refresh Score &amp; Risk&quot; or &quot;Regenerate AI Analysis&quot; to bring evaluations current.
                  </p>
                </div>
              </div>
            )}

            {/* Top KPI Metric Cards */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
              {/* Compliance Score */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Compliance Score
                </span>
                <div className="mt-2 flex items-baseline gap-1">
                  <span
                    className={`text-2xl font-bold font-mono ${
                      (evaluation.score.overall_compliance_score ?? 0) >= 80
                        ? "text-emerald-700"
                        : (evaluation.score.overall_compliance_score ?? 0) >= 50
                        ? "text-amber-700"
                        : "text-rose-700"
                    }`}
                  >
                    {evaluation.score.overall_compliance_score !== null
                      ? `${evaluation.score.overall_compliance_score.toFixed(1)}%`
                      : "—"}
                  </span>
                  {evaluation.score.score_type === "PROVISIONAL" && (
                    <span className="text-[10px] font-semibold text-indigo-600">Prov.</span>
                  )}
                </div>
                <p className="mt-1 text-[11px] text-slate-500">
                  {evaluation.score.earned_weight.toFixed(1)} / {evaluation.score.eligible_weight.toFixed(1)} weight
                </p>
              </div>

              {/* Adjusted Risk */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Adjusted Risk
                </span>
                <div className="mt-2">
                  {getRiskBadge(
                    evaluation.risk.adjusted_risk_level || evaluation.risk.base_risk_level,
                    evaluation.risk.adjusted_risk_score ?? evaluation.risk.base_risk_score
                  )}
                </div>
                <p className="mt-1 text-[11px] text-slate-500">
                  Base: {evaluation.risk.base_risk_score !== null ? evaluation.risk.base_risk_score.toFixed(1) : "—"} {evaluation.risk.override_applied && "(Override)"}
                </p>
              </div>

              {/* Mandatory Failures */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Mandatory Failures
                </span>
                <p className={`mt-2 text-2xl font-bold font-mono ${
                  evaluation.compliance.mandatory_failures_count > 0 ? "text-rose-600" : "text-slate-900"
                }`}>
                  {evaluation.compliance.mandatory_failures_count}
                </p>
                <p className="mt-1 text-[11px] text-slate-500">Of {evaluation.compliance.total_requirements} total rules</p>
              </div>

              {/* Critical Defects */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Critical Defects
                </span>
                <p className={`mt-2 text-2xl font-bold font-mono ${
                  evaluation.critical_summary.critical_failure_present || evaluation.critical_summary.critical_override_applied
                    ? "text-rose-600"
                    : "text-slate-900"
                }`}>
                  {evaluation.critical_summary.critical_failure_count + (evaluation.critical_summary.critical_override_applied ? 1 : 0)}
                </p>
                <p className="mt-1 text-[11px] text-slate-500">Trigger critical floors</p>
              </div>

              {/* Review Items */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Review Items
                </span>
                <p className={`mt-2 text-2xl font-bold font-mono ${
                  evaluation.compliance.review_count > 0 ? "text-amber-700" : "text-slate-900"
                }`}>
                  {evaluation.compliance.review_count}
                </p>
                <p className="mt-1 text-[11px] text-slate-500">Pending officer verification</p>
              </div>

              {/* AI Recommendation */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  AI Recommendation
                </span>
                <div className="mt-2">
                  {evaluation.ai_recommendation.recommendation ? (
                    <span className="inline-flex items-center gap-1 rounded bg-purple-50 px-2 py-0.5 text-xs font-bold text-purple-900 border border-purple-200">
                      <Sparkles className="h-3 w-3 text-purple-600" />
                      {evaluation.ai_recommendation.recommendation}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-400 italic">Not Generated</span>
                  )}
                </div>
                <p className="mt-1 text-[11px] text-slate-500">Status: {evaluation.ai_recommendation.status}</p>
              </div>
            </div>

            {/* Tab Navigation */}
            <div className="border-b border-slate-200 flex items-center gap-4 text-xs font-semibold">
              <button
                onClick={() => setActiveTab("summary")}
                className={`pb-3 transition-colors border-b-2 ${
                  activeTab === "summary"
                    ? "border-purple-900 text-purple-900 font-bold"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                Executive Summary &amp; Critical Findings
              </button>
              <button
                onClick={() => setActiveTab("scoring_risk")}
                className={`pb-3 transition-colors border-b-2 ${
                  activeTab === "scoring_risk"
                    ? "border-purple-900 text-purple-900 font-bold"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                Category Scores &amp; Risk Vectors
              </button>
              <button
                onClick={() => setActiveTab("compliance")}
                className={`pb-3 transition-colors border-b-2 ${
                  activeTab === "compliance"
                    ? "border-purple-900 text-purple-900 font-bold"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                Rule-Level Compliance Breakdown
              </button>
              <button
                onClick={() => setActiveTab("ai_assistant")}
                className={`pb-3 transition-colors border-b-2 flex items-center gap-1.5 ${
                  activeTab === "ai_assistant"
                    ? "border-purple-900 text-purple-900 font-bold"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                <Sparkles className="h-3.5 w-3.5 text-purple-600" />
                AI Analysis &amp; Grounded Q&amp;A
              </button>
            </div>

            {/* TAB 1: Executive Summary & Critical Findings */}
            {activeTab === "summary" && (
              <div className="space-y-6">
                {/* Critical Findings Panel */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-4">
                    <ShieldAlert className="h-4 w-4 text-rose-600" />
                    Critical Defects &amp; Risk Overrides Summary
                  </h3>

                  {evaluation.critical_summary.critical_findings.length === 0 && !evaluation.critical_summary.critical_override_applied ? (
                    <div className="rounded-lg bg-emerald-50/60 border border-emerald-200 p-4 flex items-center gap-3">
                      <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
                      <p className="text-xs text-emerald-900 font-medium">
                        No critical defects detected in the current evaluation. Bid is clear on active blacklisting, critical OEM mandates, and identity checks.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {evaluation.critical_summary.critical_findings.map((f, i) => (
                        <div key={i} className="rounded-lg border border-rose-200 bg-rose-50/50 p-4 space-y-1.5">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-mono font-bold text-rose-900">{f.requirement_code}</span>
                            <span className="font-semibold text-rose-800 bg-rose-100 px-2 py-0.5 rounded">
                              {f.compliance_status}
                            </span>
                          </div>
                          <p className="text-xs font-bold text-slate-900">{f.requirement_name}</p>
                          <p className="text-xs text-slate-700">{f.finding_reason}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Review Queue Summary */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-4">
                    <AlertCircle className="h-4 w-4 text-amber-600" />
                    Items Requiring Human Officer Inspection
                  </h3>

                  {evaluation.review_summary.review_reasons.length === 0 ? (
                    <div className="rounded-lg bg-slate-50 border border-slate-200 p-4 flex items-center gap-3">
                      <Check className="h-5 w-5 text-slate-500 shrink-0" />
                      <p className="text-xs text-slate-600">
                        No current items require human review. All verification claims have resolved deterministically.
                      </p>
                    </div>
                  ) : (
                    <ul className="space-y-2">
                      {evaluation.review_summary.review_reasons.map((r, i) => (
                        <li key={i} className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 text-xs text-amber-900 flex items-start gap-2">
                          <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}

            {/* TAB 2: Scoring & Risk Vectors */}
            {activeTab === "scoring_risk" && (
              <div className="space-y-6">
                {/* Category Scoring Breakdown */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Award className="h-4 w-4 text-purple-900" />
                    Category-Wise Weighted Compliance Scoring
                  </h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(evaluation.score.category_scores || {}).map(([catKey, catVal]: [string, any]) => {
                      const scoreVal = catVal?.category_score ?? catVal?.score;
                      const earned = catVal?.earned_weight ?? 0;
                      const eligible = catVal?.eligible_weight ?? 0;

                      return (
                        <div key={catKey} className="rounded-lg border border-slate-200 bg-slate-50/50 p-4 space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-bold text-slate-800 uppercase tracking-wide">{catKey}</span>
                            <span className="font-mono font-bold text-slate-900">
                              {scoreVal !== null && scoreVal !== undefined ? `${Number(scoreVal).toFixed(1)}%` : "N/A"}
                            </span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-slate-200 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-purple-800 transition-all duration-300"
                              style={{ width: `${Math.min(100, Math.max(0, scoreVal || 0))}%` }}
                            />
                          </div>
                          <p className="text-[11px] text-slate-500">
                            Earned: <span className="font-mono font-semibold text-slate-700">{Number(earned).toFixed(1)}</span> / Eligible: <span className="font-mono font-semibold text-slate-700">{Number(eligible).toFixed(1)}</span> weight
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Risk Contributors */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-3">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Activity className="h-4 w-4 text-purple-900" />
                    Deterministic Risk Reasons &amp; Feature Signals
                  </h3>
                  <ul className="space-y-2">
                    {evaluation.risk.summary_reasons.map((r, i) => (
                      <li key={i} className="text-xs text-slate-700 rounded-lg bg-slate-50 p-3 border border-slate-200 flex items-start gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-purple-900 mt-1.5 shrink-0" />
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* TAB 3: Rule-Level Compliance */}
            {activeTab === "compliance" && (
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-purple-900" />
                    Tender Requirement Compliance Matrix
                  </h3>
                  <span className="text-xs text-slate-500">
                    Version: <span className="font-mono font-semibold text-slate-700">v{evaluation.compliance.evaluation_version}</span>
                  </span>
                </div>

                <div className="grid grid-cols-5 gap-3 text-center text-xs">
                  <div className="rounded-lg bg-emerald-50 p-3 border border-emerald-200">
                    <p className="text-[10px] font-bold text-emerald-800 uppercase">PASS</p>
                    <p className="text-xl font-bold font-mono text-emerald-900 mt-1">{evaluation.compliance.pass_count}</p>
                  </div>
                  <div className="rounded-lg bg-rose-50 p-3 border border-rose-200">
                    <p className="text-[10px] font-bold text-rose-800 uppercase">FAIL</p>
                    <p className="text-xl font-bold font-mono text-rose-900 mt-1">{evaluation.compliance.fail_count}</p>
                  </div>
                  <div className="rounded-lg bg-amber-50 p-3 border border-amber-200">
                    <p className="text-[10px] font-bold text-amber-800 uppercase">REVIEW</p>
                    <p className="text-xl font-bold font-mono text-amber-900 mt-1">{evaluation.compliance.review_count}</p>
                  </div>
                  <div className="rounded-lg bg-indigo-50 p-3 border border-indigo-200">
                    <p className="text-[10px] font-bold text-indigo-800 uppercase">PENDING</p>
                    <p className="text-xl font-bold font-mono text-indigo-900 mt-1">{evaluation.compliance.pending_count}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <p className="text-[10px] font-bold text-slate-600 uppercase">N / A</p>
                    <p className="text-xl font-bold font-mono text-slate-700 mt-1">{evaluation.compliance.not_applicable_count}</p>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 4: Grounded AI Assistant & Q&A Console */}
            {activeTab === "ai_assistant" && (
              <div className="space-y-6">
                {/* AI Executive Recommendation */}
                <div className="rounded-xl border border-purple-200 bg-purple-50/40 p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Bot className="h-5 w-5 text-purple-900" />
                      <h3 className="text-base font-bold text-purple-950">
                        AI-Assisted Evaluation Recommendation
                      </h3>
                    </div>
                    <span className="font-mono text-[11px] font-bold bg-white px-2.5 py-1 rounded border border-purple-200 text-purple-900">
                      {evaluation.ai_recommendation.recommendation || "NOT_GENERATED"}
                    </span>
                  </div>

                  {evaluation.ai_recommendation.recommendation_reason && (
                    <p className="text-xs text-slate-800 bg-white p-4 rounded-lg border border-purple-100 leading-relaxed">
                      {evaluation.ai_recommendation.recommendation_reason}
                    </p>
                  )}

                  {/* Strengths & Concerns Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="rounded-lg bg-white p-4 border border-slate-200 space-y-2">
                      <p className="text-xs font-bold text-emerald-800 flex items-center gap-1.5">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        Grounded Strengths ({evaluation.ai_recommendation.strengths.length})
                      </p>
                      <ul className="space-y-1.5 text-xs text-slate-700">
                        {evaluation.ai_recommendation.strengths.map((s, i) => (
                          <li key={i} className="flex items-start gap-1.5">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-600 mt-1.5 shrink-0" />
                            <span>{s}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="rounded-lg bg-white p-4 border border-slate-200 space-y-2">
                      <p className="text-xs font-bold text-rose-800 flex items-center gap-1.5">
                        <AlertTriangle className="h-4 w-4 text-rose-600" />
                        Grounded Concerns ({evaluation.ai_recommendation.concerns.length})
                      </p>
                      <ul className="space-y-1.5 text-xs text-slate-700">
                        {evaluation.ai_recommendation.concerns.map((c, i) => (
                          <li key={i} className="flex items-start gap-1.5">
                            <span className="h-1.5 w-1.5 rounded-full bg-rose-600 mt-1.5 shrink-0" />
                            <span>{c}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>

                {/* Grounded Interactive Q&A Console */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-purple-900" />
                    <h3 className="text-sm font-bold text-slate-900">
                      Grounded Inquiries Console
                    </h3>
                  </div>

                  {/* Suggested Prompts */}
                  <div className="flex flex-wrap gap-2">
                    {[
                      "Why did this bid fail?",
                      "Show critical issues.",
                      "Explain the adjusted risk score.",
                      "Which documents need review?",
                      "Summarize turnover verification.",
                    ].map((prompt, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleAskQuestion(prompt)}
                        disabled={isAsking}
                        className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] text-slate-700 hover:bg-purple-50 hover:border-purple-300 hover:text-purple-900 transition-colors disabled:opacity-50"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>

                  {/* Input form */}
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={questionInput}
                      onChange={(e) => setQuestionInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAskQuestion()}
                      placeholder="Ask any question about this bid's compliance and evidence..."
                      className="flex-1 h-9.5 rounded-md border border-slate-300 bg-white px-3 text-xs text-slate-800 placeholder-slate-400 focus:border-purple-600 focus:outline-hidden focus:ring-1 focus:ring-purple-600"
                    />
                    <button
                      onClick={() => handleAskQuestion()}
                      disabled={isAsking || !questionInput.trim()}
                      className="inline-flex items-center gap-1.5 h-9.5 rounded-md bg-purple-900 px-4 text-xs font-semibold text-white hover:bg-purple-800 transition-colors shadow-xs disabled:opacity-50"
                    >
                      <Send className="h-3.5 w-3.5" />
                      Ask AI
                    </button>
                  </div>

                  {/* Q&A History */}
                  {qaHistory.length > 0 && (
                    <div className="space-y-3 pt-4 border-t border-slate-100">
                      {qaHistory.map((item, index) => (
                        <div key={index} className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 space-y-2 text-xs">
                          <p className="font-bold text-purple-950 flex items-center gap-1.5">
                            <HelpCircle className="h-3.5 w-3.5 text-purple-700" />
                            {item.question}
                          </p>
                          <p className="text-slate-800 leading-relaxed pl-5 bg-white p-3 rounded border border-slate-200">
                            {item.answer}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ============================================================= */}
            {/* Part 8D: Final Human Decision Workflow Panel */}
            {/* ============================================================= */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <Award className="h-5 w-5 text-purple-900" />
                    <h3 className="text-base font-bold text-slate-900">
                      Final Human Evaluation Decision
                    </h3>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Authoritative qualification or disqualification determination recorded by authorized Procurement Officers.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {decisionHistory.length > 0 && (
                    <button
                      onClick={() => setShowHistoryDrawer(!showHistoryDrawer)}
                      className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
                    >
                      <Clock className="h-3.5 w-3.5 text-slate-500" />
                      Decision History ({decisionHistory.length})
                    </button>
                  )}
                </div>
              </div>

              {/* Staleness Banner if applicable */}
              {decisionData?.is_stale && (
                <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <div className="flex-1 text-xs text-amber-900 space-y-1">
                    <p className="font-bold">Prior Decision Requires Reconfirmation</p>
                    <p>
                      {decisionData.stale_reason || "Upstream compliance or verification records were updated after this decision was recorded."}
                    </p>
                    <p className="text-[11px] text-amber-800">
                      The prior decision remains on record, but please review the latest evidence and submit a reconfirmation or updated decision.
                    </p>
                  </div>
                </div>
              )}

              {/* Current Decision Summary Card */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Current Decision Status
                  </span>
                  <div className="mt-1.5">
                    {decisionData?.decision === "QUALIFIED" ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800 border border-emerald-300">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                        QUALIFIED
                      </span>
                    ) : decisionData?.decision === "DISQUALIFIED" ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-100 px-3 py-1 text-xs font-bold text-rose-800 border border-rose-300">
                        <XCircle className="h-3.5 w-3.5 text-rose-600" />
                        DISQUALIFIED
                      </span>
                    ) : decisionData?.decision === "UNDER_REVIEW" ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800 border border-amber-300">
                        <Clock className="h-3.5 w-3.5 text-amber-600" />
                        UNDER REVIEW / DEFERRED
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-200 px-3 py-1 text-xs font-medium text-slate-700">
                        <MinusCircle className="h-3.5 w-3.5 text-slate-500" />
                        NOT DECIDED
                      </span>
                    )}
                  </div>
                </div>

                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Decided By / Identity
                  </span>
                  <p className="mt-1 text-xs font-bold text-slate-800">
                    {decisionData?.decided_by?.full_name || "—"}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {decisionData?.decided_by?.role_name || "Procurement Officer"}
                  </p>
                </div>

                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Timestamp & Version
                  </span>
                  <p className="mt-1 text-xs font-mono font-medium text-slate-800">
                    {decisionData?.decision_version ? `Version ${decisionData.decision_version}` : "v0"}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {decisionData?.decided_at ? new Date(decisionData.decided_at).toLocaleString() : "—"}
                  </p>
                </div>

                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Evaluation Version Link
                  </span>
                  <p className="mt-1 text-xs font-mono text-slate-800">
                    Eval v{decisionData?.snapshot_reference?.evaluation_version ?? 1}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Score: {decisionData?.snapshot_reference?.overall_score !== null && decisionData?.snapshot_reference?.overall_score !== undefined ? `${decisionData.snapshot_reference.overall_score.toFixed(1)}%` : "N/A"}
                  </p>
                </div>
              </div>

              {/* Decision Reason on Record */}
              {decisionData?.decision !== "NOT_DECIDED" && decisionData?.reason && (
                <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-1 text-xs">
                  <span className="font-bold text-slate-700">Recorded Factual Justification:</span>
                  <p className="text-slate-800 italic bg-slate-50 p-3 rounded border border-slate-200 leading-relaxed">
                    &quot;{decisionData.reason}&quot;
                  </p>
                  {decisionData.category && (
                    <p className="text-[11px] text-slate-500 mt-1">
                      Reason Category: <span className="font-semibold text-slate-700">{decisionData.category.replace(/_/g, " ")}</span>
                    </p>
                  )}
                </div>
              )}

              {/* Decision Readiness & Preconditions Card */}
              {decisionData?.readiness && (
                <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                      <ShieldCheck className="h-4 w-4 text-purple-900" />
                      Platform Decision Readiness Safeguards
                    </span>
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold ${
                        decisionData.readiness.can_qualify
                          ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                          : "bg-rose-100 text-rose-800 border border-rose-200"
                      }`}>
                        {decisionData.readiness.can_qualify ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
                        Qualification: {decisionData.readiness.can_qualify ? "Permitted" : "Blocked"}
                      </span>
                    </div>
                  </div>

                  {/* Blocking Reasons if blocked */}
                  {decisionData.readiness.blocking_reasons.length > 0 && (
                    <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-900 space-y-1">
                      <p className="font-bold flex items-center gap-1">
                        <AlertOctagon className="h-3.5 w-3.5 text-rose-600" />
                        Qualification Safeguard Blockers:
                      </p>
                      <ul className="list-disc pl-5 space-y-0.5">
                        {decisionData.readiness.blocking_reasons.map((b, i) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Advisory Warnings */}
                  {decisionData.readiness.warnings.length > 0 && (
                    <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs text-amber-900 space-y-1">
                      <p className="font-bold flex items-center gap-1">
                        <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                        Advisory Warnings &amp; Override Disclaimers:
                      </p>
                      <ul className="list-disc pl-5 space-y-0.5">
                        {decisionData.readiness.warnings.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Action Buttons for Procurement Officer */}
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => handleOpenDecisionModal("QUALIFIED")}
                  disabled={!decisionData?.readiness?.can_qualify}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-600 transition-colors shadow-xs disabled:opacity-40 disabled:cursor-not-allowed"
                  title={!decisionData?.readiness?.can_qualify ? decisionData?.readiness?.blocking_reasons.join("; ") : "Mark bid as qualified to proceed to next stage"}
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Accept &amp; Qualify Bid
                </button>

                <button
                  type="button"
                  onClick={() => handleOpenDecisionModal("DISQUALIFIED")}
                  className="inline-flex items-center gap-2 rounded-lg bg-rose-700 px-4 py-2 text-xs font-bold text-white hover:bg-rose-600 transition-colors shadow-xs"
                >
                  <XCircle className="h-4 w-4" />
                  Disqualify Bid
                </button>

                <button
                  type="button"
                  onClick={() => handleOpenDecisionModal("UNDER_REVIEW")}
                  className="inline-flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-xs font-bold text-amber-800 hover:bg-amber-100 transition-colors shadow-xs"
                >
                  <Clock className="h-4 w-4 text-amber-600" />
                  Keep Under Review / Defer
                </button>
              </div>

              {/* Decision History Collapsible Drawer */}
              {showHistoryDrawer && (
                <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 space-y-3 pt-4">
                  <h4 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <Clock className="h-4 w-4 text-purple-900" />
                    Chronological Decision Version History
                  </h4>
                  <div className="space-y-2">
                    {decisionHistory.map((item) => (
                      <div
                        key={item.id}
                        className={`rounded-lg border p-3 text-xs space-y-1 ${
                          item.is_current
                            ? "bg-white border-purple-300 shadow-xs"
                            : "bg-slate-100/60 border-slate-200 opacity-80"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-slate-800 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                              v{item.decision_version}
                            </span>
                            <span className={`font-bold ${
                              item.decision === "QUALIFIED"
                                ? "text-emerald-800"
                                : item.decision === "DISQUALIFIED"
                                ? "text-rose-800"
                                : "text-amber-800"
                            }`}>
                              {item.decision}
                            </span>
                            {item.is_current && (
                              <span className="rounded bg-purple-100 px-1.5 py-0.2 text-[10px] font-bold text-purple-900">
                                CURRENT
                              </span>
                            )}
                          </div>
                          <span className="text-[11px] text-slate-500 font-mono">
                            {new Date(item.decided_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-slate-700 italic">
                          &quot;{item.reason}&quot;
                        </p>
                        <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                          <span>Decided by: {item.decided_by_name} ({item.decided_by_role})</span>
                          {item.superseded_at && (
                            <span>Superseded: {new Date(item.superseded_at).toLocaleTimeString()}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Decision Submission Modal Dialog */}
            {showDecisionModal && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                    <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                      <Award className="h-5 w-5 text-purple-900" />
                      Record Human Decision: {selectedDecisionOutcome}
                    </h3>
                    <button
                      onClick={() => setShowDecisionModal(false)}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>

                  {decisionError && (
                    <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-800 flex items-start gap-2">
                      <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                      <span>{decisionError}</span>
                    </div>
                  )}

                  {/* Explicit Legal & Scope Notice */}
                  {selectedDecisionOutcome === "QUALIFIED" ? (
                    <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3.5 text-xs text-emerald-900 space-y-1">
                      <p className="font-bold flex items-center gap-1.5 text-emerald-950">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        Qualification Acceptance Notice
                      </p>
                      <p>
                        You are marking this bid as <strong>QUALIFIED</strong>. This indicates the bidder has satisfied required evaluation criteria to proceed to the next procurement stage.
                      </p>
                      <p className="text-[11px] text-emerald-800 font-semibold mt-1">
                        This action does NOT constitute tender award or winner selection.
                      </p>
                    </div>
                  ) : selectedDecisionOutcome === "DISQUALIFIED" ? (
                    <div className="rounded-lg bg-rose-50 border border-rose-200 p-3.5 text-xs text-rose-900 space-y-1">
                      <p className="font-bold flex items-center gap-1.5 text-rose-950">
                        <XCircle className="h-4 w-4 text-rose-600" />
                        Disqualification Notice
                      </p>
                      <p>
                        You are marking this bid as <strong>DISQUALIFIED</strong>. The bidder will be eliminated from further consideration. A detailed factual justification is legally mandatory.
                      </p>
                    </div>
                  ) : (
                    <div className="rounded-lg bg-amber-50 border border-amber-200 p-3.5 text-xs text-amber-900 space-y-1">
                      <p className="font-bold flex items-center gap-1.5 text-amber-950">
                        <Clock className="h-4 w-4 text-amber-600" />
                        Under Review / Deferral Notice
                      </p>
                      <p>
                        The evaluation outcome is deferred pending further evidence inspection or clarification.
                      </p>
                    </div>
                  )}

                  {/* Disqualification Category if applicable */}
                  {selectedDecisionOutcome === "DISQUALIFIED" && (
                    <div className="space-y-1.5">
                      <label className="block text-xs font-bold text-slate-700">
                        Disqualification Reason Category
                      </label>
                      <select
                        value={decisionCategory}
                        onChange={(e) => setDecisionCategory(e.target.value as any)}
                        className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs text-slate-800 focus:border-purple-600 focus:outline-hidden"
                      >
                        <option value="">Select category (optional)</option>
                        <option value="MANDATORY_REQUIREMENT_FAILURE">Mandatory Requirement Failure</option>
                        <option value="CRITICAL_REQUIREMENT_FAILURE">Critical Requirement Failure</option>
                        <option value="DOCUMENT_INSUFFICIENT">Document Insufficient / Inauthentic</option>
                        <option value="REGISTRATION_NON_COMPLIANCE">Statutory Registration Non-Compliance</option>
                        <option value="FINANCIAL_NON_COMPLIANCE">Financial Criteria Non-Compliance</option>
                        <option value="TECHNICAL_NON_COMPLIANCE">Technical Specification Non-Compliance</option>
                        <option value="INTEGRITY_CONCERN">Integrity / Debarment / Exclusion</option>
                        <option value="OTHER">Other Factual Procurement Reason</option>
                      </select>
                    </div>
                  )}

                  {/* Mandatory Reason */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="block text-xs font-bold text-slate-700">
                        Factual Justification / Reason <span className="text-rose-600">*</span>
                      </label>
                      <span className={`text-[11px] font-mono ${decisionReason.trim().length < 10 ? "text-rose-600" : "text-slate-500"}`}>
                        {decisionReason.trim().length}/2000 (min 10)
                      </span>
                    </div>
                    <textarea
                      rows={4}
                      value={decisionReason}
                      onChange={(e) => setDecisionReason(e.target.value)}
                      placeholder="Enter detailed, auditable justification for this qualification decision..."
                      className="w-full rounded-md border border-slate-300 bg-white p-3 text-xs text-slate-800 focus:border-purple-600 focus:outline-hidden focus:ring-1 focus:ring-purple-600"
                    />
                  </div>

                  {/* Brief Summary (optional) */}
                  <div className="space-y-1.5">
                    <label className="block text-xs font-bold text-slate-700">
                      Internal Decision Summary (Optional)
                    </label>
                    <input
                      type="text"
                      value={decisionSummary}
                      onChange={(e) => setDecisionSummary(e.target.value)}
                      placeholder="e.g. All OEM & technical criteria verified"
                      className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs text-slate-800 focus:border-purple-600 focus:outline-hidden"
                    />
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200">
                    <button
                      type="button"
                      onClick={() => setShowDecisionModal(false)}
                      disabled={submittingDecision}
                      className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleSubmitDecision}
                      disabled={submittingDecision || decisionReason.trim().length < 10}
                      className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold text-white transition-colors shadow-xs disabled:opacity-50 ${
                        selectedDecisionOutcome === "QUALIFIED"
                          ? "bg-emerald-700 hover:bg-emerald-600"
                          : selectedDecisionOutcome === "DISQUALIFIED"
                          ? "bg-rose-700 hover:bg-rose-600"
                          : "bg-amber-600 hover:bg-amber-500"
                      }`}
                    >
                      {submittingDecision ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                          Recording Decision...
                        </>
                      ) : (
                        `Confirm ${selectedDecisionOutcome}`
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Advisory Operational Notice */}
            <div className="rounded-xl border border-purple-200 bg-purple-50/40 p-5">
              <div className="flex items-start gap-3">
                <ShieldCheck className="h-5 w-5 text-purple-900 shrink-0 mt-0.5" />
                <div className="text-xs text-slate-700 space-y-1">
                  <p className="font-bold text-purple-900">
                    Enterprise Procurement Governance Disclaimer
                  </p>
                  <p>
                    All scoring contributions and risk floors are derived deterministically. AI recommendations are purely advisory and do not constitute an official procurement decision. The final qualification or disqualification decision remains strictly with the authorized Procurement Officer.
                  </p>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </DashboardLayout>
  );
}
