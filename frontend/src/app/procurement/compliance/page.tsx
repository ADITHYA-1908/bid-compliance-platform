"use client";

import React, { useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  getProcurementBidCompliance,
  evaluateProcurementBidCompliance,
} from "@/lib/api/compliance";
import {
  getProcurementBidScore,
  calculateProcurementBidScore,
} from "@/lib/api/scoring";
import {
  getProcurementBidRisk,
  calculateProcurementBidRisk,
} from "@/lib/api/risk";
import {
  BidComplianceSummaryResponse,
  ComplianceResultItem,
  ComplianceStatus,
} from "@/types/compliance";
import {
  BidScoringFoundationResponse,
  CategoryScore,
} from "@/types/scoring";
import {
  BidRiskAssessmentResponse,
  RiskContribution,
  RiskLevel,
} from "@/types/risk";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
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
  ShieldAlert,
  Activity,
  AlertCircle,
  Sparkles,
  Bot,
  MessageSquare,
  Send,
  CornerDownRight,
  HelpCircle,
  Check,
} from "lucide-react";
import { AIRecommendationResponse, AIQuestionResponse } from "@/types/ai";
import {
  getProcurementBidAIRecommendation,
  generateProcurementBidAIRecommendation,
  askProcurementBidAIQuestion,
} from "@/lib/api/ai";


