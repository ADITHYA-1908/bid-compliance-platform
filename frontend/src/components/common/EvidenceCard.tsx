import React from "react";
import { FileText, Eye } from "lucide-react";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface EvidenceCardProps {
  fieldName: string;
  extractedValue: string | number | null;
  documentName?: string;
  pageNumber?: number | string;
  snippet?: string;
  confidence?: number | null;
  onViewDocument?: () => void;
  className?: string;
}

export function EvidenceCard({
  fieldName,
  extractedValue,
  documentName,
  pageNumber,
  snippet,
  confidence,
  onViewDocument,
  className = "",
}: EvidenceCardProps) {
  return (
    <div className={`rounded-lg border border-slate-200 bg-white p-4 shadow-xs transition-colors hover:border-slate-300 ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            {fieldName}
          </span>
          <p className="font-mono-score text-sm font-bold text-slate-900 mt-0.5">
            {extractedValue !== null && extractedValue !== undefined && extractedValue !== ""
              ? String(extractedValue)
              : "—"}
          </p>
        </div>

        {confidence !== undefined && <ConfidenceBadge score={confidence} />}
      </div>

      {/* Document & Page Source */}
      {(documentName || pageNumber) && (
        <div className="mt-2.5 flex items-center justify-between border-t border-slate-100 pt-2 text-[11px] text-slate-500">
          <div className="flex items-center gap-1.5 truncate max-w-[200px]">
            <FileText className="h-3 w-3 text-slate-400 shrink-0" />
            <span className="truncate font-medium text-slate-700">{documentName || "Document"}</span>
            {pageNumber && (
              <span className="rounded bg-slate-100 px-1 py-0.2 font-mono text-[10px] font-bold text-slate-600">
                p.{pageNumber}
              </span>
            )}
          </div>

          {onViewDocument && (
            <button
              type="button"
              onClick={onViewDocument}
              className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-700 hover:text-slate-900 hover:underline cursor-pointer"
            >
              <Eye className="h-3 w-3" />
              <span>Evidence</span>
            </button>
          )}
        </div>
      )}

      {/* Snippet Context */}
      {snippet && (
        <div className="mt-2 rounded bg-slate-50 border border-slate-200 p-2 text-[11px] text-slate-700 font-mono italic leading-relaxed">
          &ldquo;{snippet}&rdquo;
        </div>
      )}
    </div>
  );
}
