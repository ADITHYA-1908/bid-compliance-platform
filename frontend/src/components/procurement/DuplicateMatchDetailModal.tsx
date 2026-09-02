"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  AlertTriangle,
  FileText,
  CheckCircle2,
  XCircle,
  Copy,
  Hash,
  ShieldCheck,
  ShieldAlert,
  Loader2,
  ExternalLink,
} from "lucide-react";
import {
  DuplicateMatchDetail,
  DuplicateReviewRequest,
} from "@/types/duplicate_detection";
import { getDuplicateMatchDetail, submitDuplicateReview } from "@/lib/api/duplicate_detection";

interface DuplicateMatchDetailModalProps {
  matchId: string;
  isOpen: boolean;
  onClose: () => void;
  onReviewed?: () => void;
}

export function DuplicateMatchDetailModal({
  matchId,
  isOpen,
  onClose,
  onReviewed,
}: DuplicateMatchDetailModalProps) {
  const [detail, setDetail] = useState<DuplicateMatchDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Review Form State
  const [resolution, setResolution] = useState<"CONFIRMED_BENIGN" | "CONFIRMED_REUSE" | "DISMISSED">("CONFIRMED_BENIGN");
  const [reviewerNotes, setReviewerNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && matchId) {
      loadDetail();
    }
  }, [isOpen, matchId]);

  async function loadDetail() {
    setLoading(true);
    setError(null);
    setSubmitSuccess(null);
    try {
      const res = await getDuplicateMatchDetail(matchId);
      setDetail(res);
      if (res.reviewer_notes) {
        setReviewerNotes(res.reviewer_notes);
      }
      if (res.status === "CONFIRMED_REUSE" || res.status === "CONFIRMED_BENIGN" || res.status === "DISMISSED") {
        setResolution(res.status);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load duplicate match details.");
    } finally {
      setLoading(false);
    }
  }

  async function handleReviewSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!detail) return;

    setSubmitting(true);
    setError(null);
    try {
      const payload: DuplicateReviewRequest = {
        resolution,
        reviewer_notes: reviewerNotes.trim() || undefined,
      };
      const res = await submitDuplicateReview(detail.id, payload);
      setSubmitSuccess(res.message);
      loadDetail();
      if (onReviewed) onReviewed();
    } catch (err: any) {
      setError(err?.message || "Failed to submit review decision.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 overflow-y-auto font-body">
      <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 text-slate-900">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-700">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-heading text-lg font-bold text-slate-900 flex items-center gap-2">
                Side-by-Side Duplicate Document Inspection
              </h2>
              <p className="text-xs text-slate-500">
                Multi-signal cross-bidder comparison and human review decision workspace
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="flex flex-col items-center justify-center py-20 space-y-3">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
              <p className="text-sm text-slate-400">Loading document comparison telemetry...</p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-start gap-3">
              <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-400" />
              <div>{error}</div>
            </div>
          )}

          {submitSuccess && (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5 text-emerald-400" />
              <div>{submitSuccess}</div>
            </div>
          )}

          {detail && !loading && (
            <>
              {/* Match Signal Telemetry Banner */}
              <div className="p-5 rounded-xl bg-gradient-to-r from-slate-800/80 via-slate-800/50 to-indigo-950/40 border border-slate-700/80 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                      detail.match_type === "EXACT_FILE_DUPLICATE"
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                        : detail.match_type === "CONTENT_DUPLICATE"
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                        : detail.match_type === "STRUCTURED_DATA_MATCH"
                        ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                        : "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                    }`}>
                      {detail.match_type.replace(/_/g, " ")}
                    </span>
                    <span className="text-xs text-slate-400">
                      Overall Confidence: <strong className="text-slate-200 text-sm">{Math.round(detail.overall_confidence * 100)}%</strong>
                    </span>
                  </div>

                  {/* Status Badge */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Status:</span>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                      detail.status === "CONFIRMED_REUSE"
                        ? "bg-rose-600/20 text-rose-400 border border-rose-600/40"
                        : detail.status === "CONFIRMED_BENIGN"
                        ? "bg-emerald-600/20 text-emerald-400 border border-emerald-600/40"
                        : detail.status === "DISMISSED"
                        ? "bg-slate-700 text-slate-300"
                        : "bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse"
                    }`}>
                      {detail.status.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>

                {/* Micro Metric Pills */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-700/50">
                    <div className="text-[10px] text-slate-400 uppercase tracking-wider">File SHA-256 Hash</div>
                    <div className={`text-xs font-semibold mt-1 flex items-center gap-1.5 ${detail.file_hash_match ? "text-rose-400" : "text-slate-400"}`}>
                      {detail.file_hash_match ? <CheckCircle2 className="w-3.5 h-3.5 text-rose-400" /> : <XCircle className="w-3.5 h-3.5" />}
                      {detail.file_hash_match ? "Exact Match" : "Different"}
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-700/50">
                    <div className="text-[10px] text-slate-400 uppercase tracking-wider">Normalized Content</div>
                    <div className={`text-xs font-semibold mt-1 flex items-center gap-1.5 ${detail.content_hash_match ? "text-amber-400" : "text-slate-400"}`}>
                      {detail.content_hash_match ? <CheckCircle2 className="w-3.5 h-3.5 text-amber-400" /> : <XCircle className="w-3.5 h-3.5" />}
                      {detail.content_hash_match ? "Exact Content" : "Different"}
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-700/50">
                    <div className="text-[10px] text-slate-400 uppercase tracking-wider">Structured Fields</div>
                    <div className="text-xs font-semibold text-purple-300 mt-1">
                      {Math.round(detail.structured_field_match_score * 100)}% Match
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-700/50">
                    <div className="text-[10px] text-slate-400 uppercase tracking-wider">Text Similarity</div>
                    <div className="text-xs font-semibold text-blue-300 mt-1">
                      {Math.round(detail.text_similarity_score * 100)}% Match
                    </div>
                  </div>
                </div>
              </div>

              {/* Side-by-Side Metadata Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Document A Card */}
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-xs font-bold">Doc A</span>
                      <span className="text-sm font-semibold text-slate-200">{detail.document_a.bidder_name}</span>
                    </div>
                    <span className="text-xs text-slate-400">Bid: {detail.document_a.bid_number || "N/A"}</span>
                  </div>

                  <div className="space-y-1.5 text-xs text-slate-300">
                    <div className="flex justify-between"><span className="text-slate-400">Document Name:</span> <span className="font-medium text-slate-200">{detail.document_a.document_name}</span></div>
                    <div className="flex justify-between"><span className="text-slate-400">Filename:</span> <span className="font-mono text-slate-300">{detail.document_a.original_filename}</span></div>
                    <div className="flex justify-between"><span className="text-slate-400">File Size:</span> <span>{(detail.document_a.file_size / 1024).toFixed(1)} KB</span></div>
                    <div className="flex justify-between items-center"><span className="text-slate-400">SHA-256:</span> <span className="font-mono text-[10px] text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded">{detail.document_a.file_hash?.slice(0, 16)}...</span></div>
                  </div>

                  {detail.document_a.text_snippet && (
                    <div className="mt-3 p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-[11px] text-slate-300 font-mono line-clamp-3">
                      {detail.document_a.text_snippet}
                    </div>
                  )}
                </div>

                {/* Document B Card */}
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 text-xs font-bold">Doc B</span>
                      <span className="text-sm font-semibold text-slate-200">{detail.document_b.bidder_name}</span>
                    </div>
                    <span className="text-xs text-slate-400">Bid: {detail.document_b.bid_number || "N/A"}</span>
                  </div>

                  <div className="space-y-1.5 text-xs text-slate-300">
                    <div className="flex justify-between"><span className="text-slate-400">Document Name:</span> <span className="font-medium text-slate-200">{detail.document_b.document_name}</span></div>
                    <div className="flex justify-between"><span className="text-slate-400">Filename:</span> <span className="font-mono text-slate-300">{detail.document_b.original_filename}</span></div>
                    <div className="flex justify-between"><span className="text-slate-400">File Size:</span> <span>{(detail.document_b.file_size / 1024).toFixed(1)} KB</span></div>
                    <div className="flex justify-between items-center"><span className="text-slate-400">SHA-256:</span> <span className="font-mono text-[10px] text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded">{detail.document_b.file_hash?.slice(0, 16)}...</span></div>
                  </div>

                  {detail.document_b.text_snippet && (
                    <div className="mt-3 p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-[11px] text-slate-300 font-mono line-clamp-3">
                      {detail.document_b.text_snippet}
                    </div>
                  )}
                </div>
              </div>

              {/* Structured Fields Comparison Table */}
              {detail.matched_fields_details && detail.matched_fields_details.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <Hash className="w-3.5 h-3.5 text-indigo-400" />
                    Identical Extracted Structured Fields
                  </h3>
                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 overflow-hidden">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 font-semibold">
                        <tr>
                          <th className="py-2.5 px-4">Field Attribute</th>
                          <th className="py-2.5 px-4">{detail.document_a.bidder_name} (Doc A)</th>
                          <th className="py-2.5 px-4">{detail.document_b.bidder_name} (Doc B)</th>
                          <th className="py-2.5 px-4 text-right">Match Signal</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {detail.matched_fields_details.map((field) => (
                          <tr key={field.field_key} className="hover:bg-slate-900/30">
                            <td className="py-2.5 px-4 font-medium text-slate-300">{field.label}</td>
                            <td className="py-2.5 px-4 font-mono text-emerald-400 font-semibold bg-emerald-950/20">{field.value_a || "—"}</td>
                            <td className="py-2.5 px-4 font-mono text-emerald-400 font-semibold bg-emerald-950/20">{field.value_b || "—"}</td>
                            <td className="py-2.5 px-4 text-right">
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                                <CheckCircle2 className="w-3 h-3" /> Exact
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Human Review Decision Panel */}
              <div className="p-5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-indigo-400" />
                    Procurement Officer Evaluation Decision
                  </h3>
                  {detail.reviewed_by_name && (
                    <span className="text-xs text-slate-400">
                      Reviewed by <strong>{detail.reviewed_by_name}</strong> on {new Date(detail.reviewed_at || "").toLocaleDateString()}
                    </span>
                  )}
                </div>

                <form onSubmit={handleReviewSubmit} className="space-y-4">
                  {/* Resolution Choice Buttons */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <button
                      type="button"
                      onClick={() => setResolution("CONFIRMED_BENIGN")}
                      className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
                        resolution === "CONFIRMED_BENIGN"
                          ? "bg-emerald-950/40 border-emerald-500 text-emerald-200 ring-1 ring-emerald-500"
                          : "bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      <div className="font-bold text-xs flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        Confirmed Benign
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1">
                        Legitimate co-submission, authorized multi-dealer certificate, or common public template.
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setResolution("CONFIRMED_REUSE")}
                      className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
                        resolution === "CONFIRMED_REUSE"
                          ? "bg-rose-950/40 border-rose-500 text-rose-200 ring-1 ring-rose-500"
                          : "bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      <div className="font-bold text-xs flex items-center gap-1.5">
                        <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                        Confirmed Unauthorized Reuse
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1">
                        Confirmed illicit document reuse between competing bidder submissions.
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setResolution("DISMISSED")}
                      className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
                        resolution === "DISMISSED"
                          ? "bg-slate-800 border-slate-600 text-slate-200 ring-1 ring-slate-500"
                          : "bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      <div className="font-bold text-xs flex items-center gap-1.5">
                        <XCircle className="w-3.5 h-3.5 text-slate-400" />
                        Dismiss (False Alarm)
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1">
                        Uncorrelated coincidence or non-actionable match.
                      </p>
                    </button>
                  </div>

                  {/* Reviewer Notes Textarea */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                      Officer Justification & Review Notes (Auditable)
                    </label>
                    <textarea
                      rows={3}
                      value={reviewerNotes}
                      onChange={(e) => setReviewerNotes(e.target.value)}
                      placeholder="Record detailed observations, verified OEM authorization context, or justification for this decision..."
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>

                  {/* Submit Button */}
                  <div className="flex justify-end gap-3 pt-2">
                    <button
                      type="button"
                      onClick={onClose}
                      className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                    >
                      Close
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 transition-all flex items-center gap-2 shadow-lg shadow-indigo-600/20"
                    >
                      {submitting ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Saving Review...
                        </>
                      ) : (
                        "Record Human Decision"
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
