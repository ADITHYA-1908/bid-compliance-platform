"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  X,
  FileText,
  Download,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  Maximize2,
  RefreshCw,
  Eye,
  Info,
} from "lucide-react";
import { ComplianceResultItem } from "@/types/compliance";
import { downloadBidDocumentBlob, downloadProcurementBidDocumentBlob } from "@/lib/api/bids";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { EvidenceDetails } from "./EvidenceDetails";

export interface EvidenceViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  bidId: string;
  documentId?: string | null;
  initialPage?: number | null;
  documentName?: string | null;
  rule?: ComplianceResultItem | null;
  isProcurement?: boolean;
}

export function EvidenceViewerModal({
  isOpen,
  onClose,
  bidId,
  documentId,
  initialPage,
  documentName,
  rule,
  isProcurement = true,
}: EvidenceViewerModalProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [mimeType, setMimeType] = useState<string>("application/pdf");
  const [fileName, setFileName] = useState<string>(documentName || "Document.pdf");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(initialPage || 1);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [activeTab, setActiveTab] = useState<"viewer" | "details">("viewer");

  // Determine active document ID (from prop or rule)
  const activeDocId =
    documentId ||
    rule?.document_id ||
    (rule?.evidence && (rule.evidence.document_id || rule.evidence.doc_id || rule.evidence.source_document_id));

  // Determine target initial page
  const targetPage =
    initialPage ??
    rule?.page_number ??
    (rule?.evidence && (rule.evidence.page_number || rule.evidence.page)) ??
    1;

  useEffect(() => {
    if (isOpen && targetPage) {
      setCurrentPage(Number(targetPage) || 1);
    }
  }, [isOpen, targetPage]);

  // Load document blob
  const loadDocument = useCallback(async () => {
    if (!bidId || !activeDocId) {
      setError("No document reference is associated with this evidence item.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let res: { blob: Blob; filename: string };
      if (isProcurement) {
        try {
          res = await downloadProcurementBidDocumentBlob(bidId, activeDocId);
        } catch {
          // Fallback to bidder download if procurement route fails
          res = await downloadBidDocumentBlob(bidId, activeDocId);
        }
      } else {
        res = await downloadBidDocumentBlob(bidId, activeDocId);
      }

      setMimeType(res.blob.type || "application/pdf");
      if (res.filename) setFileName(res.filename);

      const url = URL.createObjectURL(res.blob);
      setBlobUrl(url);
    } catch (err: any) {
      console.error("Failed to load document evidence:", err);
      setError(err?.message || "Failed to load document. Please check permissions or try downloading directly.");
    } finally {
      setLoading(false);
    }
  }, [bidId, activeDocId, isProcurement]);

  useEffect(() => {
    if (isOpen && activeDocId) {
      loadDocument();
    }

    return () => {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
        setBlobUrl(null);
      }
    };
  }, [isOpen, activeDocId]);

  // Handle ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Zoom helpers
  const handleZoomIn = () => setZoomLevel((prev) => Math.min(prev + 25, 200));
  const handleZoomOut = () => setZoomLevel((prev) => Math.max(prev - 25, 50));
  const handleZoomReset = () => setZoomLevel(100);

  // Page helpers
  const handlePrevPage = () => setCurrentPage((p) => Math.max(1, p - 1));
  const handleNextPage = () => setCurrentPage((p) => p + 1);
  const handleJumpToEvidence = () => {
    if (targetPage) setCurrentPage(Number(targetPage));
  };

  // Direct download
  const handleDownload = () => {
    if (blobUrl) {
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = fileName || "evidence-document.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

  const pdfSrc = blobUrl
    ? `${blobUrl}#page=${currentPage}&zoom=${zoomLevel}`
    : null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-2 sm:p-4 overflow-hidden animate-in fade-in duration-200"
    >
      <div className="relative flex flex-col w-full max-w-7xl h-[94vh] rounded-2xl bg-white shadow-2xl border border-slate-200 overflow-hidden">
        {/* Top Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-200 bg-slate-900 text-white shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600/30 border border-blue-500/40 text-blue-300 shrink-0">
              <FileText className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="text-sm sm:text-base font-bold text-white truncate max-w-[280px] sm:max-w-md">
                  {documentName || fileName || "Document Evidence Viewer"}
                </h2>
                {rule?.requirement_code && (
                  <span className="rounded bg-blue-500/20 border border-blue-400/30 px-2 py-0.5 font-mono text-[11px] font-bold text-blue-300">
                    {rule.requirement_code}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 truncate">
                {rule?.requirement_name
                  ? `Evidence for: ${rule.requirement_name}`
                  : "Verified Bid Submission Document"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {blobUrl && (
              <button
                type="button"
                onClick={handleDownload}
                className="hidden sm:inline-flex items-center gap-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 transition-colors cursor-pointer"
                title="Download original document"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Download</span>
              </button>
            )}

            <button
              type="button"
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer"
              title="Close viewer (ESC)"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Mobile Tab Switcher */}
        <div className="flex lg:hidden border-b border-slate-200 bg-slate-50 px-3 py-1.5">
          <button
            type="button"
            onClick={() => setActiveTab("viewer")}
            className={`flex-1 py-1.5 text-xs font-bold rounded-lg text-center ${
              activeTab === "viewer"
                ? "bg-white text-blue-600 shadow-2xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Document Viewer
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("details")}
            className={`flex-1 py-1.5 text-xs font-bold rounded-lg text-center ${
              activeTab === "details"
                ? "bg-white text-blue-600 shadow-2xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Explain Why & Evidence
          </button>
        </div>

        {/* Main Split Body */}
        <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden bg-slate-100">
          {/* Left / Center: Interactive PDF Document Viewer */}
          <div
            className={`flex-1 flex flex-col min-h-0 border-r border-slate-200 bg-slate-200/60 ${
              activeTab === "viewer" ? "flex" : "hidden lg:flex"
            }`}
          >
            {/* Viewer Control Bar */}
            <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 border-b border-slate-200 bg-white text-xs font-medium text-slate-700 shrink-0">
              {/* Page Controls */}
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={handlePrevPage}
                  disabled={currentPage <= 1}
                  className="inline-flex items-center justify-center h-7 w-7 rounded border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed text-slate-700 cursor-pointer"
                  title="Previous page"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <div className="flex items-center gap-1 font-mono text-xs px-2">
                  <span>Page</span>
                  <input
                    type="number"
                    min={1}
                    value={currentPage}
                    onChange={(e) => setCurrentPage(Math.max(1, parseInt(e.target.value) || 1))}
                    className="h-7 w-12 rounded border border-slate-300 bg-white text-center font-bold text-slate-900 focus:outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <button
                  type="button"
                  onClick={handleNextPage}
                  className="inline-flex items-center justify-center h-7 w-7 rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 cursor-pointer"
                  title="Next page"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>

                {targetPage && Number(targetPage) !== currentPage && (
                  <button
                    type="button"
                    onClick={handleJumpToEvidence}
                    className="ml-2 inline-flex items-center gap-1 rounded bg-blue-50 border border-blue-200 px-2 py-1 text-[11px] font-bold text-blue-700 hover:bg-blue-100 transition-colors cursor-pointer"
                  >
                    <span>Jump to Evidence (p.{targetPage})</span>
                  </button>
                )}
              </div>

              {/* Zoom Controls */}
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={handleZoomOut}
                  disabled={zoomLevel <= 50}
                  className="inline-flex items-center justify-center h-7 w-7 rounded border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed text-slate-700 cursor-pointer"
                  title="Zoom out"
                >
                  <ZoomOut className="h-3.5 w-3.5" />
                </button>
                <span className="font-mono text-xs w-12 text-center text-slate-600">
                  {zoomLevel}%
                </span>
                <button
                  type="button"
                  onClick={handleZoomIn}
                  disabled={zoomLevel >= 200}
                  className="inline-flex items-center justify-center h-7 w-7 rounded border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed text-slate-700 cursor-pointer"
                  title="Zoom in"
                >
                  <ZoomIn className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={handleZoomReset}
                  className="inline-flex items-center justify-center h-7 w-7 rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 ml-1 cursor-pointer"
                  title="Reset zoom"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {/* Document Render Area */}
            <div className="flex-1 min-h-0 relative overflow-auto flex items-center justify-center p-2 sm:p-4">
              {loading && (
                <div className="flex flex-col items-center justify-center gap-3 text-slate-600">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                  <p className="text-sm font-medium">Loading document evidence...</p>
                </div>
              )}

              {error && !loading && (
                <div className="flex flex-col items-center justify-center max-w-md p-6 text-center bg-white rounded-xl border border-slate-200 shadow-sm">
                  <AlertTriangle className="h-10 w-10 text-amber-500 mb-2" />
                  <h4 className="text-sm font-bold text-slate-900">Document Unavailable in Viewer</h4>
                  <p className="text-xs text-slate-600 mt-1 mb-4">{error}</p>
                  <button
                    type="button"
                    onClick={loadDocument}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 px-3.5 py-2 text-xs font-bold text-white shadow-xs transition-colors cursor-pointer"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    <span>Retry Loading</span>
                  </button>
                </div>
              )}

              {blobUrl && !loading && !error && (
                <div className="w-full h-full rounded-lg bg-white shadow-md border border-slate-300 overflow-hidden flex flex-col">
                  {mimeType.includes("image") ? (
                    <div className="flex-1 overflow-auto flex items-center justify-center p-4 bg-slate-900">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={blobUrl}
                        alt="Evidence Document"
                        style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: "top center" }}
                        className="max-w-full max-h-full object-contain transition-transform"
                      />
                    </div>
                  ) : (
                    <iframe
                      src={pdfSrc || blobUrl}
                      title="PDF Evidence Viewer"
                      className="w-full h-full border-none"
                    />
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right: Explain Why & Structured Evidence Panel */}
          <div
            className={`w-full lg:w-[420px] xl:w-[460px] flex flex-col min-h-0 bg-white shrink-0 overflow-y-auto p-4 sm:p-5 ${
              activeTab === "details" ? "flex" : "hidden lg:flex"
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-blue-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  Explain Why & Verification Analysis
                </h3>
              </div>
            </div>

            <div className="mt-4 flex-1">
              {rule ? (
                <EvidenceDetails
                  rule={rule}
                  onViewDocument={() => handleJumpToEvidence()}
                  showFullHeader={true}
                />
              ) : (
                <div className="p-6 text-center text-slate-500 text-xs">
                  No rule details attached. Viewing raw document.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
