"use client";

import React, { useState } from "react";
import {
  X,
  MessageSquarePlus,
  Send,
  Save,
  AlertTriangle,
  Clock,
  FileText,
  ShieldCheck,
  Calendar,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import {
  ClarificationPriority,
  ClarificationRequestCreate,
  ClarificationType,
} from "@/types/clarification";
import { procurementClarificationsApi } from "@/lib/api/clarifications";

interface CreateClarificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (createdId: string) => void;
  tenderId: string;
  bidId: string;
  tenderTitle?: string;
  bidNumber?: string;
  bidderName?: string;
  // Optional pre-filled linkage
  initialSubject?: string;
  initialType?: ClarificationType;
  initialPriority?: ClarificationPriority;
  relatedRequirementId?: string;
  relatedRequirementCode?: string;
  relatedDocumentId?: string;
  relatedDocumentName?: string;
  relatedReviewItemId?: string;
  relatedVerificationRecordId?: string;
  relatedComplianceResultId?: string;
  relatedDuplicateMatchId?: string;
  token?: string;
}

const CLARIFICATION_TYPES: { label: string; value: ClarificationType; desc: string }[] = [
  { label: "Missing Document", value: "MISSING_DOCUMENT", desc: "A mandatory requirement document was omitted" },
  { label: "Unclear Document", value: "UNCLEAR_DOCUMENT", desc: "Low legibility, blurry scan, or truncated page" },
  { label: "Low OCR Confidence", value: "LOW_OCR_CONFIDENCE", desc: "OCR text extraction confidence is below safe threshold" },
  { label: "Verification Mismatch", value: "VERIFICATION_MISMATCH", desc: "External API portal check returned discrepancy (e.g., GST / PAN)" },
  { label: "Compliance Review", value: "COMPLIANCE_REVIEW", desc: "Specific clause criteria requires official explanation" },
  { label: "Duplicate / Reuse Alert", value: "DUPLICATE_REUSE_EXPLANATION", desc: "Cross-bid similarity match flagged potential reuse" },
  { label: "Certificate Validity", value: "CERTIFICATE_VALIDITY", desc: "Certificate has expired or expires before milestone" },
  { label: "Conflicting Information", value: "CONFLICTING_INFORMATION", desc: "Extracted fields conflict across submitted documents" },
  { label: "Additional Evidence", value: "ADDITIONAL_EVIDENCE", desc: "Supplementary supporting records or annexures requested" },
  { label: "Other Inquiry", value: "OTHER", desc: "General clarification or administrative query" },
];

const PRIORITIES: { label: string; value: ClarificationPriority; color: string }[] = [
  { label: "Low", value: "LOW", color: "text-slate-600 bg-slate-100 border-slate-200" },
  { label: "Normal", value: "NORMAL", color: "text-blue-700 bg-blue-50 border-blue-200" },
  { label: "High", value: "HIGH", color: "text-amber-700 bg-amber-50 border-amber-200" },
  { label: "Urgent", value: "URGENT", color: "text-rose-700 bg-rose-50 border-rose-200" },
];

