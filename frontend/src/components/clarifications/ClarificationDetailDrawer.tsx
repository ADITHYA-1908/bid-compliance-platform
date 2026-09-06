"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Clock,
  AlertTriangle,
  FileText,
  Send,
  Upload,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Eye,
  Calendar,
  User,
  Building2,
  Layers,
  Sparkles,
  RefreshCw,
  FileCheck,
  Ban,
  ArrowRight,
} from "lucide-react";
import {
  ClarificationPriority,
  ClarificationRequestDetailResponse,
  ClarificationResponseCreate,
  ClarificationStatus,
} from "@/types/clarification";
import { bidderClarificationsApi, procurementClarificationsApi } from "@/lib/api/clarifications";
import { ResolveClarificationModal } from "./ResolveClarificationModal";

interface ClarificationDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  clarificationId: string | null;
  userRole?: "BIDDER" | "PROCUREMENT_OFFICER" | "ADMIN" | string;
  token?: string;
  onUpdate?: () => void;
}

const STATUS_CONFIG: Record<
  ClarificationStatus,
  { label: string; bg: string; text: string; border: string; icon: React.ElementType }
> = {
  DRAFT: { label: "Draft", bg: "bg-slate-100", text: "text-slate-700", border: "border-slate-200", icon: Clock },
  SENT: { label: "Sent to Bidder", bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200", icon: AlertTriangle },
  VIEWED: { label: "Viewed by Bidder", bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-200", icon: AlertTriangle },
  RESPONDED: { label: "Responded", bg: "bg-amber-50", text: "text-amber-800", border: "border-amber-200", icon: Clock },
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
  LOW: { label: "Low Priority", bg: "bg-slate-100 text-slate-700" },
  NORMAL: { label: "Normal Priority", bg: "bg-blue-100 text-blue-800" },
  HIGH: { label: "High Priority", bg: "bg-amber-100 text-amber-800" },
  URGENT: { label: "Urgent", bg: "bg-rose-100 text-rose-800 font-bold" },
};

export const ClarificationDetailDrawer: React.FC<ClarificationDetailDrawerProps> = ({
  isOpen,
  onClose,
  clarificationId,
  userRole = "PROCUREMENT_OFFICER",
  token,
  onUpdate,
}) => {
  const [data, setData] = useState<ClarificationRequestDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Bidder reply state
  const [responseText, setResponseText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isReplacement, setIsReplacement] = useState(false);
  const [isReplying, setIsReplying] = useState(false);
  const [replySuccess, setReplySuccess] = useState(false);

  // Procurement actions state
  const [isResolveOpen, setIsResolveOpen] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isSendingDraft, setIsSendingDraft] = useState(false);
  const [isReevaluating, setIsReevaluating] = useState(false);
  const [reevalResult, setReevalResult] = useState<any | null>(null);

  const isBidder = userRole === "BIDDER";
  const isOfficer = userRole === "PROCUREMENT_OFFICER" || userRole === "ADMIN";

  const fetchDetail = async () => {
    if (!clarificationId) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = isBidder
        ? await bidderClarificationsApi.getClarification(clarificationId, token)
        : await procurementClarificationsApi.getClarification(clarificationId, token);
      setData(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load clarification details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && clarificationId) {
      fetchDetail();
      setResponseText("");
      setSelectedFile(null);
      setIsReplacement(false);
      setReplySuccess(false);
      setReevalResult(null);
    }
  }, [isOpen, clarificationId]);

  if (!isOpen) return null;

  // Handle bidder reply submission
  const handleBidderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clarificationId || !responseText.trim()) return;

    setIsReplying(true);
    setErrorMsg(null);

    try {
      let attachedDocId: string | null = null;

      // If a file is selected, upload it first
      if (selectedFile) {
        const uploadRes = await bidderClarificationsApi.uploadSupportingDocument(
          clarificationId,
          selectedFile,
          "SUPPORTING_EVIDENCE",
          isReplacement,
          data?.related_document_id || undefined,
          token
        );
        attachedDocId = uploadRes.document_id;
      }

      // Submit response
      const payload: ClarificationResponseCreate = {
        response_text: responseText.trim(),
        attached_document_id: attachedDocId,
        is_replacement_document: isReplacement,
        replaced_document_id: isReplacement ? data?.related_document_id : null,
      };

      await bidderClarificationsApi.respondToClarification(clarificationId, payload, token);
      setReplySuccess(true);
      setResponseText("");
      setSelectedFile(null);
      await fetchDetail();
      if (onUpdate) onUpdate();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit response");
    } finally {
      setIsReplying(false);
    }
  };

  // Officer action: Send draft
  const handleSendDraft = async () => {
    if (!clarificationId) return;
    setIsSendingDraft(true);
    try {
      await procurementClarificationsApi.sendClarification(clarificationId, token);
      await fetchDetail();
      if (onUpdate) onUpdate();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to send clarification");
    } finally {
      setIsSendingDraft(false);
    }
  };

  // Officer action: Mark Under Review
  const handleMarkUnderReview = async () => {
    if (!clarificationId) return;
    try {
      await procurementClarificationsApi.markUnderReview(clarificationId, token);
      await fetchDetail();
      if (onUpdate) onUpdate();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to mark under review");
    }
  };

  // Officer action: Cancel
  const handleCancelClarification = async () => {
    if (!clarificationId) return;
    const confirmCancel = window.confirm("Are you sure you want to cancel this clarification request?");
    if (!confirmCancel) return;

    setIsCancelling(true);
    try {
      await procurementClarificationsApi.cancelClarification(
        clarificationId,
        "Cancelled by Procurement Officer",
        token
      );
      await fetchDetail();
      if (onUpdate) onUpdate();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to cancel clarification");
    } finally {
      setIsCancelling(false);
    }
  };

  // Officer action: Re-evaluate
  const handleReevaluate = async () => {
    if (!clarificationId) return;
    setIsReevaluating(true);
    try {
      const res = await procurementClarificationsApi.reevaluateEvidence(clarificationId, token);
      setReevalResult(res);
      if (onUpdate) onUpdate();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to re-evaluate evidence");
    } finally {
      setIsReevaluating(false);
    }
  };

  const statusObj = data ? STATUS_CONFIG[data.status] || STATUS_CONFIG.DRAFT : STATUS_CONFIG.DRAFT;
  const priorityObj = data ? PRIORITY_CONFIG[data.priority] || PRIORITY_CONFIG.NORMAL : PRIORITY_CONFIG.NORMAL;

  const isClosedOrResolved = data?.status === "RESOLVED" || data?.status === "CLOSED" || data?.status === "CANCELLED";

  return (
    <>
      <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/50 backdrop-blur-xs">
        <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
          <div className="w-screen max-w-2xl bg-white shadow-2xl border-l border-slate-200 flex flex-col">
            {/* Header */}
            <div className="border-b border-slate-100 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-6 text-white">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-bold border ${statusObj.bg} ${statusObj.text} ${statusObj.border}`}>
                      {React.createElement(statusObj.icon, { className: "h-3 w-3 shrink-0" })}
                      {statusObj.label}
                    </span>
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${priorityObj.bg}`}>
                      {priorityObj.label}
                    </span>
                    {data?.is_overdue && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-rose-600 px-2.5 py-0.5 text-xs font-bold text-white animate-pulse">
                        <Clock className="h-3 w-3" /> OVERDUE
                      </span>
                    )}
                  </div>
                  <h2 className="text-lg font-bold leading-snug text-white">
                    {data ? data.subject : "Clarification Request"}
                  </h2>
                  <p className="text-xs text-indigo-200/80 mt-1">
                    {data?.tender_title} • Bid: {data?.bid_number}
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {loading && (
                <div className="flex items-center justify-center py-20">
                  <div className="h-8 w-8 animate-spin rounded-full border-3 border-indigo-600 border-t-transparent" />
                </div>
              )}

              {errorMsg && (
                <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {data && !loading && (
                <>
                  {/* Meta info strip */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 rounded-xl bg-slate-50 border border-slate-200 p-3.5 text-xs">
                    <div>
                      <span className="text-slate-500 block">Requested By</span>
                      <span className="font-semibold text-slate-900">{data.created_by_name || "Procurement Officer"}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Bidder Organization</span>
                      <span className="font-semibold text-slate-900">{data.bidder_organization_name}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Response Deadline</span>
                      <span className={`font-semibold ${data.is_overdue ? "text-rose-600 font-bold" : "text-slate-900"}`}>
                        {data.due_date ? new Date(data.due_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "No deadline"}
                      </span>
                    </div>
                  </div>

                  {/* Context Linkages */}
                  {(data.related_requirement_code || data.related_document_name || data.related_rule_version_number) && (
                    <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-3.5 text-xs space-y-1.5">
                      <div className="font-bold text-indigo-950 flex items-center gap-1.5">
                        <Layers className="h-3.5 w-3.5 text-indigo-600" /> Linked Compliance Context
                      </div>
                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        {data.related_requirement_code && (
                          <span className="rounded-md bg-white border border-indigo-200 px-2 py-0.5 font-medium text-indigo-700">
                            Requirement: <strong>[{data.related_requirement_code}]</strong>
                            {data.related_rule_version_number ? ` (Version ${data.related_rule_version_number})` : ""}
                          </span>
                        )}
                        {data.related_document_name && (
                          <span className="rounded-md bg-white border border-blue-200 px-2 py-0.5 font-medium text-blue-700 flex items-center gap-1">
                            <FileText className="h-3 w-3" /> {data.related_document_name}
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Original Clarification Request Box */}
                  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-3">
                      <div className="flex items-center gap-2">
                        <div className="h-7 w-7 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs">
                          PO
                        </div>
                        <div>
                          <div className="text-xs font-bold text-slate-900">Clarification Question</div>
                          <div className="text-[11px] text-slate-400">
                            {data.sent_at ? `Sent ${new Date(data.sent_at).toLocaleString()}` : `Created ${new Date(data.created_at).toLocaleString()}`}
                          </div>
                        </div>
                      </div>
                      <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                        {data.clarification_type.replace(/_/g, " ")}
                      </span>
                    </div>

                    <div className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed">
                      {data.message}
                    </div>
                  </div>

                  {/* Responses Thread */}
                  <div className="space-y-4">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <Send className="h-3.5 w-3.5 text-indigo-600" /> Response History ({data.responses.length})
                    </h4>

                    {data.responses.length === 0 ? (
                      <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-xs text-slate-500">
                        {data.status === "DRAFT"
                          ? "This clarification request is still a DRAFT. Send it to notify the bidder."
                          : "Awaiting response from the bidder representative."}
                      </div>
                    ) : (
                      data.responses.map((resp, idx) => (
                        <div key={resp.id} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-5 space-y-3">
                          <div className="flex items-center justify-between border-b border-slate-200/60 pb-2.5">
                            <div className="flex items-center gap-2">
                              <div className="h-7 w-7 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-xs">
                                B
                              </div>
                              <div>
                                <div className="text-xs font-bold text-slate-900">
                                  {resp.responded_by_name || "Bidder Representative"}
                                </div>
                                <div className="text-[11px] text-slate-400">
                                  {new Date(resp.created_at).toLocaleString()}
                                </div>
                              </div>
                            </div>
                            <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                              Response #{idx + 1}
                            </span>
                          </div>

                          <div className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed">
                            {resp.response_text}
                          </div>

                          {/* Attached Document Badges */}
                          {resp.attached_document_id && (
                            <div className="pt-2 border-t border-slate-200/60 flex flex-wrap items-center gap-2 text-xs">
                              <span className="font-semibold text-slate-600">Attached Document:</span>
                              <span className="inline-flex items-center gap-1 rounded-lg bg-white border border-slate-200 px-2.5 py-1 text-slate-800 font-medium shadow-2xs">
                                <FileText className="h-3.5 w-3.5 text-indigo-600" />
                                {resp.attached_document_name || "Supporting Document"}
                              </span>
                              {resp.is_replacement_document && (
                                <span className="inline-flex items-center gap-1 rounded-lg bg-amber-50 border border-amber-200 px-2 py-0.5 text-[11px] font-bold text-amber-800">
                                  <FileCheck className="h-3 w-3" /> Replacement Document (Prior version archived)
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>

                  {/* Resolution Summary Block if Resolved */}
                  {data.status === "RESOLVED" && (
                    <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-5 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-emerald-950 font-bold text-sm">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Resolution Recorded
                        </div>
                        <span className="text-[11px] text-emerald-800">
                          {data.resolved_at ? new Date(data.resolved_at).toLocaleString() : ""}
                        </span>
                      </div>
                      <div className="text-xs text-emerald-900 leading-relaxed font-medium">
                        {data.resolution_note || "Clarification marked as RESOLVED by Procurement Officer."}
                      </div>
                      <div className="text-[11px] text-emerald-700/80 pt-1">
                        Resolved by: <strong>{data.resolved_by_name || "Procurement Officer"}</strong>
                      </div>
                    </div>
                  )}

                  {/* Re-evaluation Telemetry Result */}
                  {reevalResult && (
                    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-xs space-y-1 text-blue-900">
                      <div className="font-bold flex items-center gap-1.5">
                        <Sparkles className="h-4 w-4 text-blue-600" /> Deterministic Re-evaluation Triggered
                      </div>
                      <div className="grid grid-cols-3 gap-2 pt-2">
                        <div>
                          <span className="text-blue-600 block">Compliance Status</span>
                          <span className="font-bold">{reevalResult.compliance_status}</span>
                        </div>
                        <div>
                          <span className="text-blue-600 block">Total Score</span>
                          <span className="font-bold">{reevalResult.total_score ?? "N/A"}</span>
                        </div>
                        <div>
                          <span className="text-blue-600 block">Risk Level</span>
                          <span className="font-bold">{reevalResult.risk_level ?? "N/A"}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Bidder Response Input Box (Shown if open and user is Bidder) */}
                  {isBidder && !isClosedOrResolved && (
                    <form onSubmit={handleBidderSubmit} className="rounded-2xl border border-slate-200 bg-slate-50 p-5 space-y-4">
                      <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                        <Send className="h-3.5 w-3.5 text-emerald-600" /> Submit Your Clarification Response
                      </h4>

                      {replySuccess && (
                        <div className="rounded-xl bg-emerald-100 border border-emerald-200 p-3 text-xs font-bold text-emerald-800 flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Response submitted successfully!
                        </div>
                      )}

                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Explanation / Clarification Text <span className="text-rose-500">*</span>
                        </label>
                        <textarea
                          rows={3}
                          value={responseText}
                          onChange={(e) => setResponseText(e.target.value)}
                          placeholder="Provide detailed clarification, references, or context in response to the officer query..."
                          className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
                          required
                        />
                      </div>

                      {/* File Attachment & Replacement Toggle */}
                      <div className="space-y-2 pt-2 border-t border-slate-200/60">
                        <label className="block text-xs font-semibold text-slate-700">
                          Supporting or Replacement Document (PDF, JPEG, PNG, ZIP)
                        </label>
                        <input
                          type="file"
                          onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                          className="block w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
                        />

                        {selectedFile && (
                          <label className="relative flex items-center gap-2.5 pt-1.5 cursor-pointer select-none">
                            <input
                              type="checkbox"
                              checked={isReplacement}
                              onChange={(e) => setIsReplacement(e.target.checked)}
                              className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                            />
                            <span className="text-xs font-medium text-slate-700">
                              This file is an updated <strong>Replacement</strong> of the original document (Prior version will be archived).
                            </span>
                          </label>
                        )}
                      </div>

                      <div className="flex justify-end pt-2">
                        <button
                          type="submit"
                          disabled={isReplying || !responseText.trim()}
                          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-2.5 text-xs font-bold text-white shadow-md hover:from-emerald-700 hover:to-teal-700 transition-all disabled:opacity-50"
                        >
                          {isReplying ? (
                            <>
                              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                              Submitting...
                            </>
                          ) : (
                            <>
                              <Send className="h-4 w-4" />
                              Send Clarification Response
                            </>
                          )}
                        </button>
                      </div>
                    </form>
                  )}
                </>
              )}
            </div>

            {/* Action Footer (For Procurement Officers) */}
            {isOfficer && data && !isClosedOrResolved && (
              <div className="border-t border-slate-200 bg-slate-50 p-4 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCancelClarification}
                    disabled={isCancelling}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50 hover:border-rose-200 transition-colors"
                  >
                    <Ban className="h-3.5 w-3.5" />
                    Cancel Thread
                  </button>

                  {data.status === "RESPONDED" && (
                    <button
                      onClick={handleMarkUnderReview}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-purple-700 hover:bg-purple-50 transition-colors"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      Mark Under Review
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {data.status === "DRAFT" ? (
                    <button
                      onClick={handleSendDraft}
                      disabled={isSendingDraft}
                      className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-indigo-700 transition-all"
                    >
                      <Send className="h-3.5 w-3.5" />
                      Send to Bidder
                    </button>
                  ) : (
                    <button
                      onClick={() => setIsResolveOpen(true)}
                      className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:from-emerald-700 hover:to-teal-700 transition-all"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      Resolve Clarification
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Resolve Clarification Modal */}
      {data && (
        <ResolveClarificationModal
          isOpen={isResolveOpen}
          onClose={() => setIsResolveOpen(false)}
          onSuccess={() => {
            fetchDetail();
            if (onUpdate) onUpdate();
          }}
          clarificationId={data.id}
          subject={data.subject}
          bidderName={data.bidder_organization_name}
          bidNumber={data.bid_number}
          token={token}
        />
      )}
    </>
  );
};
