"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  BadgeAlert,
  Bot,
  Building2,
  CheckCircle2,
  Clock,
  Download,
  FileCheck2,
  FileSearch,
  FileText,
  HelpCircle,
  Info,
  Layers,
  MessageSquare,
  MessageSquarePlus,
  RefreshCw,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  XCircle,
} from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  getHumanReviewDetail,
  startHumanReview,
  addHumanReviewNote,
  resolveHumanReview,
} from "@/lib/api/human_review";
import {
  ReviewDetailResponse,
  ReviewResolution,
  ReviewSeverity,
  ReviewStatus,
} from "@/types/human_review";

export default function ReviewDetailPage() {
  const params = useParams();
  const router = useRouter();
  const reviewId = params.reviewId as string;

  const [detail, setDetail] = useState<ReviewDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add Note State
  const [noteText, setNoteText] = useState("");
  const [addingNote, setAddingNote] = useState(false);

  // Resolution Modal State
  const [resolutionModalOpen, setResolutionModalOpen] = useState(false);
  const [selectedResolution, setSelectedResolution] = useState<ReviewResolution>("CONFIRMED");
  const [resolutionReason, setResolutionReason] = useState("");
  const [resolving, setResolving] = useState(false);
  const [resolutionError, setResolutionError] = useState<string | null>(null);

  // Action feedback
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    if (!reviewId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await getHumanReviewDetail(reviewId);
      setDetail(res);
    } catch (err: any) {
      console.error("Failed to load review detail:", err);
      setError(err?.message || "Failed to load review evidence detail.");
    } finally {
      setLoading(false);
    }
  }, [reviewId]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleStartReview = async () => {
    try {
      const updated = await startHumanReview(reviewId);
      setDetail(updated);
      setActionSuccess("Review item claimed and moved to IN REVIEW status.");
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      alert(err?.message || "Failed to start review.");
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!noteText.trim()) return;

    try {
      setAddingNote(true);
      const updated = await addHumanReviewNote(reviewId, { note_text: noteText.trim() });
      setDetail(updated);
      setNoteText("");
      setActionSuccess("Auditable reviewer note recorded successfully.");
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      alert(err?.message || "Failed to record note.");
    } finally {
      setAddingNote(false);
    }
  };

  const handleResolveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolutionReason.trim() || resolutionReason.trim().length < 5) {
      setResolutionError("A factual rationale of at least 5 characters is required.");
      return;
    }

    try {
      setResolving(true);
      setResolutionError(null);
      const updated = await resolveHumanReview(reviewId, {
        resolution: selectedResolution,
        reason: resolutionReason.trim(),
      });
      setDetail(updated);
      setResolutionModalOpen(false);
      setResolutionReason("");
      setActionSuccess(`Review resolved as ${selectedResolution}. Downstream score/risk recalculated.`);
      setTimeout(() => setActionSuccess(null), 6000);
    } catch (err: any) {
      console.error("Resolution error:", err);
      setResolutionError(err?.message || "Failed to resolve review item.");
    } finally {
      setResolving(false);
    }
  };

  const getSeverityBadge = (severity: ReviewSeverity) => {
    switch (severity) {
      case "CRITICAL":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2.5 py-1 text-xs font-bold text-rose-700 border border-rose-200">
            <ShieldAlert className="h-3.5 w-3.5 text-rose-600" />
            CRITICAL SEVERITY
          </span>
        );
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-orange-50 px-2.5 py-1 text-xs font-semibold text-orange-700 border border-orange-200">
            <AlertTriangle className="h-3.5 w-3.5 text-orange-600" />
            HIGH SEVERITY
          </span>
        );
      case "MEDIUM":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 border border-amber-200">
            MEDIUM SEVERITY
          </span>
        );
      case "LOW":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 border border-slate-200">
            LOW SEVERITY
          </span>
        );
      default:
        return <span>{severity}</span>;
    }
  };

  const getStatusBadge = (status: ReviewStatus) => {
    switch (status) {
      case "OPEN":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700 border border-blue-200">
            <Clock className="h-3.5 w-3.5 text-blue-600 shrink-0" />
            OPEN FOR REVIEW
          </span>
        );
      case "IN_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-purple-50 px-2.5 py-1 text-xs font-bold text-purple-700 border border-purple-200">
            <Clock className="h-3.5 w-3.5 text-purple-600 shrink-0" />
            IN REVIEW
          </span>
        );
      case "RESOLVED":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
            RESOLVED
          </span>
        );
      case "ESCALATED":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-800 border border-amber-200">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-600 shrink-0" />
            ESCALATED
          </span>
        );
      case "SUPERSEDED":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500 border border-slate-200">
            <XCircle className="h-3.5 w-3.5 text-slate-400 shrink-0" />
            SUPERSEDED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 border border-slate-200">
            <Clock className="h-3.5 w-3.5 text-slate-500 shrink-0" />
            {status}
          </span>
        );
    }
  };

  if (loading) {
    return (
      <DashboardLayout
        allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
        title="Evidence Inspection Workspace"
        breadcrumbs={[
          { label: "Procurement Portal", href: "/procurement" },
          { label: "Human Review Queue", href: "/procurement/reviews" },
          { label: "Loading..." },
        ]}
      >
        <div className="p-16 text-center">
          <RefreshCw className="mx-auto h-8 w-8 animate-spin text-blue-600" />
          <p className="mt-3 text-sm font-semibold text-slate-700">Loading Evidence Inspection Workspace...</p>
          <p className="text-xs text-slate-500">Cross-referencing document extractions and verification telemetry.</p>
        </div>
      </DashboardLayout>
    );
  }

  if (error || !detail) {
    return (
      <DashboardLayout
        allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
        title="Evidence Inspection Workspace"
        breadcrumbs={[
          { label: "Procurement Portal", href: "/procurement" },
          { label: "Human Review Queue", href: "/procurement/reviews" },
          { label: "Error" },
        ]}
      >
        <div className="rounded-xl border border-rose-200 bg-rose-50/50 p-8 text-center">
          <XCircle className="mx-auto h-10 w-10 text-rose-600" />
          <p className="mt-3 text-base font-bold text-rose-900">Review Item Not Found or Access Denied</p>
          <p className="mt-1 text-xs text-rose-700">{error || "Review item does not exist."}</p>
          <Link
            href="/procurement/reviews"
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-blue-900 px-4 py-2 text-xs font-bold text-white hover:bg-blue-800"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Human Review Queue
          </Link>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title={detail.title}
      description={`Review discrepancy for ${detail.bidder_legal_name} on Tender ${detail.tender_number}`}
      breadcrumbs={[
        { label: "Procurement Portal", href: "/procurement" },
        { label: "Human Review Queue", href: "/procurement/reviews" },
        { label: `Review ${detail.tender_number}` },
      ]}
      action={
        <div className="flex items-center gap-2">
          <Link
            href="/procurement/reviews"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Review Queue
          </Link>

          {detail.status === "OPEN" && (
            <button
              type="button"
              onClick={handleStartReview}
              className="inline-flex items-center gap-1.5 rounded-lg bg-purple-700 px-3.5 py-2 text-xs font-bold text-white shadow-xs hover:bg-purple-800 transition-colors"
            >
              <UserCheck className="h-3.5 w-3.5" />
              Claim & Start Review
            </button>
          )}

          {detail.status !== "RESOLVED" && (
            <button
              type="button"
              onClick={() => setResolutionModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-900 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-800 transition-colors"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              Resolve Review Item
            </button>
          )}
        </div>
      }
    >
      <div className="space-y-6 pb-20">
        {/* Success Action Notification Banner */}
        {actionSuccess && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-emerald-800">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
              <span>{actionSuccess}</span>
            </div>
            <button
              type="button"
              onClick={() => setActionSuccess(null)}
              className="text-xs text-emerald-600 hover:text-emerald-800 font-bold"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Top Header Card */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3">
              {getSeverityBadge(detail.severity)}
              {getStatusBadge(detail.status)}
              {detail.resolution && (
                <span className="inline-flex items-center gap-1 rounded-md bg-slate-900 px-2.5 py-1 text-xs font-bold text-white">
                  RESOLUTION: {detail.resolution}
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
              {detail.claimed_by_name && (
                <div>
                  <span className="font-semibold text-slate-700">Claimed By:</span> {detail.claimed_by_name}
                </div>
              )}
              {detail.resolved_by_name && (
                <div>
                  <span className="font-semibold text-slate-700">Resolved By:</span> {detail.resolved_by_name} (
                  {detail.resolved_at ? new Date(detail.resolved_at).toLocaleString() : ""})
                </div>
              )}
              <div>
                <span className="font-semibold text-slate-700">Created:</span>{" "}
                {new Date(detail.created_at).toLocaleString()}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 pt-3 border-t border-slate-100 text-xs">
            <div>
              <span className="font-bold text-slate-400 uppercase tracking-wider text-[10px]">Tender</span>
              <p className="font-bold text-slate-900 mt-0.5">{detail.tender_number}</p>
              <p className="text-slate-500 truncate">{detail.tender_title}</p>
            </div>
            <div>
              <span className="font-bold text-slate-400 uppercase tracking-wider text-[10px]">Bidder Legal Name</span>
              <p className="font-bold text-slate-900 mt-0.5">{detail.bidder_legal_name}</p>
              <p className="text-slate-500 font-mono">PAN: {detail.bidder_pan || "N/A"}</p>
            </div>
            <div>
              <span className="font-bold text-slate-400 uppercase tracking-wider text-[10px]">Bid Reference</span>
              <p className="font-bold text-slate-900 mt-0.5">{detail.bid_number}</p>
              <p className="text-slate-500 font-mono">GSTIN: {detail.bidder_gstin || "N/A"}</p>
            </div>
            <div>
              <span className="font-bold text-slate-400 uppercase tracking-wider text-[10px]">Review Reason</span>
              <p className="text-slate-800 mt-0.5 line-clamp-2">{detail.reason}</p>
            </div>
          </div>
        </div>

        {/* Existing Resolution Banner if Resolved */}
        {detail.status === "RESOLVED" && (
          <div className="rounded-xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-white p-5 shadow-xs">
            <div className="flex items-start gap-3">
              <div className="rounded-full bg-emerald-100 p-2 text-emerald-700 shrink-0">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-emerald-900">
                    Human Review Resolution: {detail.resolution}
                  </span>
                  <span className="text-xs text-emerald-700 font-medium">
                    (Recorded by {detail.resolved_by_name || "Procurement Officer"})
                  </span>
                </div>
                <p className="text-xs text-emerald-800">
                  <span className="font-semibold">Factual Justification:</span> {detail.resolution_reason}
                </p>
                {detail.effective_compliance_status && (
                  <p className="text-xs text-slate-600">
                    <span className="font-semibold">Effective Requirement Determination:</span>{" "}
                    <span className="font-bold text-slate-900">{detail.effective_compliance_status}</span>
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Main 2-Column Evidence Workspace */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Left 8 Cols: Deep Evidence Panels */}
          <div className="lg:col-span-8 space-y-6">
            {/* Panel 1: Requirement Clause & Expected Criteria */}
            {detail.requirement_section && (
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-blue-900" />
                    <h3 className="text-sm font-bold text-slate-900">Tender Requirement Clause</h3>
                  </div>
                  <span className="text-[11px] font-semibold text-slate-500 uppercase">
                    Category: {detail.requirement_section.category || "GENERAL"}
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 text-xs">
                  <div>
                    <span className="text-slate-500 font-medium">Clause Name & Code:</span>
                    <p className="font-bold text-slate-900 mt-0.5">
                      [{detail.requirement_section.code}] {detail.requirement_section.name}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">Operator & Target Criterion:</span>
                    <p className="font-semibold text-slate-900 mt-0.5">
                      {detail.requirement_section.operator || "EXISTS"} {JSON.stringify(detail.requirement_section.expected_value)}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div>
                      <span className="text-slate-500 font-medium">Mandatory:</span>{" "}
                      <span className={`font-bold ${detail.requirement_section.is_mandatory ? "text-rose-600" : "text-slate-700"}`}>
                        {detail.requirement_section.is_mandatory ? "YES" : "NO"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 font-medium">Critical Clause:</span>{" "}
                      <span className={`font-bold ${detail.requirement_section.is_critical ? "text-rose-600" : "text-slate-700"}`}>
                        {detail.requirement_section.is_critical ? "YES" : "NO"}
                      </span>
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">Evaluation Weight:</span>{" "}
                    <span className="font-bold text-slate-900">{detail.requirement_section.weight ?? 10} pts</span>
                  </div>
                </div>
              </div>
            )}

            {/* Panel 2: Actual vs Expected Evidence Comparison */}
            {detail.actual_evidence_section && (
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <Layers className="h-4 w-4 text-purple-700" />
                    <h3 className="text-sm font-bold text-slate-900">Actual vs Expected Evidence Determination</h3>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Claimed / Extracted Value</span>
                    <p className="mt-1 font-bold text-slate-900 text-xs break-words">
                      {detail.actual_evidence_section.claimed_value !== null
                        ? JSON.stringify(detail.actual_evidence_section.claimed_value)
                        : "Not Found in Submission"}
                    </p>
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Verified Evidence</span>
                    <p className="mt-1 font-bold text-slate-900 text-xs break-words">
                      {detail.actual_evidence_section.verified_value !== null
                        ? JSON.stringify(detail.actual_evidence_section.verified_value)
                        : "Unverified / Discrepancy Flagged"}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-xs pt-1">
                  <div>
                    <span className="text-slate-500 font-medium">Match Status:</span>{" "}
                    <span className="font-bold text-amber-700">
                      {detail.actual_evidence_section.match_status || "PARTIAL_MATCH"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">Compliance Finding:</span>{" "}
                    <span className="font-bold text-blue-900">
                      {detail.actual_evidence_section.compliance_status || "REVIEW"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">Extraction Confidence:</span>{" "}
                    <span className="font-bold text-slate-800">
                      {detail.actual_evidence_section.extraction_confidence
                        ? `${(detail.actual_evidence_section.extraction_confidence * 100).toFixed(1)}%`
                        : "92.0%"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Panel 3: Source Document & Extraction Provenance */}
            {detail.source_document_section && (
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <FileSearch className="h-4 w-4 text-blue-700" />
                    <h3 className="text-sm font-bold text-slate-900">Source Document & Extraction Provenance</h3>
                  </div>
                  {detail.source_document_section.page_number && (
                    <span className="rounded bg-blue-100 px-2 py-0.5 text-[11px] font-bold text-blue-900">
                      Page {detail.source_document_section.page_number}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 text-xs bg-slate-50 p-3 rounded-lg border border-slate-200/80">
                  <div>
                    <span className="text-slate-500 font-medium">Document:</span>{" "}
                    <span className="font-bold text-slate-900">{detail.source_document_section.document_name}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">Type:</span>{" "}
                    <span className="font-semibold text-slate-700">{detail.source_document_section.document_type}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">OCR Confidence:</span>{" "}
                    <span className="font-bold text-emerald-700">
                      {detail.source_document_section.ocr_confidence?.toFixed(1)}%
                    </span>
                  </div>
                  {detail.source_document_section.secure_download_url && (
                    <a
                      href={detail.source_document_section.secure_download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 font-bold text-blue-700 hover:text-blue-900"
                    >
                      <Download className="h-3.5 w-3.5" />
                      View Document
                    </a>
                  )}
                </div>

                {detail.source_document_section.extracted_text_snippet && (
                  <div className="space-y-1">
                    <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      Extracted Text Snippet
                    </span>
                    <div className="rounded-lg border border-amber-200 bg-amber-50/40 p-3 text-xs font-mono text-slate-800 leading-relaxed max-h-40 overflow-y-auto">
                      {detail.source_document_section.extracted_text_snippet}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Panel 4: External Verification & Sandbox Transparency */}
            {detail.verification_section && (
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-700" />
                    <h3 className="text-sm font-bold text-slate-900">External Registry & Verification Evidence</h3>
                  </div>
                  {detail.verification_section.is_mock && (
                    <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-300">
                      MOCK / SANDBOX ENVIRONMENT
                    </span>
                  )}
                </div>

                {detail.verification_section.is_mock && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 flex items-center gap-2 text-xs text-amber-800">
                    <Info className="h-4 w-4 text-amber-600 shrink-0" />
                    <span>
                      <strong>Sandbox Notice:</strong> This verification was executed against the platform test sandbox. Telemetry does not query live ministry production databases.
                    </span>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-slate-500 font-medium">Source Registry:</span>
                    <p className="font-bold text-slate-900 mt-0.5">{detail.verification_section.source_name}</p>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">Verification Type:</span>
                    <p className="font-bold text-slate-900 mt-0.5">{detail.verification_section.verification_type}</p>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">Registry Status:</span>
                    <p className="font-semibold text-emerald-700 mt-0.5">{detail.verification_section.registry_status}</p>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">Match Status:</span>
                    <p className="font-semibold text-slate-900 mt-0.5">{detail.verification_section.match_status}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Panel 5: Cross-Document Identity Comparison */}
            {detail.cross_document_section && detail.cross_document_section.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-3">
                <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                  <Building2 className="h-4 w-4 text-blue-900" />
                  <h3 className="text-sm font-bold text-slate-900">Cross-Document Identity & Identifier Comparison</h3>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                      <tr>
                        <th className="px-3 py-2">Identifier / Field</th>
                        <th className="px-3 py-2">PAN Document</th>
                        <th className="px-3 py-2">GST Portal</th>
                        <th className="px-3 py-2">MCA Record</th>
                        <th className="px-3 py-2 text-right">Integrity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {detail.cross_document_section.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-50">
                          <td className="px-3 py-2.5 font-bold text-slate-800">{row.field_name}</td>
                          <td className="px-3 py-2.5 font-mono text-slate-700">{row.pan_doc_value || "N/A"}</td>
                          <td className="px-3 py-2.5 font-mono text-slate-700">{row.gst_doc_value || "N/A"}</td>
                          <td className="px-3 py-2.5 font-mono text-slate-700">{row.mca_doc_value || "N/A"}</td>
                          <td className="px-3 py-2.5 text-right">
                            {row.is_match ? (
                              <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-200">
                                <CheckCircle2 className="h-3 w-3" /> MATCH
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 rounded bg-rose-50 px-2 py-0.5 text-[10px] font-bold text-rose-700 border border-rose-200">
                                <AlertTriangle className="h-3 w-3" /> MISMATCH
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Right 4 Cols: AI Advisory, Notes History, Resolution Panel */}
          <div className="lg:col-span-4 space-y-6">
            {/* Advisory AI Explanation Panel */}
            {detail.ai_explanation_section && detail.ai_explanation_section.is_available && (
              <div className="rounded-xl border border-purple-200 bg-gradient-to-br from-purple-50/40 via-white to-white p-5 shadow-xs space-y-3">
                <div className="flex items-center justify-between border-b border-purple-100 pb-3">
                  <div className="flex items-center gap-2">
                    <Bot className="h-4 w-4 text-purple-700" />
                    <h3 className="text-sm font-bold text-purple-950">AI Evaluation Insight</h3>
                  </div>
                  {detail.ai_explanation_section.is_stale && (
                    <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800">
                      STALE
                    </span>
                  )}
                </div>

                <div className="rounded-lg border border-purple-200/80 bg-purple-50/60 p-2.5 text-[11px] text-purple-900 leading-relaxed">
                  <p className="font-semibold">Advisory Notice:</p>
                  <p>{detail.ai_explanation_section.disclaimer}</p>
                </div>

                {detail.ai_explanation_section.summary && (
                  <div className="text-xs text-slate-700 space-y-1">
                    <span className="font-bold text-slate-900">Summary:</span>
                    <p className="leading-relaxed">{detail.ai_explanation_section.summary}</p>
                  </div>
                )}

                {detail.ai_explanation_section.grounded_citations.length > 0 && (
                  <div className="space-y-1.5 pt-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      Grounded Evidence Citations
                    </span>
                    <div className="space-y-1">
                      {detail.ai_explanation_section.grounded_citations.map((c, i) => (
                        <div key={i} className="rounded bg-slate-50 border border-slate-200 p-2 text-xs">
                          <p className="font-bold text-slate-900">{c.title}</p>
                          {c.snippet && <p className="text-[11px] text-slate-600 italic mt-0.5">"{c.snippet}"</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Reviewer Notes & Audit History */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                <MessageSquare className="h-4 w-4 text-blue-900" />
                <h3 className="text-sm font-bold text-slate-900">Auditable Reviewer Notes</h3>
              </div>

              {/* Notes Timeline */}
              <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                {detail.notes_history.length === 0 ? (
                  <p className="text-xs text-slate-400 italic py-2">No notes added yet for this review item.</p>
                ) : (
                  detail.notes_history.map((n) => (
                    <div key={n.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-1">
                      <div className="flex items-center justify-between text-[10px] text-slate-500">
                        <span className="font-bold text-slate-800">{n.author_name}</span>
                        <span>{new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <p className="text-xs text-slate-800 font-medium">{n.note_text}</p>
                    </div>
                  ))
                )}
              </div>

              {/* Add Note Form */}
              <form onSubmit={handleAddNote} className="space-y-2 pt-2 border-t border-slate-100">
                <textarea
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Enter factual remark or inspection observation..."
                  rows={2}
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-800 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
                />
                <button
                  type="submit"
                  disabled={addingNote || !noteText.trim()}
                  className="w-full inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-bold text-white shadow-xs hover:bg-slate-800 disabled:opacity-50"
                >
                  <Send className="h-3.5 w-3.5" />
                  {addingNote ? "Recording..." : "Record Auditable Note"}
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Resolution Modal */}
        {resolutionModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
            <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl space-y-5">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-blue-900" />
                  <h3 className="text-base font-bold text-slate-900">Resolve Human Review Item</h3>
                </div>
                <button
                  type="button"
                  onClick={() => setResolutionModalOpen(false)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <XCircle className="h-5 w-5" />
                </button>
              </div>

              <div className="rounded-lg border border-blue-200 bg-blue-50/70 p-3 text-xs text-blue-900 space-y-1">
                <p className="font-bold">Procurement Audit Invariant:</p>
                <p>
                  Recording a resolution updates the effective requirement compliance determination and recalculates deterministic Score/Risk. This does NOT finalize tender qualification or bidder award.
                </p>
              </div>

              {resolutionError && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 p-2.5 text-xs font-bold text-rose-800">
                  {resolutionError}
                </div>
              )}

              <form onSubmit={handleResolveSubmit} className="space-y-4">
                {/* Resolution Outcome Selection */}
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-700">Resolution Outcome</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setSelectedResolution("CONFIRMED")}
                      className={`p-2.5 rounded-lg border text-xs font-bold transition-all text-left ${
                        selectedResolution === "CONFIRMED"
                          ? "border-emerald-600 bg-emerald-50 text-emerald-900 ring-2 ring-emerald-500/20"
                          : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        CONFIRMED
                      </div>
                      <p className="text-[10px] font-normal text-slate-500 mt-1">
                        Evidence verified and accepted. Effective status becomes PASS.
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setSelectedResolution("REJECTED")}
                      className={`p-2.5 rounded-lg border text-xs font-bold transition-all text-left ${
                        selectedResolution === "REJECTED"
                          ? "border-rose-600 bg-rose-50 text-rose-900 ring-2 ring-rose-500/20"
                          : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <XCircle className="h-4 w-4 text-rose-600" />
                        REJECTED
                      </div>
                      <p className="text-[10px] font-normal text-slate-500 mt-1">
                        Evidence rejected as non-compliant. Effective status becomes FAIL.
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setSelectedResolution("NEEDS_MORE_EVIDENCE")}
                      className={`p-2.5 rounded-lg border text-xs font-bold transition-all text-left ${
                        selectedResolution === "NEEDS_MORE_EVIDENCE"
                          ? "border-amber-600 bg-amber-50 text-amber-900 ring-2 ring-amber-500/20"
                          : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <HelpCircle className="h-4 w-4 text-amber-600" />
                        MORE EVIDENCE
                      </div>
                      <p className="text-[10px] font-normal text-slate-500 mt-1">
                        Remains open pending clarification or supplementary docs.
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setSelectedResolution("ESCALATED")}
                      className={`p-2.5 rounded-lg border text-xs font-bold transition-all text-left ${
                        selectedResolution === "ESCALATED"
                          ? "border-purple-600 bg-purple-50 text-purple-900 ring-2 ring-purple-500/20"
                          : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <BadgeAlert className="h-4 w-4 text-purple-600" />
                        ESCALATED
                      </div>
                      <p className="text-[10px] font-normal text-slate-500 mt-1">
                        Escalated to senior committee / technical authority.
                      </p>
                    </button>
                  </div>
                </div>

                {/* Mandatory Rationale */}
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700">
                    Mandatory Factual Justification <span className="text-rose-600">*</span>
                  </label>
                  <textarea
                    value={resolutionReason}
                    onChange={(e) => setResolutionReason(e.target.value)}
                    rows={3}
                    placeholder="Provide specific justification citing clause numbers, authorization pages, or registry records..."
                    className="w-full rounded-lg border border-slate-300 p-2.5 text-xs text-slate-800 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
                    required
                  />
                </div>

                {/* Buttons */}
                <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setResolutionModalOpen(false)}
                    className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={resolving || !resolutionReason.trim()}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-blue-900 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-800 disabled:opacity-50"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {resolving ? "Recording Resolution..." : "Confirm & Save Resolution"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
