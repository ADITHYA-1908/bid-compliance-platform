"use client";

import React from "react";
import { DocumentQualityResult } from "@/types/document_quality";
import {
  X,
  ShieldCheck,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  Scan,
  Info,
  Sparkles,
} from "lucide-react";

interface DocumentQualityModalProps {
  isOpen: boolean;
  onClose: () => void;
  quality: DocumentQualityResult | null;
  documentName?: string;
  documentType?: string;
}

export const DocumentQualityModal: React.FC<DocumentQualityModalProps> = ({
  isOpen,
  onClose,
  quality,
  documentName = "Compliance Document",
  documentType = "DOCUMENT",
}) => {
  if (!isOpen || !quality) return null;

  const score = Math.round(quality.quality_score || 0);
  const normLevel = (quality.quality_level || "GOOD").toUpperCase();

  let levelBg = "bg-emerald-50 text-emerald-800 border-emerald-200";
  let scoreBarColor = "bg-emerald-600";

  if (normLevel === "UNUSABLE" || quality.is_corrupted || quality.is_password_protected) {
    levelBg = "bg-rose-50 text-rose-800 border-rose-200";
    scoreBarColor = "bg-rose-600";
  } else if (normLevel === "POOR") {
    levelBg = "bg-amber-50 text-amber-800 border-amber-200";
    scoreBarColor = "bg-amber-600";
  } else if (normLevel === "ACCEPTABLE") {
    levelBg = "bg-blue-50 text-blue-800 border-blue-200";
    scoreBarColor = "bg-blue-600";
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="relative w-full max-w-3xl rounded-xl bg-white shadow-2xl border border-slate-200 overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="rounded-lg bg-blue-100 p-2 text-blue-700">
              <Scan className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Document Quality Diagnostics
              </h3>
              <p className="text-xs text-slate-500">
                {documentName} · <span className="font-semibold uppercase">{documentType}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {/* Top Score & Level KPI Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Score Card */}
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-500 uppercase">Quality Score</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded border ${levelBg}`}>
                  {normLevel}
                </span>
              </div>
              <div className="text-2xl font-black text-slate-900">{score}/100</div>
              <div className="w-full bg-slate-200 rounded-full h-2 mt-2 overflow-hidden">
                <div
                  className={`h-2 rounded-full ${scoreBarColor} transition-all duration-500`}
                  style={{ width: `${score}%` }}
                />
              </div>
            </div>

            {/* OCR Confidence Card */}
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <span className="text-xs font-semibold text-slate-500 uppercase">OCR Confidence</span>
              <div className="text-2xl font-black text-slate-900 mt-1">
                {quality.average_ocr_confidence !== null && quality.average_ocr_confidence !== undefined
                  ? `${Math.round(quality.average_ocr_confidence * 100)}%`
                  : "N/A (Digital PDF)"}
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                {quality.page_count} page{quality.page_count !== 1 ? "s" : ""} analyzed
              </p>
            </div>

            {/* Integrity Status Card */}
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <span className="text-xs font-semibold text-slate-500 uppercase">Integrity Flag</span>
              <div className="text-sm font-bold mt-1.5 flex items-center gap-1.5">
                {quality.is_corrupted ? (
                  <span className="text-rose-700 flex items-center gap-1">
                    <AlertOctagon className="h-4 w-4" /> Corrupted File
                  </span>
                ) : quality.is_password_protected ? (
                  <span className="text-rose-700 flex items-center gap-1">
                    <AlertOctagon className="h-4 w-4" /> Password Locked
                  </span>
                ) : quality.review_required ? (
                  <span className="text-amber-700 flex items-center gap-1">
                    <AlertTriangle className="h-4 w-4" /> Review Required
                  </span>
                ) : (
                  <span className="text-emerald-700 flex items-center gap-1">
                    <CheckCircle2 className="h-4 w-4" /> Verified Clean
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Deterministic Pre-Extraction
              </p>
            </div>
          </div>

          {/* Diagnostic Flags Summary */}
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-blue-600" />
              Diagnostic Signals & Telemetry
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 text-xs">
              <div className={`p-2.5 rounded-lg border flex flex-col items-center text-center ${quality.is_blurry ? "bg-amber-50 border-amber-200 text-amber-900" : "bg-slate-50 border-slate-200 text-slate-700"}`}>
                <span className="font-semibold">Blur Detection</span>
                <span className="text-[11px] mt-1 font-bold">{quality.is_blurry ? "⚠️ Blurry Scan" : "✓ Sharp"}</span>
              </div>
              <div className={`p-2.5 rounded-lg border flex flex-col items-center text-center ${quality.has_blank_pages ? "bg-amber-50 border-amber-200 text-amber-900" : "bg-slate-50 border-slate-200 text-slate-700"}`}>
                <span className="font-semibold">Blank Pages</span>
                <span className="text-[11px] mt-1 font-bold">{quality.has_blank_pages ? "⚠️ Blank Found" : "✓ No Blank"}</span>
              </div>
              <div className={`p-2.5 rounded-lg border flex flex-col items-center text-center ${quality.has_unreadable_pages ? "bg-rose-50 border-rose-200 text-rose-900" : "bg-slate-50 border-slate-200 text-slate-700"}`}>
                <span className="font-semibold">Legibility</span>
                <span className="text-[11px] mt-1 font-bold">{quality.has_unreadable_pages ? "❌ Unreadable" : "✓ Legible"}</span>
              </div>
              <div className={`p-2.5 rounded-lg border flex flex-col items-center text-center ${quality.has_low_resolution_pages ? "bg-amber-50 border-amber-200 text-amber-900" : "bg-slate-50 border-slate-200 text-slate-700"}`}>
                <span className="font-semibold">Resolution</span>
                <span className="text-[11px] mt-1 font-bold">{quality.has_low_resolution_pages ? "⚠️ Low DPI" : "✓ Standard"}</span>
              </div>
              <div className={`p-2.5 rounded-lg border flex flex-col items-center text-center ${quality.has_skewed_pages ? "bg-amber-50 border-amber-200 text-amber-900" : "bg-slate-50 border-slate-200 text-slate-700"}`}>
                <span className="font-semibold">Skew / Tilt</span>
                <span className="text-[11px] mt-1 font-bold">{quality.has_skewed_pages ? "⚠️ Tilted" : "✓ Upright"}</span>
              </div>
            </div>
          </div>

          {/* Bidder-Facing Guidance */}
          {quality.bidder_feedback && quality.bidder_feedback.length > 0 && (
            <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-blue-900 mb-2 flex items-center gap-1.5">
                <Info className="h-4 w-4 text-blue-700" />
                Bidder Actionable Feedback
              </h4>
              <ul className="space-y-1 text-xs text-blue-800">
                {quality.bidder_feedback.map((fb, idx) => (
                  <li key={idx} className="flex items-start gap-1.5">
                    <span className="text-blue-600 font-bold">•</span>
                    <span>{fb}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Procurement Review Reasons */}
          {quality.review_reasons && quality.review_reasons.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-2 flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 text-slate-700" />
                Technical Review Explanations
              </h4>
              <ul className="space-y-1 text-xs text-slate-700">
                {quality.review_reasons.map((reason, idx) => (
                  <li key={idx} className="flex items-start gap-1.5">
                    <span className="text-slate-500 font-bold">•</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Page-by-Page Diagnostics Table */}
          {quality.page_qualities && quality.page_qualities.length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5">
                Page-by-Page Diagnostic Breakdown
              </h4>
              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <table className="w-full text-left text-xs text-slate-700">
                  <thead className="bg-slate-100 text-[11px] font-bold uppercase text-slate-600 border-b border-slate-200">
                    <tr>
                      <th className="px-3 py-2.5">Page #</th>
                      <th className="px-3 py-2.5">Quality Level</th>
                      <th className="px-3 py-2.5">Sharpness</th>
                      <th className="px-3 py-2.5">Resolution</th>
                      <th className="px-3 py-2.5">Skew</th>
                      <th className="px-3 py-2.5">Findings</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 bg-white">
                    {quality.page_qualities.map((pq) => (
                      <tr key={pq.id} className="hover:bg-slate-50">
                        <td className="px-3 py-2.5 font-bold text-slate-900">
                          Page {pq.page_number}
                        </td>
                        <td className="px-3 py-2.5">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${
                              pq.quality_level === "GOOD"
                                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                                : pq.quality_level === "ACCEPTABLE"
                                ? "bg-blue-50 text-blue-800 border-blue-200"
                                : pq.quality_level === "POOR"
                                ? "bg-amber-50 text-amber-800 border-amber-200"
                                : "bg-rose-50 text-rose-800 border-rose-200"
                            }`}
                          >
                            {pq.quality_level}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-slate-600 font-mono">
                          {pq.blur_score.toFixed(1)}
                        </td>
                        <td className="px-3 py-2.5 text-slate-600">
                          {pq.resolution || (pq.width && pq.height ? `${pq.width}x${pq.height}` : "Standard")}
                        </td>
                        <td className="px-3 py-2.5 text-slate-600 font-mono">
                          {pq.skew_angle ? `${pq.skew_angle}°` : "0°"}
                        </td>
                        <td className="px-3 py-2.5">
                          {pq.issues && pq.issues.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {pq.issues.map((iss, i) => (
                                <span
                                  key={i}
                                  className="inline-block bg-amber-50 text-amber-800 border border-amber-200 px-1.5 py-0.5 rounded text-[10px]"
                                >
                                  {iss}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-emerald-700 font-medium">Clear</span>
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

        {/* Modal Footer */}
        <div className="flex items-center justify-end border-t border-slate-200 bg-slate-50 px-6 py-3">
          <button
            onClick={onClose}
            className="rounded-lg bg-slate-200 px-4 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-300 transition-colors"
          >
            Close Diagnostics
          </button>
        </div>
      </div>
    </div>
  );
};