export default function ProcurementCompliancePage() {
  const [bidIdInput, setBidIdInput] = useState<string>("");
  const [selectedBidId, setSelectedBidId] = useState<string | null>(null);
  const [complianceData, setComplianceData] = useState<BidComplianceSummaryResponse | null>(null);
  const [scoringData, setScoringData] = useState<BidScoringFoundationResponse | null>(null);
  const [riskData, setRiskData] = useState<BidRiskAssessmentResponse | null>(null);
  const [aiData, setAiData] = useState<AIRecommendationResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [isScoring, setIsScoring] = useState<boolean>(false);
  const [isRiskLoading, setIsRiskLoading] = useState<boolean>(false);
  const [isAILoading, setIsAILoading] = useState<boolean>(false);
  const [aiQuestion, setAiQuestion] = useState<string>("");
  const [isAsking, setIsAsking] = useState<boolean>(false);
  const [qaHistory, setQaHistory] = useState<AIQuestionResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Evidence Drawer / Modal
  const [selectedRule, setSelectedRule] = useState<ComplianceResultItem | null>(null);

  const fetchComplianceAndScore = async (bidId: string) => {
    if (!bidId.trim()) return;
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const [compData, scoreData, rData, aData] = await Promise.all([
        getProcurementBidCompliance(bidId.trim()),
        getProcurementBidScore(bidId.trim()).catch(() => null),
        getProcurementBidRisk(bidId.trim()).catch(() => null),
        getProcurementBidAIRecommendation(bidId.trim()).catch(() => null),
      ]);
      setComplianceData(compData);
      setScoringData(scoreData);
      setRiskData(rData);
      setAiData(aData);
      setSelectedBidId(bidId.trim());
    } catch (err: any) {
      setError(err?.message || "Failed to load bid compliance record. Ensure the Bid ID exists and has been submitted.");
      setComplianceData(null);
      setScoringData(null);
      setRiskData(null);
      setAiData(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunEvaluation = async () => {
    if (!selectedBidId) return;
    setIsEvaluating(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const compData = await evaluateProcurementBidCompliance(selectedBidId);
      setComplianceData(compData);
      const scoreData = await calculateProcurementBidScore(selectedBidId).catch(() => null);
      setScoringData(scoreData);
      const rData = await calculateProcurementBidRisk(selectedBidId).catch(() => null);
      setRiskData(rData);
      // Mark AI data as stale or re-fetch
      const aData = await getProcurementBidAIRecommendation(selectedBidId).catch(() => null);
      setAiData(aData);
      setSuccessMessage(`Compliance audit evaluation completed (Version ${compData.evaluation_version}). All clauses evaluated.`);
    } catch (err: any) {
      setError(err?.message || "Failed to execute compliance audit evaluation.");
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleRecalculateScore = async () => {
    if (!selectedBidId) return;
    setIsScoring(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const scoreData = await calculateProcurementBidScore(selectedBidId);
      setScoringData(scoreData);
      const rData = await calculateProcurementBidRisk(selectedBidId).catch(() => null);
      setRiskData(rData);
      const aData = await getProcurementBidAIRecommendation(selectedBidId).catch(() => null);
      setAiData(aData);
      setSuccessMessage(`Scoring and risk recalculation complete (Snapshot v${scoreData.scoring_version}).`);
    } catch (err: any) {
      setError(err?.message || "Failed to calculate bid score.");
    } finally {
      setIsScoring(false);
    }
  };

  const handleRecalculateRisk = async () => {
    if (!selectedBidId) return;
    setIsRiskLoading(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const rData = await calculateProcurementBidRisk(selectedBidId);
      setRiskData(rData);
      const aData = await getProcurementBidAIRecommendation(selectedBidId).catch(() => null);
      setAiData(aData);
      setSuccessMessage(`Base risk assessment updated (Snapshot v${rData.risk_version}).`);
    } catch (err: any) {
      setError(err?.message || "Failed to recalculate base risk.");
    } finally {
      setIsRiskLoading(false);
    }
  };

  const handleGenerateAIRecommendation = async () => {
    if (!selectedBidId) return;
    setIsAILoading(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const aData = await generateProcurementBidAIRecommendation(selectedBidId);
      setAiData(aData);
      setSuccessMessage("AI evaluation assistant recommendation generated successfully from grounded evidence.");
    } catch (err: any) {
      setError(err?.message || "Failed to generate AI evaluation recommendation.");
    } finally {
      setIsAILoading(false);
    }
  };

  const handleAskAIQuestion = async (customQuestion?: string) => {
    const q = customQuestion || aiQuestion;
    if (!selectedBidId || !q.trim()) return;
    setIsAsking(true);
    setError(null);
    try {
      const resp = await askProcurementBidAIQuestion(selectedBidId, q.trim());
      setQaHistory((prev) => [resp, ...prev]);
      if (!customQuestion) {
        setAiQuestion("");
      }
    } catch (err: any) {
      setError(err?.message || "Failed to retrieve evidence-grounded answer.");
    } finally {
      setIsAsking(false);
    }
  };


  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (bidIdInput.trim()) {
      fetchComplianceAndScore(bidIdInput.trim());
    }
  };


  // Filtered results
  const filteredResults = complianceData?.results.filter((item) => {
    // Category filter
    if (categoryFilter !== "ALL") {
      const cat = (item.category || "").toUpperCase();
      if (categoryFilter === "STATUTORY" && !cat.includes("STATUTORY") && !cat.includes("REGISTRATION")) return false;
      if (categoryFilter === "FINANCIAL" && !cat.includes("FINANCIAL")) return false;
      if (categoryFilter === "EXPERIENCE" && !cat.includes("EXPERIENCE")) return false;
      if (categoryFilter === "TECHNICAL" && !cat.includes("TECHNICAL") && !cat.includes("OEM") && !cat.includes("BIS") && !cat.includes("LOCAL_CONTENT")) return false;
      if (categoryFilter === "INTEGRITY" && !cat.includes("INTEGRITY") && !cat.includes("BLACKLIST")) return false;
    }

    // Status filter
    if (statusFilter !== "ALL") {
      if (statusFilter === "CRITICAL_FAILURES" && !(item.critical_failure || (item.is_critical && item.compliance_status === ComplianceStatus.FAIL))) return false;
      if (statusFilter === "MANDATORY_FAILURES" && !(item.is_mandatory && item.compliance_status === ComplianceStatus.FAIL)) return false;
      if (statusFilter !== "CRITICAL_FAILURES" && statusFilter !== "MANDATORY_FAILURES" && item.compliance_status !== statusFilter) return false;
    }

    // Text search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const code = (item.requirement_code || "").toLowerCase();
      const name = (item.requirement_name || "").toLowerCase();
      const reason = (item.reason || "").toLowerCase();
      if (!code.includes(q) && !name.includes(q) && !reason.includes(q)) return false;
    }

    return true;
  }) || [];

  const getStatusBadge = (status: ComplianceStatus, isCritical?: boolean, criticalFailure?: boolean) => {
    if (criticalFailure || (isCritical && status === ComplianceStatus.FAIL)) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-red-100 text-red-900 border border-red-300 animate-pulse">
          <AlertOctagon className="w-3.5 h-3.5 text-red-700" />
          CRITICAL FAIL
        </span>
      );
    }

    switch (status) {
      case ComplianceStatus.PASS:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
            PASS
          </span>
        );
      case ComplianceStatus.FAIL:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-900 border border-rose-300">
            <XCircle className="w-3.5 h-3.5 text-rose-700" />
            FAIL
          </span>
        );
      case ComplianceStatus.REVIEW:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
            REVIEW
          </span>
        );
      case ComplianceStatus.PENDING:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-900 border border-blue-300">
            <Clock className="w-3.5 h-3.5 text-blue-700" />
            PENDING
          </span>
        );
      case ComplianceStatus.NOT_APPLICABLE:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-300">
            <MinusCircle className="w-3.5 h-3.5 text-slate-500" />
            N/A
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER"]}
      title="Compliance Audit & Clause Verification"
      description="Inspect deterministic clause-by-clause compliance determinations, statutory verifications, and audit evidence across submitted bidder proposals."
      breadcrumbs={[
        { label: "Procurement", href: "/procurement" },
        { label: "Compliance Audit" },
      ]}
    >
      <div className="space-y-6">
        {/* Bid Search & Audit Initiation Bar */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-purple-800" />
                Select Bid Proposal for Compliance Audit
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Enter a submitted Bid UUID to inspect verified statutory credentials, financial criteria, technical specs, and human review items.
              </p>
            </div>

            <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 w-full md:w-auto">
              <div className="relative flex-1 md:w-80">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Enter Bid UUID (e.g. 550e8400...)"
                  value={bidIdInput}
                  onChange={(e) => setBidIdInput(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-xs font-mono border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-purple-700 focus:border-purple-700"
                />
              </div>
              <button
                type="submit"
                disabled={isLoading || !bidIdInput.trim()}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-lg bg-purple-900 text-white hover:bg-purple-800 disabled:opacity-50 transition-colors shadow-xs"
              >
                {isLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                Load Audit
              </button>
            </form>
          </div>

          {/* Feedback alerts */}
          {error && (
            <div className="mt-4 p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-rose-700 mt-0.5 shrink-0" />
              <p className="text-xs font-medium text-rose-800">{error}</p>
            </div>
          )}
          {successMessage && (
            <div className="mt-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-700 mt-0.5 shrink-0" />
              <p className="text-xs font-medium text-emerald-800">{successMessage}</p>
            </div>
          )}
        </div>

        {/* Audit Dashboard Content */}
        {complianceData && (
          <>
            {/* Header Telemetry Card */}
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Audit Target
                    </span>
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-md bg-purple-50 text-purple-900 border border-purple-200">
                      BID: {complianceData.bid_id}
                    </span>
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-800 border border-slate-300">
                      TENDER: {complianceData.tender_id}
                    </span>
                    <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded-md bg-blue-50 text-blue-800 border border-blue-200">
                      Evaluation Version: v{complianceData.evaluation_version}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Last Evaluated: {complianceData.evaluated_at ? new Date(complianceData.evaluated_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" }) : "Recently"} IST
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleRunEvaluation}
                    disabled={isEvaluating}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold bg-purple-900 text-white hover:bg-purple-800 transition-colors shadow-xs disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isEvaluating ? "animate-spin" : ""}`} />
                    {isEvaluating ? "Re-Evaluating Engine..." : "Re-Run Compliance Audit"}
                  </button>
                </div>
              </div>

              {/* Critical / Mandatory Failure Banner */}
              {(complianceData.counts.critical_failures || 0) > 0 && (
                <div className="mt-4 p-4 rounded-lg bg-red-50 border border-red-200 flex items-start gap-3">
                  <AlertOctagon className="w-5 h-5 text-red-700 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-xs font-bold text-red-900 uppercase tracking-wider">
                      Critical Non-Compliance Detected ({complianceData.counts.critical_failures} Critical Rule Violations)
                    </h4>
                    <p className="text-xs text-red-800 mt-0.5">
                      This proposal contains fatal non-compliance on critical requirements (such as debarment/blacklisting or mandatory statutory prerequisite).
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Metric KPI Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Rules</span>
                <p className="text-2xl font-black font-mono text-slate-900 mt-1">{complianceData.counts.total}</p>
                <p className="text-[10px] text-slate-400 mt-0.5">Active criteria</p>
              </div>

              <div className="bg-white rounded-xl border border-emerald-200 bg-emerald-50/20 p-4 shadow-xs">
                <span className="text-[11px] font-semibold text-emerald-800 uppercase tracking-wider">Passed</span>
                <p className="text-2xl font-black font-mono text-emerald-800 mt-1">{complianceData.counts.passed}</p>
                <p className="text-[10px] text-emerald-600 mt-0.5">Full compliance</p>
              </div>

              <div className="bg-white rounded-xl border border-rose-200 bg-rose-50/20 p-4 shadow-xs">
                <span className="text-[11px] font-semibold text-rose-800 uppercase tracking-wider">Failed</span>
                <p className="text-2xl font-black font-mono text-rose-800 mt-1">{complianceData.counts.failed}</p>
                <p className="text-[10px] text-rose-600 mt-0.5">Non-compliant</p>
              </div>

              <div className="bg-white rounded-xl border border-amber-200 bg-amber-50/20 p-4 shadow-xs">
                <span className="text-[11px] font-semibold text-amber-800 uppercase tracking-wider">In Review</span>
                <p className="text-2xl font-black font-mono text-amber-800 mt-1">{complianceData.counts.review}</p>
                <p className="text-[10px] text-amber-600 mt-0.5">Human audit needed</p>
              </div>

              <div className="bg-white rounded-xl border border-blue-200 bg-blue-50/20 p-4 shadow-xs">
                <span className="text-[11px] font-semibold text-blue-800 uppercase tracking-wider">Pending</span>
                <p className="text-2xl font-black font-mono text-blue-800 mt-1">{complianceData.counts.pending}</p>
                <p className="text-[10px] text-blue-600 mt-0.5">Unverified claims</p>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
                <span className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">Not Applicable</span>
                <p className="text-2xl font-black font-mono text-slate-700 mt-1">{complianceData.counts.not_applicable}</p>
                <p className="text-[10px] text-slate-400 mt-0.5">Exempt / N/A</p>
              </div>

              <div className="bg-white rounded-xl border border-red-300 bg-red-50 p-4 shadow-xs">
                <span className="text-[11px] font-bold text-red-900 uppercase tracking-wider">Mandatory Fails</span>
                <p className="text-2xl font-black font-mono text-red-900 mt-1">{complianceData.counts.mandatory_failures || 0}</p>
                <p className="text-[10px] text-red-700 mt-0.5">Disqualifying flags</p>
              </div>
            </div>

            {/* Compliance Scoring & Category Breakdown (Part 7A & 7B) */}
            {scoringData && (
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-700">
                      <Award className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                        Compliance Scoring Foundation & Category Breakdown
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                          {scoringData.scoring_formula_version}
                        </span>
                      </h3>
                      <p className="text-xs text-slate-500">
                        Deterministic weighted compliance scoring computed across all applicable tender requirements.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleRecalculateScore}
                      disabled={isScoring}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors border border-slate-200 disabled:opacity-50"
                    >
                      <RefreshCw className={`w-3 h-3 ${isScoring ? "animate-spin" : ""}`} />
                      {isScoring ? "Recalculating..." : "Recalculate Score"}
                    </button>
                  </div>
                </div>

                {/* Overall Score Banner */}
                <div className={`p-5 rounded-xl border ${
                  scoringData.is_provisional
                    ? "bg-amber-50/40 border-amber-200"
                    : "bg-slate-900 text-white border-slate-800"
                }`}>
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold uppercase tracking-wider ${
                          scoringData.is_provisional ? "text-amber-800" : "text-slate-300"
                        }`}>
                          {scoringData.is_provisional ? "Provisional Compliance Score" : "Overall Compliance Score"}
                        </span>
                        {scoringData.is_provisional && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-100 text-amber-900 border border-amber-300">
                            PROVISIONAL — {scoringData.readiness.pending_rules} PENDING CLAIMS
                          </span>
                        )}
                        {scoringData.readiness.human_review_required && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-200 text-amber-900 border border-amber-400">
                            HUMAN REVIEW REQUIRED
                          </span>
                        )}
                      </div>
                      <p className={`text-xs ${scoringData.is_provisional ? "text-amber-900" : "text-slate-300"}`}>
                        Total Earned Weight: <span className="font-mono font-bold">{scoringData.earned_weight}</span> / <span className="font-mono font-bold">{scoringData.eligible_weight}</span> eligible rule weight points.
                      </p>
                    </div>

                    <div className="text-right">
                      {scoringData.overall_score !== null && scoringData.overall_score !== undefined ? (
                        <div className="flex items-baseline md:justify-end gap-1">
                          <span className={`text-4xl font-black font-mono ${
                            scoringData.is_provisional ? "text-amber-900" : "text-emerald-400"
                          }`}>
                            {scoringData.overall_score}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-sm font-bold font-mono px-3 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          NO SCORABLE REQUIREMENTS
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Visual Progress Bar */}
                  {scoringData.eligible_weight && Number(scoringData.eligible_weight) > 0 && (
                    <div className="mt-4">
                      <div className={`w-full h-2.5 rounded-full overflow-hidden ${
                        scoringData.is_provisional ? "bg-amber-200" : "bg-slate-800"
                      }`}>
                        <div
                          className={`h-full transition-all duration-500 rounded-full ${
                            scoringData.is_provisional
                              ? "bg-amber-600"
                              : Number(scoringData.overall_score || 0) >= 75
                              ? "bg-emerald-400"
                              : Number(scoringData.overall_score || 0) >= 50
                              ? "bg-blue-400"
                              : "bg-rose-400"
                          }`}
                          style={{
                            width: `${Math.min(100, Math.max(0, (Number(scoringData.earned_weight) / Number(scoringData.eligible_weight)) * 100))}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Category Breakdown Grid */}
                {scoringData.category_scores && Object.keys(scoringData.category_scores).length > 0 && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-slate-500" />
                      Category Domain Score Breakdown
                    </h4>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {Object.entries(scoringData.category_scores).map(([catKey, cat]: [string, CategoryScore]) => {
                        const scoreVal = cat.display_score !== null && cat.display_score !== undefined ? Number(cat.display_score) : null;
                        return (
                          <div
                            key={catKey}
                            className="bg-slate-50/70 rounded-xl border border-slate-200 p-4 space-y-3 hover:border-slate-300 transition-colors"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <span className="font-mono text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                                  {cat.category}
                                </span>
                                <h5 className="text-xs font-bold text-slate-900">{cat.display_name}</h5>
                              </div>
                              <div>
                                {scoreVal !== null ? (
                                  <span className={`text-xs font-black font-mono px-2 py-0.5 rounded-md border ${
                                    scoreVal >= 80
                                      ? "bg-emerald-100 text-emerald-900 border-emerald-300"
                                      : scoreVal >= 50
                                      ? "bg-blue-100 text-blue-900 border-blue-300"
                                      : "bg-rose-100 text-rose-900 border-rose-300"
                                  }`}>
                                    {scoreVal}%
                                  </span>
                                ) : (
                                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-200 text-slate-600">
                                    N/A
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Category Progress */}
                            {cat.eligible_weight && Number(cat.eligible_weight) > 0 && (
                              <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    scoreVal !== null && scoreVal >= 80
                                      ? "bg-emerald-500"
                                      : scoreVal !== null && scoreVal >= 50
                                      ? "bg-blue-500"
                                      : "bg-rose-500"
                                  }`}
                                  style={{
                                    width: `${Math.min(100, Math.max(0, (Number(cat.earned_weight) / Number(cat.eligible_weight)) * 100))}%`,
                                  }}
                                />
                              </div>
                            )}

                            {/* Category Meta */}
                            <div className="flex items-center justify-between text-[11px] text-slate-600 pt-1 border-t border-slate-200/60 font-mono">
                              <span>Earned: {cat.earned_weight} / {cat.eligible_weight}</span>
                              <div className="flex items-center gap-1.5">
                                <span className="text-emerald-700 font-bold">{cat.passed_rules}P</span>
                                <span className="text-rose-700 font-bold">{cat.failed_rules}F</span>
                                {cat.review_rules > 0 && (
                                  <span className="text-amber-700 font-bold">{cat.review_rules}R</span>
                                )}
                                {cat.pending_rules > 0 && (
                                  <span className="text-blue-700 font-bold">{cat.pending_rules}Pend</span>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}


            {/* Deterministic Risk & Overrides Assessment (Part 7C & 7D) */}
            {riskData && (
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-orange-50 border border-orange-200 flex items-center justify-center text-orange-700">
                      <ShieldAlert className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                        Deterministic Risk Assessment & Critical Overrides
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                          Base: {riskData.risk_formula_version} | Overrides: {riskData.override_formula_version || "v1"}
                        </span>
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200">
                          Risk Model v1
                        </span>
                      </h3>
                      <p className="text-xs text-slate-500">
                        Multi-signal base risk evaluation with deterministic critical risk floors and integrity overrides.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleRecalculateRisk}
                      disabled={isRiskLoading}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors border border-slate-200 disabled:opacity-50"
                    >
                      <RefreshCw className={`w-3 h-3 ${isRiskLoading ? "animate-spin" : ""}`} />
                      {isRiskLoading ? "Recalculating..." : "Recalculate Risk"}
                    </button>
                  </div>
                </div>

                {/* Adjusted & Base Risk Banner */}
                {(() => {
                  const effectiveLevel = riskData.adjusted_risk_level || riskData.base_risk_level;
                  const effectiveScore = riskData.adjusted_risk_score !== null && riskData.adjusted_risk_score !== undefined
                    ? riskData.adjusted_risk_score
                    : riskData.base_risk_score;

                  return (
                    <div className={`p-5 rounded-xl border ${
                      riskData.is_provisional
                        ? "bg-amber-50/40 border-amber-200"
                        : effectiveLevel === "CRITICAL"
                        ? "bg-rose-50 border-rose-200 text-rose-950"
                        : effectiveLevel === "HIGH"
                        ? "bg-orange-50 border-orange-200 text-orange-950"
                        : effectiveLevel === "MEDIUM"
                        ? "bg-amber-50 border-amber-200 text-amber-950"
                        : "bg-emerald-50 border-emerald-200 text-emerald-950"
                    }`}>
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                              Adjusted Risk Level:
                            </span>
                            {effectiveLevel ? (
                              <span className={`text-xs font-black px-2.5 py-0.5 rounded-md border ${
                                effectiveLevel === "CRITICAL"
                                  ? "bg-rose-600 text-white border-rose-700"
                                  : effectiveLevel === "HIGH"
                                  ? "bg-orange-500 text-white border-orange-600"
                                  : effectiveLevel === "MEDIUM"
                                  ? "bg-amber-500 text-white border-amber-600"
                                  : "bg-emerald-600 text-white border-emerald-700"
                              }`}>
                                {effectiveLevel} RISK
                              </span>
                            ) : (
                              <span className="text-xs font-bold px-2 py-0.5 rounded-md bg-slate-200 text-slate-700">
                                UNAVAILABLE
                              </span>
                            )}
                            {riskData.override_applied && (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-rose-100 text-rose-900 border border-rose-300 flex items-center gap-1">
                                <AlertOctagon className="w-3 h-3 text-rose-600" />
                                OVERRIDE APPLIED ({riskData.override_count || 1})
                              </span>
                            )}
                            {riskData.is_provisional && (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-100 text-amber-900 border border-amber-300">
                                PROVISIONAL
                              </span>
                            )}
                            {riskData.human_review_required && (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-200 text-amber-900 border border-amber-400">
                                OFFICER REVIEW REQUIRED
                              </span>
                            )}
                          </div>

                          {/* Base Risk Comparison Line */}
                          <div className="flex items-center gap-2 text-xs text-slate-600">
                            <span>Base Mathematical Risk:</span>
                            <span className="font-mono font-bold text-slate-800">
                              {riskData.base_risk_score !== null ? `${riskData.base_risk_score}/100` : "N/A"} ({riskData.base_risk_level || "N/A"})
                            </span>
                            {riskData.override_applied && (
                              <>
                                <span>→</span>
                                <span className="font-mono font-bold text-rose-700">
                                  Adjusted to {riskData.adjusted_risk_score}/100 ({riskData.adjusted_risk_level})
                                </span>
                              </>
                            )}
                          </div>
                        </div>

                        <div className="text-right">
                          {effectiveScore !== null && effectiveScore !== undefined ? (
                            <div className="flex items-baseline md:justify-end gap-1.5">
                              <span className={`text-4xl font-black font-mono ${
                                Number(effectiveScore) >= 75
                                  ? "text-rose-700"
                                  : Number(effectiveScore) >= 50
                                  ? "text-orange-700"
                                  : Number(effectiveScore) >= 25
                                  ? "text-amber-700"
                                  : "text-emerald-700"
                              }`}>
                                {effectiveScore}
                              </span>
                              <span className="text-xs font-bold text-slate-500">/ 100</span>
                            </div>
                          ) : (
                            <span className="text-sm font-bold font-mono px-3 py-1 rounded bg-slate-100 text-slate-600 border border-slate-200">
                              NOT COMPUTED
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Visual Risk Gauge Meter */}
                      {effectiveScore !== null && effectiveScore !== undefined && (
                        <div className="mt-4 space-y-1">
                          <div className="w-full h-2.5 bg-slate-200/80 rounded-full overflow-hidden">
                            <div
                              className={`h-full transition-all duration-500 rounded-full ${
                                Number(effectiveScore) >= 75
                                  ? "bg-rose-600"
                                  : Number(effectiveScore) >= 50
                                  ? "bg-orange-500"
                                  : Number(effectiveScore) >= 25
                                  ? "bg-amber-500"
                                  : "bg-emerald-600"
                              }`}
                              style={{
                                width: `${Math.min(100, Math.max(0, Number(effectiveScore)))}%`,
                              }}
                            />
                          </div>
                          <div className="flex justify-between text-[10px] font-mono text-slate-400 px-0.5">
                            <span>0 (Low)</span>
                            <span>25 (Med)</span>
                            <span>50 (High)</span>
                            <span>75 (Critical)</span>
                            <span>100</span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Applied Critical Overrides & Risk Floors (Part 7D) */}
                {riskData.override_applied && riskData.applied_overrides && riskData.applied_overrides.length > 0 ? (
                  <div className="bg-rose-50/50 rounded-xl border border-rose-200 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wider flex items-center gap-1.5">
                        <AlertOctagon className="w-3.5 h-3.5 text-rose-600" />
                        Applied Critical Risk Overrides & Minimum Floors ({riskData.applied_overrides.length})
                      </h4>
                    </div>
                    <div className="overflow-x-auto border border-rose-200 rounded-lg bg-white">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-rose-50/70 border-b border-rose-200 font-semibold text-rose-900">
                            <th className="py-2 px-3">Rule / Trigger</th>
                            <th className="py-2 px-3">Type</th>
                            <th className="py-2 px-3">Severity</th>
                            <th className="py-2 px-3 text-right">Risk Floor</th>
                            <th className="py-2 px-3">Audit Reason</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-rose-100">
                          {riskData.applied_overrides.map((ovr, idx) => (
                            <tr key={idx} className="hover:bg-rose-50/30 transition-colors">
                              <td className="py-2.5 px-3 font-semibold text-slate-900">
                                {ovr.rule_code || "OVERRIDE"}
                                <span className="block font-mono text-[10px] text-slate-400">{ovr.trigger}</span>
                              </td>
                              <td className="py-2.5 px-3 font-mono text-[11px] text-slate-700">{ovr.override_type}</td>
                              <td className="py-2.5 px-3">
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                                  ovr.severity === "CRITICAL"
                                    ? "bg-rose-100 text-rose-900 border-rose-300"
                                    : ovr.severity === "HIGH"
                                    ? "bg-orange-100 text-orange-900 border-orange-300"
                                    : "bg-amber-100 text-amber-900 border-amber-300"
                                }`}>
                                  {ovr.severity}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 font-mono text-right font-bold text-rose-700">
                                {ovr.risk_floor ? `${Number(ovr.risk_floor).toFixed(1)} pts` : "—"}
                              </td>
                              <td className="py-2.5 px-3 text-slate-600 text-[11px] leading-relaxed">{ovr.reason}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 bg-emerald-50/60 rounded-lg border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>No critical risk adjustments applied. Adjusted Risk matches mathematical Base Risk.</span>
                  </div>
                )}

                {/* Summary Explanations */}
                {riskData.summary_reasons && riskData.summary_reasons.length > 0 && (
                  <div className="bg-slate-50/80 rounded-xl border border-slate-200 p-4 space-y-2">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <Activity className="w-3.5 h-3.5 text-slate-500" />
                      Deterministic Risk Summary & Audit Findings
                    </h4>
                    <ul className="space-y-1">
                      {riskData.summary_reasons.map((r, i) => (
                        <li key={i} className="text-xs text-slate-600 flex items-start gap-2">
                          <span className="text-slate-400 mt-0.5 font-bold">•</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Itemized Deterministic Base Risk Contributors Table */}
                {riskData.contributions && riskData.contributions.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <Sliders className="w-3.5 h-3.5 text-slate-500" />
                      Itemized Base Risk Contributors Breakdown (Part 7C)
                    </h4>
                    <div className="overflow-x-auto border border-slate-200 rounded-xl">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-slate-50 border-b border-slate-200 font-semibold text-slate-600">
                            <th className="py-2.5 px-3">Risk Factor Indicator</th>
                            <th className="py-2.5 px-3">Observed Value</th>
                            <th className="py-2.5 px-3 text-right">Max Pts</th>
                            <th className="py-2.5 px-3 text-right">Base Contribution</th>
                            <th className="py-2.5 px-3">Audit Reason</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {riskData.contributions.map((c, i) => {
                            const contribVal = Number(c.weighted_contribution || 0);
                            return (
                              <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                                <td className="py-2.5 px-3 font-semibold text-slate-900">
                                  {c.name}
                                  <span className="block font-mono text-[10px] text-slate-400 uppercase">{c.indicator}</span>
                                </td>
                                <td className="py-2.5 px-3 font-mono text-slate-700">{c.raw_value}</td>
                                <td className="py-2.5 px-3 font-mono text-slate-500 text-right">{Number(c.weight).toFixed(1)}</td>
                                <td className="py-2.5 px-3 text-right font-mono font-bold">
                                  <span className={contribVal > 0 ? "text-rose-600" : "text-emerald-600"}>
                                    +{contribVal.toFixed(2)}
                                  </span>
                                </td>
                                <td className="py-2.5 px-3 text-slate-600 text-[11px]">{c.reason}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Part 7D Architectural Boundary Notice */}
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-[11px] text-slate-500 flex items-center gap-2">
                  <Info className="w-4 h-4 text-slate-400 shrink-0" />
                  <span>
                    <strong>Notice</strong>: Part 7D applies deterministic risk adjustments to Part 7C base risk. AI-generated explanations are provided in Part 7E. Final qualification/disqualification decisions remain human-controlled by the Procurement Officer in Part 8.
                  </span>
                </div>
              </div>
            )}


            {/* ============================================================= */}
            {/* Part 7E: RAG + AI Recommendation & Evidence-Based Explanation */}
            {/* ============================================================= */}
            <div className="bg-white rounded-xl border border-indigo-200 p-6 shadow-xs space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shadow-xs">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                      AI-Assisted Evaluation Assistant
                      <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                        Part 7E RAG
                      </span>
                    </h2>
                    <p className="text-xs text-slate-500">
                      Grounded knowledge retrieval, multi-source evidence citations, and non-binding AI recommendation
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleGenerateAIRecommendation}
                    disabled={isAILoading}
                    className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-colors disabled:opacity-50"
                  >
                    <Bot className={`w-3.5 h-3.5 ${isAILoading ? "animate-spin" : ""}`} />
                    {isAILoading ? "Analyzing Evidence..." : aiData ? "Re-analyze Bid" : "Analyze Bid with AI"}
                  </button>
                </div>
              </div>

              {/* Recommendation Content */}
              {aiData ? (
                <div className="space-y-5">
                  {/* Stale Warning Banner */}
                  {aiData.is_stale && (
                    <div className="p-3.5 rounded-lg bg-amber-50 border border-amber-300 text-xs text-amber-900 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />
                        <span>
                          <strong>Recommendation Outdated</strong>: Upstream compliance, scoring, or risk rules have changed since this analysis was generated.
                        </span>
                      </div>
                      <button
                        onClick={handleGenerateAIRecommendation}
                        disabled={isAILoading}
                        className="px-2.5 py-1 rounded bg-amber-200 hover:bg-amber-300 font-semibold text-[11px] text-amber-900 transition-colors"
                      >
                        Refresh Analysis
                      </button>
                    </div>
                  )}

                  {/* Hero Recommendation Banner */}
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">AI Recommendation:</span>
                        <span
                          className={`text-xs font-bold px-3 py-1 rounded-full border shadow-xs ${
                            aiData.recommendation === "PROCEED"
                              ? "bg-emerald-100 text-emerald-900 border-emerald-300"
                              : aiData.recommendation === "PROCEED_WITH_REVIEW"
                              ? "bg-sky-100 text-sky-900 border-sky-300"
                              : aiData.recommendation === "REVIEW_REQUIRED"
                              ? "bg-amber-100 text-amber-900 border-amber-300"
                              : aiData.recommendation === "DO_NOT_PROCEED_WITHOUT_REVIEW"
                              ? "bg-rose-100 text-rose-900 border-rose-300"
                              : "bg-slate-100 text-slate-800 border-slate-300"
                          }`}
                        >
                          {aiData.recommendation}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-slate-500">Confidence:</span>
                        <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                          {aiData.confidence_label}
                        </span>
                        {aiData.guardrail_applied && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-300 flex items-center gap-1">
                            <ShieldCheck className="w-3 h-3 text-purple-600" />
                            Guardrail Adjusted
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="text-sm font-semibold text-slate-900 leading-snug">
                      "{aiData.recommendation_reason}"
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed">
                      {aiData.summary}
                    </p>

                    {aiData.guardrail_applied && aiData.guardrail_reason && (
                      <div className="p-2.5 bg-purple-50 rounded-lg border border-purple-200 text-[11px] text-purple-900 flex items-start gap-2">
                        <Info className="w-3.5 h-3.5 text-purple-600 shrink-0 mt-0.5" />
                        <span>
                          <strong>Policy Guardrail Applied</strong>: {aiData.guardrail_reason}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Strengths and Concerns 2-Col Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Strengths */}
                    <div className="p-4 rounded-xl bg-emerald-50/50 border border-emerald-200 space-y-2">
                      <h4 className="text-xs font-bold text-emerald-900 uppercase tracking-wider flex items-center gap-1.5">
                        <Check className="w-4 h-4 text-emerald-700" />
                        Key Verified Strengths ({aiData.strengths?.length || 0})
                      </h4>
                      <ul className="space-y-1.5 text-xs text-emerald-950">
                        {aiData.strengths && aiData.strengths.length > 0 ? (
                          aiData.strengths.map((str, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-emerald-600 font-bold">•</span>
                              <span>{str}</span>
                            </li>
                          ))
                        ) : (
                          <li className="text-slate-500 italic text-[11px]">No specific positive items extracted.</li>
                        )}
                      </ul>
                    </div>

                    {/* Concerns & Review Items */}
                    <div className="p-4 rounded-xl bg-rose-50/50 border border-rose-200 space-y-2">
                      <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wider flex items-center gap-1.5">
                        <AlertCircle className="w-4 h-4 text-rose-700" />
                        Concerns & Inspection Items ({(aiData.concerns?.length || 0) + (aiData.review_items?.length || 0)})
                      </h4>
                      <ul className="space-y-1.5 text-xs text-rose-950">
                        {aiData.concerns && aiData.concerns.map((con, idx) => (
                          <li key={`c-${idx}`} className="flex items-start gap-2">
                            <span className="text-rose-600 font-bold">✕</span>
                            <span>{con}</span>
                          </li>
                        ))}
                        {aiData.review_items && aiData.review_items.map((rev, idx) => (
                          <li key={`r-${idx}`} className="flex items-start gap-2">
                            <span className="text-amber-600 font-bold">!</span>
                            <span className="text-amber-900">{rev}</span>
                          </li>
                        ))}
                        {(!aiData.concerns || aiData.concerns.length === 0) && (!aiData.review_items || aiData.review_items.length === 0) && (
                          <li className="text-emerald-700 italic text-[11px]">No active failures or concerns detected.</li>
                        )}
                      </ul>
                    </div>
                  </div>

                  {/* Grounded Evidence Citations */}
                  {aiData.evidence_refs && aiData.evidence_refs.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5 text-indigo-600" />
                        Grounded Knowledge Evidence Citations ({aiData.evidence_refs.length})
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                        {aiData.evidence_refs.map((ref, idx) => (
                          <div
                            key={idx}
                            className="p-3 bg-white rounded-lg border border-slate-200 hover:border-indigo-300 transition-colors shadow-2xs space-y-1"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                                {ref.source_type}
                              </span>
                              {ref.rule_code && (
                                <span className="font-mono text-[10px] font-bold text-indigo-600">
                                  {ref.rule_code}
                                </span>
                              )}
                            </div>
                            <div className="text-xs font-semibold text-slate-900 line-clamp-1">
                              {ref.title}
                            </div>
                            <p className="text-[11px] text-slate-500 line-clamp-2">
                              {ref.summary}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-8 text-center space-y-3 bg-slate-50 rounded-xl border border-dashed border-slate-300">
                  <Bot className="w-10 h-10 text-indigo-400 mx-auto" />
                  <div>
                    <h3 className="text-sm font-bold text-slate-800">No AI Recommendation Generated Yet</h3>
                    <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
                      Trigger knowledge indexing and vector similarity reasoning to generate an evidence-backed recommendation.
                    </p>
                  </div>
                  <button
                    onClick={handleGenerateAIRecommendation}
                    disabled={isAILoading}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-colors"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    {isAILoading ? "Analyzing Evidence..." : "Run AI Recommendation Analysis"}
                  </button>
                </div>
              )}

              {/* Interactive Q&A Console */}
              <div className="pt-4 border-t border-slate-100 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5 text-indigo-600" />
                    Ask AI Assistant about this Bid
                  </h3>
                  <span className="text-[11px] text-slate-400">Grounded in verified tender & bid chunks</span>
                </div>

                {/* Quick Prompts Chips */}
                <div className="flex flex-wrap gap-1.5">
                  {[
                    "Why did this bid fail?",
                    "Explain the risk score and overrides",
                    "Show OEM authorization evidence",
                    "What are the unresolved reviews?",
                  ].map((chip, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleAskAIQuestion(chip)}
                      disabled={isAsking}
                      className="px-2.5 py-1 rounded-full text-[11px] bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-700 border border-slate-200 transition-colors disabled:opacity-50 flex items-center gap-1"
                    >
                      <CornerDownRight className="w-3 h-3 text-slate-400" />
                      {chip}
                    </button>
                  ))}
                </div>

                {/* Input form */}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={aiQuestion}
                    onChange={(e) => setAiQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAskAIQuestion()}
                    placeholder="Ask any question about this proposal's compliance, documents, or risks..."
                    disabled={isAsking}
                    className="flex-1 px-3.5 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                  <button
                    onClick={() => handleAskAIQuestion()}
                    disabled={isAsking || !aiQuestion.trim()}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50 flex items-center gap-1.5"
                  >
                    <Send className="w-3.5 h-3.5" />
                    {isAsking ? "Thinking..." : "Ask"}
                  </button>
                </div>

                {/* Q&A Responses List */}
                {qaHistory.length > 0 && (
                  <div className="space-y-3 pt-2">
                    {qaHistory.map((item, idx) => (
                      <div key={idx} className="p-3.5 rounded-lg bg-indigo-50/40 border border-indigo-100 space-y-2">
                        <div className="text-xs font-bold text-indigo-950 flex items-center gap-2">
                          <HelpCircle className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                          Q: {item.question}
                        </div>
                        <div className="text-xs text-slate-800 pl-5 leading-relaxed">
                          {item.answer}
                        </div>
                        {item.evidence_refs && item.evidence_refs.length > 0 && (
                          <div className="pl-5 pt-1 flex flex-wrap gap-1.5">
                            {item.evidence_refs.map((ev, eIdx) => (
                              <span
                                key={eIdx}
                                className="text-[10px] font-mono px-2 py-0.5 rounded bg-white text-indigo-800 border border-indigo-200"
                              >
                                Citation: {ev.rule_code || ev.title}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Disclaimer Notice */}
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-[11px] text-slate-500 flex items-center gap-2">
                <Info className="w-4 h-4 text-slate-400 shrink-0" />
                <span>
                  <strong>Disclaimer</strong>: This AI recommendation is non-binding and synthesized solely from retrieved verification, compliance, and risk evidence. Final qualification and award decisions remain with the authorized Procurement Officer.
                </span>
              </div>
            </div>



            {/* Human Review Queue Card (If Any Review Items Exist) */}
            {complianceData.review_items && complianceData.review_items.length > 0 && (
              <div className="bg-amber-50/50 rounded-xl border border-amber-200 p-5 shadow-xs">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-bold text-amber-900 uppercase tracking-wider flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-700" />
                    Human Review Queue ({complianceData.review_items.length} Items Requiring Officer Inspection)
                  </h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {complianceData.review_items.map((rev, idx) => (
                    <div key={idx} className="bg-white rounded-lg border border-amber-200 p-3 shadow-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-[11px] font-bold text-slate-900">{rev.requirement_code}</span>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-100 text-amber-900 border border-amber-300">
                          {rev.review_type || "MANUAL_REVIEW"}
                        </span>
                      </div>
                      <p className="text-xs font-semibold text-slate-700 mt-1">{rev.requirement_name}</p>
                      <p className="text-xs text-slate-600 mt-1 bg-amber-50/60 p-2 rounded border border-amber-100">
                        {rev.review_reason}
                      </p>
                      {rev.source_name && (
                        <p className="text-[11px] text-slate-500 mt-1">Source: <span className="font-semibold text-slate-700">{rev.source_name}</span></p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Filters and Search Toolbar */}
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-wrap items-center justify-between gap-3">
              {/* Category Tabs */}
              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { id: "ALL", label: "All Domains" },
                  { id: "STATUTORY", label: "Statutory & MSME" },
                  { id: "FINANCIAL", label: "Financial" },
                  { id: "EXPERIENCE", label: "Past Experience" },
                  { id: "TECHNICAL", label: "Technical & OEM" },
                  { id: "INTEGRITY", label: "Integrity & Debarment" },
                ].map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setCategoryFilter(cat.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                      categoryFilter === cat.id
                        ? "bg-purple-900 text-white shadow-xs"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>

              {/* Status Select & Search */}
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  aria-label="Filter by Compliance Status"
                  className="px-3 py-1.5 text-xs font-semibold border border-slate-300 rounded-lg bg-white text-slate-700 focus:outline-hidden focus:ring-2 focus:ring-purple-700"
                >
                  <option value="ALL">All Statuses</option>
                  <option value={ComplianceStatus.PASS}>PASS Only</option>
                  <option value={ComplianceStatus.FAIL}>FAIL Only</option>
                  <option value={ComplianceStatus.REVIEW}>REVIEW Only</option>
                  <option value={ComplianceStatus.PENDING}>PENDING Only</option>
                  <option value={ComplianceStatus.NOT_APPLICABLE}>N/A Only</option>
                  <option value="MANDATORY_FAILURES">Mandatory Failures</option>
                  <option value="CRITICAL_FAILURES">Critical Failures</option>
                </select>

                <div className="relative flex-1 sm:w-48">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search clause..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-8 pr-2.5 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-purple-700"
                  />
                </div>
              </div>
            </div>

            {/* Rule-by-Rule Compliance Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Clause-by-Clause Compliance Results</h3>
                  <p className="text-xs text-slate-500">Showing {filteredResults.length} of {complianceData.results.length} evaluation criteria</p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      <th className="py-3 px-4">Requirement Clause</th>
                      <th className="py-3 px-4">Category</th>
                      <th className="py-3 px-4">Expected Condition</th>
                      <th className="py-3 px-4">Verified Actual</th>
                      <th className="py-3 px-4">Severity</th>
                      <th className="py-3 px-4">Result</th>
                      <th className="py-3 px-4 text-right">Evidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs">
                    {filteredResults.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-slate-400">
                          No compliance rules match the selected filter criteria.
                        </td>
                      </tr>
                    ) : (
                      filteredResults.map((item, idx) => (
                        <tr
                          key={idx}
                          onClick={() => setSelectedRule(item)}
                          className="hover:bg-purple-50/30 transition-colors cursor-pointer"
                        >
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono font-bold text-slate-900">{item.requirement_code}</span>
                              {item.rule_version_number ? (
                                <span className="font-mono text-[9px] font-bold px-1 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                                  v{item.rule_version_number}
                                </span>
                              ) : null}
                            </div>
                            <div className="text-slate-600 text-[11px] line-clamp-1">{item.requirement_name}</div>
                          </td>

                          <td className="py-3.5 px-4 font-semibold text-slate-700">
                            <span className="px-2 py-0.5 rounded-md bg-slate-100 text-[10px] font-bold text-slate-700">
                              {item.category}
                            </span>
                          </td>

                          <td className="py-3.5 px-4 font-mono text-slate-700 text-[11px]">
                            {item.operator ? `${item.operator} ` : ""}
                            {typeof item.expected_value === "object"
                              ? JSON.stringify(item.expected_value)
                              : String(item.expected_value ?? "—")}
                          </td>

                          <td className="py-3.5 px-4 font-mono text-slate-800 text-[11px]">
                            {typeof item.actual_value === "object"
                              ? JSON.stringify(item.actual_value)
                              : String(item.actual_value ?? "—")}
                          </td>

                          <td className="py-3.5 px-4">
                            <div className="flex flex-col gap-1">
                              {item.is_critical ? (
                                <span className="inline-flex items-center text-[10px] font-extrabold text-red-700 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded w-fit">
                                  CRITICAL
                                </span>
                              ) : item.is_mandatory ? (
                                <span className="inline-flex items-center text-[10px] font-semibold text-slate-700 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded w-fit">
                                  MANDATORY
                                </span>
                              ) : (
                                <span className="inline-flex items-center text-[10px] font-normal text-slate-500 bg-slate-50 px-1.5 py-0.5 rounded w-fit">
                                  OPTIONAL
                                </span>
                              )}
                            </div>
                          </td>

                          <td className="py-3.5 px-4">
                            {getStatusBadge(item.compliance_status, item.is_critical, item.critical_failure)}
                          </td>

                          <td className="py-3.5 px-4 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedRule(item);
                              }}
                              className="inline-flex items-center gap-1 text-[11px] font-bold text-purple-900 hover:text-purple-700 bg-purple-50 hover:bg-purple-100 px-2.5 py-1 rounded-md transition-colors"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              Inspect
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Boundary Notice Banner */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-3">
              <Info className="w-5 h-5 text-purple-800 shrink-0 mt-0.5" />
              <div className="text-xs text-slate-600">
                <strong className="text-slate-800">Deterministic Compliance Engine Notice:</strong> This audit presents verified clause determinations, source provenance records, and human review items produced by Parts 6A–6F. Final weighted scoring (0–100%), overall Risk Level scoring (LOW/MEDIUM/HIGH), and Procurement Officer final qualification workflows will execute in upcoming phases (Part 7 & Part 8).
              </div>
            </div>
          </>
        )}

        {/* Evidence Drawer Modal */}
        {selectedRule && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between sticky top-0 bg-white">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-purple-800" />
                    Clause Audit Detail & Evidence Provenance
                  </h3>
                  <p className="text-xs font-mono text-slate-500 mt-0.5 flex items-center gap-2">
                    <span>{selectedRule.requirement_code}</span>
                    {selectedRule.rule_version_number && (
                      <span className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 font-bold border border-indigo-200 text-[10px]">
                        Evaluated Rule Version: v{selectedRule.rule_version_number}
                      </span>
                    )}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedRule(null)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                >
                  <XCircle className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 space-y-5">
                {/* Status and Name */}
                <div className="flex items-start justify-between gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">{selectedRule.requirement_name}</h4>
                    <p className="text-xs text-slate-500 mt-0.5">Category: <span className="font-semibold text-slate-700">{selectedRule.category}</span></p>
                  </div>
                  {getStatusBadge(selectedRule.compliance_status, selectedRule.is_critical, selectedRule.critical_failure)}
                </div>

                {/* Human Reason */}
                <div>
                  <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Determination Explanation</h5>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-800 font-medium">
                    {selectedRule.reason}
                  </div>
                </div>

                {/* Criteria Comparison Grid */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg border border-slate-200 bg-white">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Operator & Expected Criteria</span>
                    <p className="text-xs font-mono font-bold text-slate-800 mt-1">
                      {selectedRule.operator ? `${selectedRule.operator} ` : ""}
                      {typeof selectedRule.expected_value === "object"
                        ? JSON.stringify(selectedRule.expected_value)
                        : String(selectedRule.expected_value ?? "—")}
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-slate-200 bg-white">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Verified Actual Value</span>
                    <p className="text-xs font-mono font-bold text-slate-800 mt-1">
                      {typeof selectedRule.actual_value === "object"
                        ? JSON.stringify(selectedRule.actual_value)
                        : String(selectedRule.actual_value ?? "—")}
                    </p>
                  </div>
                </div>

                {/* Verification Source IDs & Evidence Metadata */}
                {selectedRule.source_verification_ids && selectedRule.source_verification_ids.length > 0 && (
                  <div>
                    <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Source Verification Records</h5>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedRule.source_verification_ids.map((id, idx) => (
                        <span key={idx} className="px-2.5 py-1 rounded-md bg-purple-50 text-purple-900 border border-purple-200 font-mono text-[11px]">
                          {id}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Structured Evidence Payload */}
                {selectedRule.evidence && Object.keys(selectedRule.evidence).length > 0 && (
                  <div>
                    <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Evidence Payload</h5>
                    <pre className="p-3 rounded-lg bg-slate-900 text-slate-100 text-[11px] font-mono overflow-x-auto max-h-48">
                      {JSON.stringify(selectedRule.evidence, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end">
                <button
                  onClick={() => setSelectedRule(null)}
                  className="px-4 py-2 text-xs font-bold rounded-lg bg-slate-200 text-slate-700 hover:bg-slate-300 transition-colors"
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