export const CreateClarificationModal: React.FC<CreateClarificationModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  tenderId,
  bidId,
  tenderTitle,
  bidNumber,
  bidderName,
  initialSubject = "",
  initialType = "COMPLIANCE_REVIEW",
  initialPriority = "NORMAL",
  relatedRequirementId,
  relatedRequirementCode,
  relatedDocumentId,
  relatedDocumentName,
  relatedReviewItemId,
  relatedVerificationRecordId,
  relatedComplianceResultId,
  relatedDuplicateMatchId,
  token,
}) => {
  const [subject, setSubject] = useState(initialSubject);
  const [message, setMessage] = useState("");
  const [clarificationType, setClarificationType] = useState<ClarificationType>(initialType);
  const [priority, setPriority] = useState<ClarificationPriority>(initialPriority);
  const [dueDate, setDueDate] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() + 3); // Default 3 days deadline
    return d.toISOString().slice(0, 10);
  });
  const [sendImmediately, setSendImmediately] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim()) {
      setErrorMsg("Please enter a subject.");
      return;
    }
    if (!message.trim()) {
      setErrorMsg("Please provide detailed instructions or questions in the message.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const payload: ClarificationRequestCreate = {
        subject: subject.trim(),
        message: message.trim(),
        clarification_type: clarificationType,
        priority,
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
        send_immediately: sendImmediately,
        related_requirement_id: relatedRequirementId || null,
        related_document_id: relatedDocumentId || null,
        related_review_item_id: relatedReviewItemId || null,
        related_verification_record_id: relatedVerificationRecordId || null,
        related_compliance_result_id: relatedComplianceResultId || null,
        related_duplicate_match_id: relatedDuplicateMatchId || null,
      };

      const result = await procurementClarificationsApi.createClarification(
        tenderId,
        bidId,
        payload,
        token
      );

      if (onSuccess) {
        onSuccess(result.id);
      }
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create clarification request");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="relative w-full max-w-2xl rounded-2xl bg-white shadow-2xl border border-slate-200 overflow-hidden my-6">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 px-6 py-4 text-white">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-indigo-500/20 border border-indigo-400/30 p-2.5 text-indigo-300">
              <MessageSquarePlus className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold">Request Formal Clarification</h3>
              <p className="text-xs text-indigo-200/80">
                {bidNumber ? `Bid ${bidNumber}` : "Bid Submission"} • {bidderName || "Bidder"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {errorMsg && (
            <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Linkage Badge Summary */}
          {(relatedRequirementCode || relatedDocumentName || relatedReviewItemId) && (
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-3.5 flex flex-wrap items-center gap-2 text-xs text-slate-700">
              <span className="font-semibold text-slate-500 flex items-center gap-1">
                <FileText className="h-3.5 w-3.5 text-slate-400" /> Linked Context:
              </span>
              {relatedRequirementCode && (
                <span className="inline-flex items-center gap-1 rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700 border border-indigo-200">
                  Rule [{relatedRequirementCode}]
                </span>
              )}
              {relatedDocumentName && (
                <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 border border-blue-200">
                  Doc: {relatedDocumentName}
                </span>
              )}
              {relatedReviewItemId && (
                <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 border border-amber-200">
                  Human Review Item Linked
                </span>
              )}
            </div>
          )}

          {/* Subject Line */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Subject <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="e.g., Discrepancy in GST Certificate State Code"
              className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
              required
            />
          </div>

          {/* Clarification Type & Priority Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Clarification Reason / Category
              </label>
              <select
                value={clarificationType}
                onChange={(e) => setClarificationType(e.target.value as ClarificationType)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
              >
                {CLARIFICATION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Priority Level
              </label>
              <div className="grid grid-cols-4 gap-1.5">
                {PRIORITIES.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setPriority(p.value)}
                    className={`rounded-lg py-2 text-xs font-semibold border transition-all text-center ${
                      priority === p.value
                        ? `${p.color} ring-2 ring-indigo-500/30 font-bold shadow-xs`
                        : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Message Body */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Specific Query / Clarification Request <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={4}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Explain clearly what discrepancy was found, which document requires clarification or replacement, and what evidence the bidder must provide..."
              className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 resize-y"
              required
            />
            <p className="mt-1 text-[11px] text-slate-500">
              The bidder will receive an in-app notification and will be able to reply with explanatory text and uploaded evidence.
            </p>
          </div>

          {/* Due Date & Immediate Send Toggle */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1 border-t border-slate-100">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-slate-500" /> Response Deadline
              </label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
              />
            </div>

            <div className="flex items-center pt-6">
              <label className="relative flex items-center gap-3 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={sendImmediately}
                  onChange={(e) => setSendImmediately(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-xs font-semibold text-slate-800">
                  Send to Bidder Immediately
                </span>
              </label>
            </div>
          </div>

          {/* Footer Controls */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 px-5 py-2.5 text-xs font-bold text-white shadow-md hover:from-indigo-700 hover:to-blue-700 transition-all disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Saving...
                </>
              ) : sendImmediately ? (
                <>
                  <Send className="h-4 w-4" />
                  Send Clarification Request
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save as Draft
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
