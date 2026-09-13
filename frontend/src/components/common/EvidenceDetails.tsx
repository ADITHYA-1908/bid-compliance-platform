"use client";

import React, { useState } from "react";
import {
  FileText,
  Eye,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  MinusCircle,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Info,
  ShieldCheck,
  ExternalLink,
} from "lucide-react";
import { ComplianceResultItem, ComplianceStatus } from "@/types/compliance";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface EvidenceDetailsProps {
  rule: ComplianceResultItem | any;
  onViewDocument?: (documentId?: string, pageNumber?: number) => void;
  className?: string;
  showFullHeader?: boolean;
}

export function EvidenceDetails({
  rule,
  onViewDocument,
  className = "",
  showFullHeader = true,
}: EvidenceDetailsProps) {
  const [isRawExpanded, setIsRawExpanded] = useState(false);

  if (!rule) return null;

  // Extract structured fields (with fallbacks to rule.evidence dict if nested)
  const evidenceDict = typeof rule.evidence === "object" && rule.evidence !== null ? rule.evidence : {};

  const documentId =
    rule.document_id ||
    evidenceDict.document_id ||
    evidenceDict.doc_id ||
    evidenceDict.source_document_id;

  const documentName =
    rule.document_name ||
    evidenceDict.document_name ||
    evidenceDict.doc_name ||
    evidenceDict.source_name ||
    evidenceDict.filename ||
    (documentId ? "Attached Bid Document" : null);

  const pageNumber =
    rule.page_number ??
    evidenceDict.page_number ??
    evidenceDict.page ??
    null;

  const snippet =
    rule.evidence_snippet ||
    evidenceDict.snippet ||
    evidenceDict.evidence_snippet ||
    evidenceDict.text_snippet ||
    evidenceDict.matched_text ||
    evidenceDict.quote ||
    null;

  const confidence =
    rule.confidence ??
    evidenceDict.confidence ??
    evidenceDict.score ??
    null;

  const verificationSource =
    rule.verification_source ||
    evidenceDict.verification_source ||
    evidenceDict.source ||
    evidenceDict.method ||
    null;

  const status = rule.compliance_status || rule.status || "PENDING";

  const getStatusBadge = (st: string) => {
    switch (st) {
      case "PASS":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 text-xs font-bold text-emerald-800">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            PASS
          </span>
        );
      case "FAIL":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-50 border border-rose-200 px-3 py-1 text-xs font-bold text-rose-800">
            <XCircle className="h-4 w-4 text-rose-600" />
            FAIL
          </span>
        );
      case "REVIEW":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-200 px-3 py-1 text-xs font-bold text-amber-800">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            HUMAN REVIEW REQUIRED
          </span>
        );
      case "NOT_APPLICABLE":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600">
            <MinusCircle className="h-4 w-4 text-slate-400" />
            NOT APPLICABLE
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 border border-blue-200 px-3 py-1 text-xs font-medium text-blue-700">
            <Clock className="h-4 w-4 text-blue-500" />
            {st}
          </span>
        );
    }
  };

  return (
    <div className={`space-y-4 text-slate-800 ${className}`}>
      {/* Header Info */}
      {showFullHeader && (
        <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-slate-500">
                  {rule.requirement_code || "RULE"}
                </span>
                {rule.category && (
                  <span className="rounded bg-slate-200/80 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                    {rule.category}
                  </span>
                )}
                {rule.is_mandatory && (
                  <span className="rounded bg-rose-100 px-2 py-0.5 text-[10px] font-bold text-rose-800">
                    Mandatory
                  </span>
                )}
                {rule.is_critical && (
                  <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-900">
                    Critical
                  </span>
                )}
              </div>
              <h3 className="text-base font-bold text-slate-900 mt-1">
                {rule.requirement_name || rule.rule_name || "Evaluation Rule"}
              </h3>
            </div>
            <div>{getStatusBadge(status)}</div>
          </div>
        </div>
      )}

      {/* Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Expected Value
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            {rule.operator && (
              <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs font-semibold text-slate-600">
                {rule.operator}
              </span>
            )}
            <span className="font-mono text-sm font-bold text-slate-900">
              {rule.expected_value !== null && rule.expected_value !== undefined
                ? String(rule.expected_value)
                : "—"}
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Actual Extracted / Evaluated Value
          </div>
          <div className="mt-1">
            <span className="font-mono text-sm font-bold text-slate-900">
              {rule.actual_value !== null && rule.actual_value !== undefined
                ? String(rule.actual_value)
                : "None / Not Found"}
            </span>
          </div>
        </div>
      </div>

      {/* Deterministic Reason / Explanation */}
      {rule.reason && (
        <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-4">
          <div className="flex items-start gap-2.5">
            <Info className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-blue-900">
                Compliance Determination Reason
              </div>
              <p className="mt-1 text-xs text-blue-950 leading-relaxed">
                {rule.reason}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Evidence & Verification Card */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-blue-600" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Verified Evidence Details
            </span>
          </div>
          {confidence !== null && confidence !== undefined && (
            <ConfidenceBadge score={confidence} />
          )}
        </div>

        {/* Source Document & Page */}
        <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-50 rounded-lg p-2.5 text-xs">
          <div className="flex items-center gap-2 text-slate-700 min-w-0">
            <span className="font-medium text-slate-500">Document:</span>
            <span className="font-semibold text-slate-900 truncate max-w-[220px]">
              {documentName || (documentId ? "Attached Document" : "No Document Linked")}
            </span>
            {pageNumber && (
              <span className="rounded bg-blue-100 text-blue-800 px-2 py-0.5 font-mono text-[11px] font-bold">
                Page {pageNumber}
              </span>
            )}
          </div>

          {onViewDocument && (
            <button
              type="button"
              onClick={() => onViewDocument(documentId, pageNumber ? Number(pageNumber) : undefined)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white shadow-xs transition-colors cursor-pointer"
            >
              <Eye className="h-3.5 w-3.5" />
              <span>View in Evidence Viewer</span>
            </button>
          )}
        </div>

        {/* Evidence Snippet Quotation */}
        {snippet ? (
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
              Document Excerpt / Extracted Snippet
            </div>
            <div className="relative rounded-lg border-l-4 border-blue-500 bg-slate-50 p-3 text-xs text-slate-700 font-mono italic leading-relaxed">
              &ldquo;{snippet}&rdquo;
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-500 italic">
            No verbatim text snippet was recorded for this rule.
          </div>
        )}

        {/* Verification Source / Method */}
        {verificationSource && (
          <div className="flex items-center gap-2 pt-1 text-[11px] text-slate-600">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
            <span className="font-medium">Verification Source:</span>
            <span className="font-mono font-semibold uppercase text-slate-800">
              {verificationSource}
            </span>
          </div>
        )}
      </div>

      {/* Raw / Extended Metadata Accordion */}
      {evidenceDict && Object.keys(evidenceDict).length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-slate-50/50 overflow-hidden">
          <button
            type="button"
            onClick={() => setIsRawExpanded(!isRawExpanded)}
            className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-100/80 transition-colors cursor-pointer"
          >
            <span>Extended Metadata & Parameters ({Object.keys(evidenceDict).length} fields)</span>
            {isRawExpanded ? (
              <ChevronUp className="h-4 w-4 text-slate-400" />
            ) : (
              <ChevronDown className="h-4 w-4 text-slate-400" />
            )}
          </button>

          {isRawExpanded && (
            <div className="p-4 border-t border-slate-200 bg-white space-y-2">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {Object.entries(evidenceDict).map(([key, val]) => (
                  <div key={key} className="rounded border border-slate-100 bg-slate-50/50 p-2">
                    <span className="font-mono text-[10px] uppercase text-slate-400 block truncate">
                      {key}
                    </span>
                    <span className="font-mono text-xs font-semibold text-slate-800 break-all">
                      {typeof val === "object" ? JSON.stringify(val) : String(val ?? "—")}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
