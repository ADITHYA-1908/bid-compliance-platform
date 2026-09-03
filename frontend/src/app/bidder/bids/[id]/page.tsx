"use client";

import React, { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  api,
  ApiError,
  BidDetail,
  BidUpdatePayload,
  BidDocument,
  BidDocumentsSummary,
  BidderTenderDetail,
  BidSubmissionReadinessResponse,
  BidSubmitResponse,
  DocumentExtractedTextResponse,
  VerificationSummaryItem,
  BidVerificationListResponse,
} from "@/lib/api";
import {
  formatCurrency,
  formatDateTime,
  formatDeadlineRemaining,
} from "@/lib/formatters";
import { getBidCompliance, evaluateBidCompliance } from "@/lib/api/compliance";
import { BidComplianceSummaryResponse, ComplianceResultItem } from "@/types/compliance";
import { DocumentQualityBadge } from "@/components/common/DocumentQualityBadge";
import { DocumentQualityModal } from "@/components/procurement/DocumentQualityModal";
import { documentQualityApi } from "@/lib/api/document_quality";
import { DocumentQualityResult } from "@/types/document_quality";
import {
  ArrowLeft,
  Building2,
  Calendar,
  Clock,
  Save,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileText,
  ShieldCheck,
  FileUp,
  Send,
  ExternalLink,
  Layers,
  Sparkles,
  Info,
  DollarSign,
  Briefcase,
  Lock,
  Download,
  Trash2,
  RefreshCw,
  Eye,
  Paperclip,
  UploadCloud,
  X,
  FileCheck,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Award,
  Cpu,
  RotateCw,
  Copy,
  Check,
} from "lucide-react";

const DOCUMENT_TYPES = [
  { value: "PAN", label: "PAN Card / Tax Identity" },
  { value: "GST_CERTIFICATE", label: "GST Registration Certificate" },
  { value: "UDYAM_CERTIFICATE", label: "Udyam / MSME Registration" },
  { value: "OEM_AUTHORIZATION", label: "OEM Authorization Form (MAF)" },
  { value: "FINANCIAL_STATEMENT", label: "Audited Financial Statements" },
  { value: "TURNOVER_CERTIFICATE", label: "CA Certified Turnover Certificate" },
  { value: "EXPERIENCE_CERTIFICATE", label: "Past Performance / Experience" },
  { value: "LOCAL_CONTENT_DECLARATION", label: "Make in India (MII) Declaration" },
  { value: "BLACKLIST_DECLARATION", label: "Non-Blacklisting Undertaking" },
  { value: "TECHNICAL_DOCUMENT", label: "Technical Compliance / Datasheet" },
  { value: "COMMERCIAL_DOCUMENT", label: "Commercial Terms & Price Breakdown" },
  { value: "OTHER", label: "Other Supporting Document" },
];

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

export default function BidWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const bidId = params?.id as string;

  const [bid, setBid] = useState<BidDetail | null>(null);
  const [tenderDetail, setTenderDetail] = useState<BidderTenderDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form fields for DRAFT editing
  const [quotedAmount, setQuotedAmount] = useState<string>("");
  const [currency, setCurrency] = useState<string>("INR");
  const [technicalSummary, setTechnicalSummary] = useState<string>("");
  const [commercialNotes, setCommercialNotes] = useState<string>("");
  const [remarks, setRemarks] = useState<string>("");

  // Save states
  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Part 3D Documents state
  const [documents, setDocuments] = useState<BidDocument[]>([]);
  const [docsSummary, setDocsSummary] = useState<BidDocumentsSummary | null>(null);
  const [loadingDocs, setLoadingDocs] = useState<boolean>(false);

  // Upload Modal State
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [uploadTargetReqId, setUploadTargetReqId] = useState<string | null>(null);
  const [uploadTargetReqName, setUploadTargetReqName] = useState<string>("");
  const [selectedDocType, setSelectedDocType] = useState<string>("TECHNICAL_DOCUMENT");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadNotes, setUploadNotes] = useState<string>("");
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccessMsg, setUploadSuccessMsg] = useState<string | null>(null);

  // Replace / Remove Modal States
  const [replaceTargetDoc, setReplaceTargetDoc] = useState<BidDocument | null>(null);
  const [removeTargetDoc, setRemoveTargetDoc] = useState<BidDocument | null>(null);
  const [actionInProgress, setActionInProgress] = useState<boolean>(false);

  // Part 3E: Submission & Readiness States
  const [readiness, setReadiness] = useState<BidSubmissionReadinessResponse | null>(null);
  const [loadingReadiness, setLoadingReadiness] = useState<boolean>(false);
  const [declarationAccepted, setDeclarationAccepted] = useState<boolean>(false);
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitSuccessReceipt, setSubmitSuccessReceipt] = useState<BidSubmitResponse | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Part 4A & 4B: Document Processing & Extracted Text state
  const [processingDocId, setProcessingDocId] = useState<string | null>(null);
  const [viewingExtractedTextDoc, setViewingExtractedTextDoc] = useState<BidDocument | null>(null);
  const [extractedTextData, setExtractedTextData] = useState<DocumentExtractedTextResponse | null>(null);
  const [loadingExtractedText, setLoadingExtractedText] = useState<boolean>(false);
  const [copiedText, setCopiedText] = useState<boolean>(false);

  // Part 11: Document Quality Diagnostic States
  const [qualityModalDoc, setQualityModalDoc] = useState<BidDocument | null>(null);
  const [qualityResultData, setQualityResultData] = useState<DocumentQualityResult | null>(null);
  const [loadingQuality, setLoadingQuality] = useState<boolean>(false);

  // Part 5A: Verification Engine State
  const [verifyingDocId, setVerifyingDocId] = useState<string | null>(null);
  const [retryingVerificationId, setRetryingVerificationId] = useState<string | null>(null);
  const [docVerificationsMap, setDocVerificationsMap] = useState<Record<string, VerificationSummaryItem[]>>({});
  const [bidVerifications, setBidVerifications] = useState<BidVerificationListResponse | null>(null);

  // Part 6A/6B: Compliance Evaluation Engine State
  const [complianceSummary, setComplianceSummary] = useState<BidComplianceSummaryResponse | null>(null);
  const [loadingCompliance, setLoadingCompliance] = useState<boolean>(false);
  const [evaluatingCompliance, setEvaluatingCompliance] = useState<boolean>(false);
  const [expandedComplianceId, setExpandedComplianceId] = useState<string | null>(null);
  const [complianceFilter, setComplianceFilter] = useState<"ALL" | "STATUTORY" | "INTEGRITY" | "FINANCIAL" | "EXPERIENCE" | "TECHNICAL" | "OEM" | "LOCAL_CONTENT" | "BIS" | "DOCUMENTS" | "ATTENTION">("ALL");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const quoteInputRef = useRef<HTMLInputElement>(null);

  const fetchBidDetail = async () => {
    if (!bidId) return;
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await api.getBid(bidId);
      setBid(data);
      setQuotedAmount(data.quoted_amount ? String(data.quoted_amount) : "");
      setCurrency(data.currency || "INR");
      setTechnicalSummary(data.technical_summary || "");
      setCommercialNotes(data.commercial_notes || "");
      setRemarks(data.remarks || "");
      setDeclarationAccepted(Boolean(data.declaration_accepted));

      // Load full tender details including requirements
      if (data.tender_id) {
        try {
          const tDetail = await api.getBidderTender(data.tender_id);
          setTenderDetail(tDetail);
        } catch {
          // Non-blocking
        }
      }

      // Load documents
      await fetchDocuments();
      // Load submission readiness
      await fetchReadiness();
      // Load verifications
      await fetchVerifications();
      // Load compliance evaluation
      await fetchCompliance();
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 404) {
        setErrorMessage(
          "Bid proposal workspace not found or you do not have permission to view it."
        );
      } else {
        setErrorMessage(
          err instanceof ApiError ? err.message : "Failed to load bid workspace."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchCompliance = async () => {
    if (!bidId) return;
    setLoadingCompliance(true);
    try {
      const compRes = await getBidCompliance(bidId);
      setComplianceSummary(compRes);
    } catch (err) {
      console.error("Failed to load compliance results:", err);
    } finally {
      setLoadingCompliance(false);
    }
  };

  const handleEvaluateCompliance = async () => {
    if (!bidId) return;
    setEvaluatingCompliance(true);
    try {
      const compRes = await evaluateBidCompliance(bidId);
      setComplianceSummary(compRes);
    } catch (err: any) {
      alert(err instanceof ApiError ? err.message : "Failed to evaluate compliance rules.");
    } finally {
      setEvaluatingCompliance(false);
    }
  };

  const fetchDocuments = async () => {
    if (!bidId) return;
    setLoadingDocs(true);
    try {
      const res = await api.getBidDocuments(bidId);
      setDocuments(res.items);
      setDocsSummary(res.summary);
    } catch (err) {
      console.error("Failed to load bid documents:", err);
    } finally {
      setLoadingDocs(false);
    }
  };

  const fetchVerifications = async () => {
    if (!bidId) return;
    try {
      const vRes = await api.getBidVerifications(bidId);
      setBidVerifications(vRes);
      // Group by document if available
      const grouped: Record<string, VerificationSummaryItem[]> = {};
      for (const item of vRes.verifications) {
        // Find document linked to this verification
        const docMatch = documents.find(d => d.processing && d.processing.id);
        const key = item.id;
        if (!grouped[key]) grouped[key] = [];
        grouped[key].push(item);
      }
      setDocVerificationsMap(grouped);
    } catch (err) {
      console.error("Failed to load bid verifications:", err);
    }
  };

  const fetchReadiness = async () => {
    if (!bidId) return;
    setLoadingReadiness(true);
    try {
      const data = await api.getBidSubmissionReadiness(bidId);
      setReadiness(data);
    } catch (err) {
      console.error("Failed to evaluate submission readiness:", err);
    } finally {
      setLoadingReadiness(false);
    }
  };

  useEffect(() => {
    fetchBidDetail();
  }, [bidId]);

  const handleSaveDraft = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!bidId || !bid) return;

    setSaving(true);
    setSaveSuccess(false);
    setSaveError(null);

    const payload: BidUpdatePayload = {
      quoted_amount: quotedAmount.trim() ? parseFloat(quotedAmount) : null,
      currency: currency.trim() || "INR",
      technical_summary: technicalSummary.trim() || null,
      commercial_notes: commercialNotes.trim() || null,
      remarks: remarks.trim() || null,
    };

    try {
      const updated = await api.updateBid(bidId, payload);
      setBid(updated);
      setSaveSuccess(true);
      await fetchReadiness();
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err: any) {
      setSaveError(
        err instanceof ApiError ? err.message : "Failed to save draft proposal."
      );
    } finally {
      setSaving(false);
    }
  };

  // Open upload modal for a specific requirement
  const openUploadModal = (reqId?: string, reqName?: string, defaultType?: string) => {
    setUploadTargetReqId(reqId || null);
    setUploadTargetReqName(reqName || "");
    setSelectedDocType(defaultType || "TECHNICAL_DOCUMENT");
    setSelectedFile(null);
    setUploadNotes("");
    setUploadError(null);
    setUploadSuccessMsg(null);
    setIsUploadModalOpen(true);
  };

  // Handle File Selection (Strict PDF-First Validation)
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const validTypes = ["application/pdf", "image/jpeg", "image/png"];
      const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
      const isImage = file.type.startsWith("image/") || file.name.toLowerCase().match(/\.(jpg|jpeg|png)$/i);

      if (!isPdf && !isImage) {
        setUploadError("Invalid file format. Please upload an authentic PDF document (application/pdf).");
        setSelectedFile(null);
        return;
      }

      if (file.size > 15 * 1024 * 1024) {
        setUploadError("File exceeds 15 MB limit. Please select a smaller PDF document.");
        setSelectedFile(null);
        return;
      }

      if (file.size === 0) {
        setUploadError("The selected file is empty (0 bytes). Please select a valid document.");
        setSelectedFile(null);
        return;
      }

      setSelectedFile(file);
      setUploadError(null);
    }
  };

  // Execute Document Upload
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !bidId) {
      setUploadError("Please select a file to upload.");
      return;
    }

    setUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("document_type", selectedDocType);
    if (uploadTargetReqId) {
      formData.append("tender_requirement_id", uploadTargetReqId);
    }
    if (uploadNotes.trim()) {
      formData.append("notes", uploadNotes.trim());
    }

    try {
      await api.uploadBidDocument(bidId, formData);
      setUploadSuccessMsg("Document uploaded successfully.");
      await fetchDocuments();
      await fetchReadiness();
      setTimeout(() => {
        setIsUploadModalOpen(false);
        setUploadSuccessMsg(null);
      }, 1200);
    } catch (err: any) {
      setUploadError(
        err instanceof ApiError ? err.message : "Failed to upload document."
      );
    } finally {
      setUploading(false);
    }
  };

  // Execute Replace Document
  const handleReplaceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !bidId || !replaceTargetDoc) {
      setUploadError("Please select a replacement file.");
      return;
    }

    setActionInProgress(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", selectedFile);
    if (uploadNotes.trim()) {
      formData.append("notes", uploadNotes.trim());
    }

    try {
      await api.replaceBidDocument(bidId, replaceTargetDoc.id, formData);
      await fetchDocuments();
      await fetchReadiness();
      setReplaceTargetDoc(null);
      setSelectedFile(null);
    } catch (err: any) {
      setUploadError(
        err instanceof ApiError ? err.message : "Failed to replace document."
      );
    } finally {
      setActionInProgress(false);
    }
  };

  // Execute Remove Document
  const handleRemoveConfirm = async () => {
    if (!bidId || !removeTargetDoc) return;
    setActionInProgress(true);
    try {
      await api.removeBidDocument(bidId, removeTargetDoc.id);
      await fetchDocuments();
      await fetchReadiness();
      setRemoveTargetDoc(null);
    } catch (err: any) {
      alert(err instanceof ApiError ? err.message : "Failed to remove document.");
    } finally {
      setActionInProgress(false);
    }
  };

  // Execute Final Bid Submission
  const handleFinalSubmitConfirm = async () => {
    if (!bidId || !declarationAccepted) return;
    setSubmitting(true);
    setSubmitError(null);

    try {
      const receipt = await api.submitFinalBid(bidId, {
        declaration_accepted: true,
      });
      setSubmitSuccessReceipt(receipt);
      setIsSubmitModalOpen(false);
      // Reload updated bid status
      await fetchBidDetail();
    } catch (err: any) {
      setSubmitError(
        err instanceof ApiError ? err.message : "Failed to submit final bid proposal."
      );
    } finally {
      setSubmitting(false);
    }
  };

  // Download / View document
  const handleDownload = async (doc: BidDocument) => {
    if (!bidId) return;
    try {
      if (doc.download_url) {
        window.open(doc.download_url, "_blank");
        return;
      }
      const res = await api.getBidDocumentDownloadUrl(bidId, doc.id);
      if (res.download_url) {
        window.open(res.download_url, "_blank");
        return;
      }
      window.open(
        `/api/v1/bidder/bids/${bidId}/documents/${doc.id}/download`,
        "_blank"
      );
    } catch (err: any) {
      alert("Unable to open document: " + (err?.message || "Unknown error"));
    }
  };

  // Part 4A: Trigger Document Processing
  const handleProcessDocument = async (docId: string) => {
    if (!bidId) return;
    setProcessingDocId(docId);
    try {
      await api.processDocument(bidId, docId);
      await fetchDocuments();
    } catch (err: any) {
      alert(err instanceof ApiError ? err.message : "Failed to queue document processing.");
    } finally {
      setProcessingDocId(null);
    }
  };

  // Part 4A: Retry Document Processing
  const handleRetryDocumentProcessing = async (docId: string) => {
    if (!bidId) return;
    setProcessingDocId(docId);
    try {
      await api.retryDocumentProcessing(bidId, docId);
      await fetchDocuments();
    } catch (err: any) {
      alert(err instanceof ApiError ? err.message : "Failed to retry document processing.");
    } finally {
      setProcessingDocId(null);
    }
  };

  // Part 5A: Trigger Claim Verification (Mock)
  const handleVerifyDocument = async (docId: string) => {
    if (!bidId) return;
    setVerifyingDocId(docId);
    try {
      await api.verifyDocumentClaims(bidId, docId);
      await fetchDocuments();
      await fetchVerifications();
      if (viewingExtractedTextDoc && viewingExtractedTextDoc.id === docId) {
        // Refresh extracted text modal data
        const data = await api.getDocumentExtractedText(bidId, docId);
        setExtractedTextData(data);
      }
    } catch (err: any) {
      alert(err instanceof ApiError ? err.message : "Failed to run claim verification.");
    } finally {
      setVerifyingDocId(null);
    }
  };

  // Part 5A: Retry Verification Record
  const handleRetryVerification = async (verificationId: string) => {
    if (!bidId) return;
    setRetryingVerificationId(verificationId);
    try {
      await api.retryVerification(bidId, verificationId);
      await fetchDocuments();
      await fetchVerifications();
      if (viewingExtractedTextDoc) {
        const data = await api.getDocumentExtractedText(bidId, viewingExtractedTextDoc.id);
        setExtractedTextData(data);
      }
    } catch (err: any) {
      alert(err instanceof ApiError ? err.message : "Failed to retry verification.");
    } finally {
      setRetryingVerificationId(null);
    }
  };

  // Part 4B: Open Extracted Text Preview Modal
  const handleOpenExtractedTextModal = async (doc: BidDocument) => {
    if (!bidId) return;
    setViewingExtractedTextDoc(doc);
    setLoadingExtractedText(true);
    setExtractedTextData(null);
    setCopiedText(false);
    try {
      const data = await api.getDocumentExtractedText(bidId, doc.id);
      setExtractedTextData(data);
      await fetchVerifications();
    } catch (err: any) {
      alert(err instanceof ApiError ? err.message : "Failed to load extracted text.");
      setViewingExtractedTextDoc(null);
    } finally {
      setLoadingExtractedText(false);
    }
  };

  // Part 11: Open Document Quality Diagnostics Modal
  const handleOpenQualityModal = async (doc: BidDocument) => {
    if (!bidId) return;
    setQualityModalDoc(doc);
    setLoadingQuality(true);
    setQualityResultData(null);
    try {
      const data = await documentQualityApi.getBidderDocumentQuality(bidId, doc.id);
      setQualityResultData(data);
    } catch (err: any) {
      alert(err instanceof ApiError ? err.message : "Failed to load document quality diagnostics.");
      setQualityModalDoc(null);
    } finally {
      setLoadingQuality(false);
    }
  };

  const handleTriggerQualityCheck = async (docId: string) => {
    if (!bidId) return;
    try {
      await documentQualityApi.triggerQualityCheck(bidId, docId);
      await fetchDocuments();
    } catch (err: any) {
      alert(err instanceof ApiError ? err.message : "Failed to run quality check.");
    }
  };

  const handleCopyExtractedText = () => {
    if (!extractedTextData?.normalized_text && !extractedTextData?.raw_text) return;
    navigator.clipboard.writeText(extractedTextData.normalized_text || extractedTextData.raw_text || "");
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 2000);
  };

  const deadline = formatDeadlineRemaining(bid?.tender?.submission_end_date);
  const isDraft = bid?.status === "DRAFT";
  const isSubmitted = bid?.status === "SUBMITTED";

  // Requirements derived from tender
  const tenderRequirements = tenderDetail?.requirements || [];
  const requiredDocs = tenderRequirements.filter(
    (r) => r.is_mandatory || r.requirement_type === "DOCUMENT"
  );

  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title={bid ? `Bid Workspace: ${bid.bid_number}` : "Bid Workspace"}
      description={
        bid
          ? `Tender: ${bid.tender.title} (${bid.tender.tender_number})`
          : "Proposal preparation and review workspace."
      }
      breadcrumbs={[
        { label: "Bidder Portal", href: "/bidder" },
        { label: "My Bids", href: "/bidder/bids" },
        { label: bid?.bid_number || "Bid Workspace" },
      ]}
    >
      <div className="space-y-6">
        {/* Top Navigation & Workspace Action Bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <Link
            href="/bidder/bids"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-blue-700 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to My Bids
          </Link>

          {bid && isDraft && (
            <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
              {saveSuccess && (
                <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200 animate-in fade-in">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Draft saved successfully
                </span>
              )}
              {saveError && (
                <span className="inline-flex items-center gap-1 text-xs font-bold text-rose-700 bg-rose-50 px-2.5 py-1 rounded-md border border-rose-200 animate-in fade-in">
                  <AlertCircle className="h-3.5 w-3.5" />
                  {saveError}
                </span>
              )}
              <button
                type="button"
                onClick={() => handleSaveDraft()}
                disabled={saving}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-700 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-800 transition-colors disabled:opacity-50"
              >
                {saving ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Saving Draft...
                  </>
                ) : (
                  <>
                    <Save className="h-3.5 w-3.5" />
                    Save Draft
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {loading ? (
          <div className="rounded-xl border border-slate-200 bg-white p-16 text-center shadow-xs">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-700" />
            <p className="mt-3 text-sm font-medium text-slate-600">
              Loading proposal workspace...
            </p>
          </div>
        ) : errorMessage || !bid ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-8 text-center shadow-xs">
            <AlertCircle className="mx-auto h-10 w-10 text-rose-600" />
            <h3 className="mt-3 text-base font-bold text-rose-900">
              Workspace Unavailable
            </h3>
            <p className="mt-1 text-xs text-rose-700 max-w-md mx-auto">
              {errorMessage || "The requested bid proposal could not be found."}
            </p>
            <div className="mt-5 flex items-center justify-center gap-3">
              <Link
                href="/bidder/bids"
                className="inline-flex items-center gap-1.5 rounded-md bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700 shadow-xs"
              >
                Back to My Bids
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Post-Submission Receipt Banner (Part 3E) */}
            {isSubmitted && (
              <div className="rounded-2xl border border-emerald-200 bg-linear-to-r from-emerald-50 via-teal-50/40 to-white p-6 shadow-xs space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-start gap-3.5">
                    <div className="rounded-xl bg-emerald-600 p-2.5 text-white shadow-xs">
                      <ShieldCheck className="h-6 w-6" />
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-800 border border-emerald-300">
                          <CheckCircle className="h-3.5 w-3.5" />
                          Final Bid Submitted
                        </span>
                        {bid.submission_reference && (
                          <span className="font-mono text-xs font-bold text-slate-800 bg-white px-2.5 py-0.5 rounded border border-slate-200">
                            REF: {bid.submission_reference}
                          </span>
                        )}
                      </div>
                      <h2 className="text-base font-bold text-slate-900">
                        Tamper-Evident Proposal Locked for Verification
                      </h2>
                      <p className="text-xs text-slate-600">
                        Submitted by <strong>{bid.bidder_organization?.name || "Your Organization"}</strong> on{" "}
                        <strong>{formatDateTime(bid.submitted_at)}</strong>. All commercial, technical, and document data is immutably sealed.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-start sm:self-auto">
                    <span className="rounded-lg bg-emerald-100/80 px-3 py-1.5 text-xs font-bold text-emerald-800 border border-emerald-200">
                      Status: SUBMITTED
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Header Overview Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-800 bg-slate-100 px-2.5 py-1 rounded border border-slate-200">
                      BID REF: {bid.bid_number}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold border ${
                        isSubmitted
                          ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                          : "bg-amber-50 text-amber-800 border-amber-200"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          isSubmitted ? "bg-emerald-500" : "bg-amber-500"
                        }`}
                      />
                      Status: {bid.status}
                    </span>
                    {bid.tender.category && (
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                        {bid.tender.category}
                      </span>
                    )}
                  </div>

                  <h1 className="text-xl font-bold text-slate-900 leading-snug">
                    {bid.tender.title}
                  </h1>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
                    <span className="font-mono font-semibold text-blue-700">
                      {bid.tender.tender_number}
                    </span>
                    {bid.tender.organization_name && (
                      <span className="flex items-center gap-1 text-slate-700">
                        <Building2 className="h-3.5 w-3.5 text-slate-400" />
                        <strong>{bid.tender.organization_name}</strong>
                      </span>
                    )}
                    <Link
                      href={`/bidder/tenders/${bid.tender_id}`}
                      target="_blank"
                      className="inline-flex items-center gap-1 text-blue-700 hover:underline font-semibold"
                    >
                      View Full Tender Notice
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </div>
                </div>

                {/* Estimated vs Quoted Box */}
                <div className="flex md:flex-col items-baseline md:items-end justify-between border-t md:border-t-0 pt-3 md:pt-0 border-slate-100 shrink-0">
                  <span className="text-xs text-slate-500 font-medium">
                    Tender Estimated Value
                  </span>
                  <span className="font-mono text-xl font-bold text-slate-700">
                    {formatCurrency(
                      bid.tender.estimated_value,
                      bid.tender.currency
                    )}
                  </span>
                </div>
              </div>
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              {/* Left 2 Columns: Proposal, Documents, Review & Submission */}
              <div className="lg:col-span-2 space-y-6">
                {/* Part 3E: Submission Readiness Checklist Card */}
                {isDraft && readiness && (
                  <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                      <div className="flex items-center gap-2">
                        <div
                          className={`rounded-lg p-2 ${
                            readiness.ready_to_submit
                              ? "bg-emerald-50 text-emerald-700"
                              : "bg-amber-50 text-amber-700"
                          }`}
                        >
                          {readiness.ready_to_submit ? (
                            <CheckCircle2 className="h-5 w-5" />
                          ) : (
                            <AlertCircle className="h-5 w-5" />
                          )}
                        </div>
                        <div>
                          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                            Submission Readiness Evaluation (Part 3E)
                          </h2>
                          <p className="text-xs text-slate-500">
                            Pre-submission criteria required before final locking.
                          </p>
                        </div>
                      </div>

                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-bold border self-start sm:self-auto ${
                          readiness.ready_to_submit
                            ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                            : "bg-amber-50 text-amber-800 border-amber-200"
                        }`}
                      >
                        {readiness.ready_to_submit
                          ? "✓ Ready to Submit"
                          : "⚠️ Incomplete Submission"}
                      </span>
                    </div>

                    {/* Criteria Checklist */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      {/* 1. Bidder Profile */}
                      <div className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
                        {readiness.checks.profile_complete ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                        ) : (
                          <XCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                        )}
                        <div>
                          <p className="font-bold text-slate-900">1. Bidder Organization Profile</p>
                          <p className="text-[11px] text-slate-500">
                            {readiness.checks.profile_complete
                              ? "100% Statutory fields verified"
                              : "Incomplete profile details"}
                          </p>
                        </div>
                      </div>

                      {/* 2. Proposal Details */}
                      <div className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
                        {readiness.checks.bid_details_complete ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                        ) : (
                          <XCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                        )}
                        <div>
                          <p className="font-bold text-slate-900">2. Commercial & Scope Quote</p>
                          <p className="text-[11px] text-slate-500">
                            {readiness.checks.bid_details_complete
                              ? `Quoted: ${formatCurrency(quotedAmount, currency)}`
                              : "Quoted amount or summary missing"}
                          </p>
                        </div>
                      </div>

                      {/* 3. Mandatory Documents */}
                      <div className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
                        {readiness.checks.mandatory_documents_complete ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                        ) : (
                          <XCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                        )}
                        <div>
                          <p className="font-bold text-slate-900">3. Mandatory Document Proofs</p>
                          <p className="text-[11px] text-slate-500">
                            {readiness.checks.mandatory_documents_complete
                              ? "All mandatory documents uploaded"
                              : `${readiness.missing_documents.length} mandatory document(s) missing`}
                          </p>
                        </div>
                      </div>

                      {/* 4. Tender & Deadline */}
                      <div className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
                        {readiness.checks.tender_open && readiness.checks.deadline_valid ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                        ) : (
                          <XCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                        )}
                        <div>
                          <p className="font-bold text-slate-900">4. Tender Status & Deadline</p>
                          <p className="text-[11px] text-slate-500">
                            {readiness.checks.deadline_valid
                              ? `Tender OPEN (${deadline.text})`
                              : "Deadline passed or tender closed"}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Missing Items Guidance Box */}
                    {!readiness.ready_to_submit && (
                      <div className="rounded-lg bg-amber-50/80 p-4 border border-amber-200 text-xs space-y-2">
                        <div className="flex items-center gap-1.5 font-bold text-amber-900">
                          <AlertTriangle className="h-4 w-4 text-amber-700" />
                          <span>Action Required Before Submission:</span>
                        </div>
                        <ul className="list-disc list-inside space-y-1 text-amber-800 text-[11px]">
                          {readiness.missing_required_fields.map((f, i) => (
                            <li key={i}>
                              Proposal Field: <strong>{f}</strong> is required.
                            </li>
                          ))}
                          {readiness.missing_documents.map((d, i) => (
                            <li key={i}>
                              Mandatory Document: <strong>{d}</strong> must be uploaded.
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Part 3D: Document Package Section */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
                    <div className="flex items-center gap-2.5">
                      <div className="rounded-lg bg-blue-50 p-2 text-blue-700">
                        <FileUp className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                          Bid Document Package & Evidence
                        </h2>
                        <p className="text-xs text-slate-500">
                          {isSubmitted
                            ? "Immutable statutory and technical evidence submitted."
                            : "Upload required statutory, technical, and commercial proof files."}
                        </p>
                      </div>
                    </div>

                    {isDraft && (
                      <button
                        type="button"
                        onClick={() => openUploadModal()}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-blue-700 px-3.5 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-blue-800 transition-colors self-start sm:self-auto"
                      >
                        <UploadCloud className="h-3.5 w-3.5" />
                        Upload Document
                      </button>
                    )}
                  </div>

                  {/* Document Requirements Checklist */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Tender Compliance Document Checklist
                    </h3>

                    {requiredDocs.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">
                        No specific mandatory document rules defined for this tender.
                      </p>
                    ) : (
                      <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-slate-50/50">
                        {requiredDocs.map((req) => {
                          const uploadedDoc = documents.find(
                            (d) => d.tender_requirement_id === req.id && d.is_active
                          );

                          return (
                            <div
                              key={req.id}
                              className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                            >
                              <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-mono text-[11px] font-bold text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                                    {req.code}
                                  </span>
                                  {req.is_mandatory ? (
                                    <span className="text-[10px] font-bold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                                      Mandatory
                                    </span>
                                  ) : (
                                    <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                                      Optional
                                    </span>
                                  )}
                                  <span className="text-[10px] font-medium text-slate-500">
                                    {req.category}
                                  </span>
                                </div>
                                <p className="text-xs font-bold text-slate-900">
                                  {req.name}
                                </p>

                                {/* Uploaded Doc Badge & Info */}
                                {uploadedDoc ? (
                                  <div className="space-y-1.5 pt-1">
                                    <div className="flex flex-wrap items-center gap-2 text-xs text-emerald-700">
                                      <FileCheck className="h-3.5 w-3.5" />
                                      <span className="font-medium">
                                        {uploadedDoc.original_filename}
                                      </span>
                                      <span className="text-slate-400">
                                        ({formatFileSize(uploadedDoc.file_size)})
                                      </span>
                                      <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 px-1.5 py-0.2 rounded">
                                        v{uploadedDoc.version}
                                      </span>
                                    </div>

                                    {/* Part 4A, 4B, 4C & 4D: Document Processing & Classification Badges */}
                                    {uploadedDoc.processing ? (
                                      <div className="flex flex-col gap-1.5">
                                        <div className="flex flex-wrap items-center gap-2">
                                          {uploadedDoc.processing.extraction_method === "DIGITAL_PDF" ||
                                          uploadedDoc.processing.extraction_method === "OCR" ||
                                          uploadedDoc.processing.extraction_method === "HYBRID" ? (
                                            <>
                                              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border bg-emerald-50 text-emerald-800 border-emerald-200">
                                                <FileText className="h-3 w-3 text-emerald-600" />
                                                Text Extracted • {uploadedDoc.processing.extraction_method === "HYBRID" ? "Hybrid" : uploadedDoc.processing.extraction_method === "OCR" ? "OCR" : "Digital PDF"} ({uploadedDoc.processing.page_count || 1} {uploadedDoc.processing.page_count === 1 ? "Page" : "Pages"})
                                              </span>
                                              <button
                                                type="button"
                                                onClick={() => handleOpenExtractedTextModal(uploadedDoc)}
                                                className="inline-flex items-center gap-1 rounded bg-white hover:bg-slate-50 text-slate-700 text-[10px] font-bold px-2 py-0.5 border border-slate-300 transition-colors shadow-2xs"
                                              >
                                                <Eye className="h-3 w-3 text-blue-600" />
                                                View Extracted Text
                                              </button>
                                            </>
                                          ) : uploadedDoc.processing.processing_status === "NEEDS_REVIEW" ? (
                                            <div className="flex items-center gap-2">
                                              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border bg-amber-50 text-amber-800 border-amber-200">
                                                <AlertTriangle className="h-3 w-3 text-amber-600" />
                                                Low Scan Quality (Review Required)
                                              </span>
                                              <button
                                                type="button"
                                                onClick={() => handleRetryDocumentProcessing(uploadedDoc.id)}
                                                disabled={processingDocId === uploadedDoc.id}
                                                className="inline-flex items-center gap-1 rounded bg-amber-100 hover:bg-amber-200 text-amber-900 text-[10px] font-bold px-2 py-0.5 border border-amber-300 transition-colors disabled:opacity-50"
                                              >
                                                <RotateCw className="h-2.5 w-2.5" />
                                                Retry
                                              </button>
                                            </div>
                                          ) : uploadedDoc.processing.processing_status === "PROCESSING" ? (
                                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border bg-blue-50 text-blue-800 border-blue-200 animate-pulse">
                                              <Loader2 className="h-3 w-3 animate-spin text-blue-600" />
                                              Processing & Running OCR...
                                            </span>
                                          ) : uploadedDoc.processing.processing_status === "FAILED" ? (
                                            <div className="flex items-center gap-2">
                                              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border bg-rose-50 text-rose-800 border-rose-200">
                                                <AlertCircle className="h-3 w-3 text-rose-600" />
                                                Extraction Failed: {uploadedDoc.processing.error_code || "ERROR"}
                                              </span>
                                              <button
                                                type="button"
                                                onClick={() => handleRetryDocumentProcessing(uploadedDoc.id)}
                                                disabled={processingDocId === uploadedDoc.id}
                                                className="inline-flex items-center gap-1 rounded bg-rose-100 hover:bg-rose-200 text-rose-800 text-[10px] font-bold px-2 py-0.5 border border-rose-300 transition-colors disabled:opacity-50"
                                              >
                                                {processingDocId === uploadedDoc.id ? (
                                                  <Loader2 className="h-2.5 w-2.5 animate-spin" />
                                                ) : (
                                                  <RotateCw className="h-2.5 w-2.5" />
                                                )}
                                                Retry
                                              </button>
                                            </div>
                                          ) : (
                                            <button
                                              type="button"
                                              onClick={() => handleProcessDocument(uploadedDoc.id)}
                                              disabled={processingDocId === uploadedDoc.id}
                                              className="inline-flex items-center gap-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-bold px-2 py-0.5 border border-slate-300 transition-colors disabled:opacity-50"
                                            >
                                              {processingDocId === uploadedDoc.id ? (
                                                <Loader2 className="h-2.5 w-2.5 animate-spin" />
                                              ) : (
                                                <Cpu className="h-2.5 w-2.5" />
                                              )}
                                              Process & Extract (OCR)
                                            </button>
                                          )}
                                        </div>

                                        {/* Part 4D: Classification Type & Confidence Badge */}
                                        {uploadedDoc.processing.detected_document_type && (
                                          <div className="flex flex-wrap items-center gap-1.5">
                                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border bg-indigo-50 text-indigo-900 border-indigo-200">
                                              <FileCheck className="h-3 w-3 text-indigo-600" />
                                              Class: {uploadedDoc.processing.detected_document_type.replace(/_/g, " ")}
                                            </span>
                                            {uploadedDoc.processing.classification_confidence !== undefined && uploadedDoc.processing.classification_confidence !== null && (
                                              <span
                                                className={`inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                                                  (uploadedDoc.processing.classification_confidence || 0) >= 0.8
                                                    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                                                    : (uploadedDoc.processing.classification_confidence || 0) >= 0.55
                                                    ? "bg-blue-50 text-blue-800 border-blue-200"
                                                    : "bg-amber-50 text-amber-800 border-amber-200"
                                                }`}
                                              >
                                                {(uploadedDoc.processing.classification_confidence || 0) >= 0.8
                                                  ? "High"
                                                  : (uploadedDoc.processing.classification_confidence || 0) >= 0.55
                                                  ? "Medium"
                                                  : "Low"}{" "}
                                                Confidence ({Math.round((uploadedDoc.processing.classification_confidence || 0) * 100)}%)
                                              </span>
                                            )}
                                            {uploadedDoc.processing.classification_requires_review && (
                                              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border bg-amber-50 text-amber-800 border-amber-200" title={uploadedDoc.processing.classification_reason || "Review Required"}>
                                                <AlertTriangle className="h-3 w-3 text-amber-600" />
                                                Review Required
                                              </span>
                                            )}

                                            {/* Part 11: Document Quality Badge */}
                                            {(() => {
                                              const qr = uploadedDoc.quality_result || uploadedDoc.processing?.quality_result;
                                              return (
                                                <DocumentQualityBadge
                                                  score={qr?.quality_score}
                                                  level={qr?.quality_level || (uploadedDoc.processing?.processing_status === "NEEDS_REVIEW" ? "POOR" : "GOOD")}
                                                  isBlurry={qr?.is_blurry}
                                                  hasBlankPages={qr?.has_blank_pages}
                                                  hasUnreadablePages={qr?.has_unreadable_pages}
                                                  isCorrupted={qr?.is_corrupted}
                                                  isPasswordProtected={qr?.is_password_protected}
                                                  onClick={() => handleOpenQualityModal(uploadedDoc)}
                                                />
                                              );
                                            })()}
                                          </div>
                                        )}
                                      </div>
                                    ) : (
                                      <button
                                        type="button"
                                        onClick={() => handleProcessDocument(uploadedDoc.id)}
                                        disabled={processingDocId === uploadedDoc.id}
                                        className="inline-flex items-center gap-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-bold px-2 py-0.5 border border-slate-300 transition-colors disabled:opacity-50"
                                      >
                                        {processingDocId === uploadedDoc.id ? (
                                          <Loader2 className="h-2.5 w-2.5 animate-spin" />
                                        ) : (
                                          <Cpu className="h-2.5 w-2.5" />
                                        )}
                                        Process & Extract (OCR)
                                      </button>
                                    )}
                                  </div>
                                ) : (
                                  <p className="text-[11px] font-semibold text-rose-600 pt-0.5">
                                    ✗ Document Not Yet Uploaded
                                  </p>
                                )}
                              </div>

                              {/* Requirement Actions */}
                              <div className="flex items-center gap-2 shrink-0">
                                {uploadedDoc ? (
                                  <>
                                    <button
                                      type="button"
                                      onClick={() => handleDownload(uploadedDoc)}
                                      className="inline-flex items-center gap-1 rounded bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 border border-slate-300 hover:bg-slate-50 shadow-2xs"
                                    >
                                      <Download className="h-3 w-3" />
                                      View
                                    </button>
                                    {isDraft && (
                                      <>
                                        <button
                                          type="button"
                                          onClick={() => {
                                            setReplaceTargetDoc(uploadedDoc);
                                            setSelectedFile(null);
                                            setUploadError(null);
                                          }}
                                          className="inline-flex items-center gap-1 rounded bg-white px-2.5 py-1 text-xs font-semibold text-blue-700 border border-blue-300 hover:bg-blue-50 shadow-2xs"
                                        >
                                          <RefreshCw className="h-3 w-3" />
                                          Replace
                                        </button>
                                        <button
                                          type="button"
                                          onClick={() => setRemoveTargetDoc(uploadedDoc)}
                                          className="inline-flex items-center gap-1 rounded bg-white px-2.5 py-1 text-xs font-semibold text-rose-700 border border-rose-300 hover:bg-rose-50 shadow-2xs"
                                        >
                                          <Trash2 className="h-3 w-3" />
                                        </button>
                                      </>
                                    )}
                                  </>
                                ) : (
                                  isDraft && (
                                    <button
                                      type="button"
                                      onClick={() =>
                                        openUploadModal(
                                          req.id,
                                          req.name,
                                          req.category === "STATUTORY"
                                            ? "GST_CERTIFICATE"
                                            : "TECHNICAL_DOCUMENT"
                                        )
                                      }
                                      className="inline-flex items-center gap-1 rounded-lg bg-blue-700 px-3 py-1.5 text-xs font-bold text-white shadow-2xs hover:bg-blue-800 transition-colors"
                                    >
                                      <FileUp className="h-3.5 w-3.5" />
                                      Upload Proof
                                    </button>
                                  )
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

                {/* ========================================================================= */}
                {/* Part 6A: Compliance Evaluation Engine Section */}
                {/* ========================================================================= */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
                    <div className="flex items-center gap-2.5">
                      <div className="rounded-lg bg-indigo-50 p-2 text-indigo-700">
                        <CheckCircle2 className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                          Compliance Evaluation Engine (Part 6A)
                        </h2>
                        <p className="text-xs text-slate-500">
                          Automated rule evaluation comparing tender criteria against verified credentials and evidence.
                        </p>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={handleEvaluateCompliance}
                      disabled={evaluatingCompliance || loadingCompliance}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-indigo-700 transition-colors disabled:opacity-50"
                    >
                      {evaluatingCompliance ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          Evaluating Rules...
                        </>
                      ) : (
                        <>
                          <RotateCw className="h-3.5 w-3.5" />
                          Evaluate Compliance
                        </>
                      )}
                    </button>
                  </div>

                  {/* Summary Metric Counters */}
                  {complianceSummary && (
                    <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
                      <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-center">
                        <span className="text-[10px] uppercase font-bold text-slate-500">Total Rules</span>
                        <p className="text-base font-extrabold text-slate-900">{complianceSummary.counts.total}</p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-center">
                        <span className="text-[10px] uppercase font-bold text-emerald-700">Pass</span>
                        <p className="text-base font-extrabold text-emerald-800">{complianceSummary.counts.passed}</p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-center">
                        <span className="text-[10px] uppercase font-bold text-rose-700">Fail</span>
                        <p className="text-base font-extrabold text-rose-800">{complianceSummary.counts.failed}</p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-center">
                        <span className="text-[10px] uppercase font-bold text-amber-700">Review</span>
                        <p className="text-base font-extrabold text-amber-800">{complianceSummary.counts.review}</p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-blue-50 border border-blue-200 text-center">
                        <span className="text-[10px] uppercase font-bold text-blue-700">Pending</span>
                        <p className="text-base font-extrabold text-blue-800">{complianceSummary.counts.pending}</p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-center">
                        <span className="text-[10px] uppercase font-bold text-slate-500">N/A</span>
                        <p className="text-base font-extrabold text-slate-700">{complianceSummary.counts.not_applicable}</p>
                      </div>
                    </div>
                  )}

                  {/* Disclaimer Notice Banner */}
                  <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 text-[11px] text-slate-600 flex items-start gap-2">
                    <Info className="h-4 w-4 text-indigo-600 shrink-0 mt-0.5" />
                    <span>
                      <strong>Compliance Architecture Notice:</strong> Evaluates criteria satisfaction against authoritative verified records. Weighted Compliance Scores (0–100%) and overall Risk Levels are calculated in Part 7.
                    </span>
                  </div>

                  {/* Filter Pills */}
                  {complianceSummary && complianceSummary.results.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <button
                        type="button"
                        onClick={() => setComplianceFilter("ALL")}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${
                          complianceFilter === "ALL"
                            ? "bg-slate-900 text-white shadow-2xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        All Rules ({complianceSummary.results.length})
                      </button>
                      <button
                        type="button"
                        onClick={() => setComplianceFilter("STATUTORY")}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${
                          complianceFilter === "STATUTORY"
                            ? "bg-indigo-600 text-white shadow-2xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        Statutory
                      </button>
                      <button
                        type="button"
                        onClick={() => setComplianceFilter("INTEGRITY")}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${
                          complianceFilter === "INTEGRITY"
                            ? "bg-red-700 text-white shadow-2xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        Integrity & Exclusion
                      </button>
                      <button
                        type="button"
                        onClick={() => setComplianceFilter("FINANCIAL")}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${
                          complianceFilter === "FINANCIAL"
                            ? "bg-emerald-700 text-white shadow-2xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        Financial
                      </button>
                      <button
                        type="button"
                        onClick={() => setComplianceFilter("EXPERIENCE")}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${
                          complianceFilter === "EXPERIENCE"
                            ? "bg-blue-700 text-white shadow-2xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        Experience
                      </button>
                      <button
                        type="button"
                        onClick={() => setComplianceFilter("TECHNICAL")}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${
                          complianceFilter === "TECHNICAL"
                            ? "bg-purple-700 text-white shadow-2xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        Technical
                      </button>
                      <button
                        type="button"
                        onClick={() => setComplianceFilter("OEM")}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${
                          complianceFilter === "OEM"
                            ? "bg-sky-700 text-white shadow-2xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        OEM
                      </button>
                      <button
                        type="button"
                        onClick={() => setComplianceFilter("LOCAL_CONTENT")}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${
                          complianceFilter === "LOCAL_CONTENT"
                            ? "bg-amber-700 text-white shadow-2xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        Make in India
                      </button>
                      <button
                        type="button"
                        onClick={() => setComplianceFilter("BIS")}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${
                          complianceFilter === "BIS"
                            ? "bg-teal-700 text-white shadow-2xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        BIS
                      </button>
                      <button
                        type="button"
                        onClick={() => setComplianceFilter("DOCUMENTS")}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${
                          complianceFilter === "DOCUMENTS"
                            ? "bg-zinc-700 text-white shadow-2xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        Documents
                      </button>
                      <button
                        type="button"
                        onClick={() => setComplianceFilter("ATTENTION")}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${
                          complianceFilter === "ATTENTION"
                            ? "bg-rose-600 text-white shadow-2xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        Action Required ({complianceSummary.counts.failed + complianceSummary.counts.review})
                      </button>
                    </div>
                  )}

                  {/* Compliance Rules List */}
                  {loadingCompliance ? (
                    <div className="flex items-center justify-center p-8 text-xs text-slate-500 gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                      Loading compliance determinations...
                    </div>
                  ) : complianceSummary && complianceSummary.results.length > 0 ? (
                    <div className="space-y-2.5">
                      {complianceSummary.results
                        .filter((r) => {
                          const code = (r.requirement_code || "").toLowerCase();
                          const name = (r.requirement_name || "").toLowerCase();
                          if (complianceFilter === "STATUTORY") {
                            return (
                              code.includes("gst") ||
                              code.includes("pan") ||
                              code.includes("udyam") ||
                              code.includes("msme") ||
                              code.includes("mca") ||
                              code.includes("startup") ||
                              code.includes("nsic") ||
                              code.includes("epfo") ||
                              code.includes("esic") ||
                              name.includes("gst") ||
                              name.includes("pan") ||
                              name.includes("udyam") ||
                              name.includes("msme") ||
                              name.includes("mca") ||
                              name.includes("startup") ||
                              name.includes("nsic") ||
                              name.includes("epfo") ||
                              name.includes("esic")
                            );
                          }
                          if (complianceFilter === "INTEGRITY") {
                            return (
                              code.includes("blacklist") ||
                              code.includes("debar") ||
                              code.includes("consistency") ||
                              code.includes("integrity") ||
                              name.includes("blacklist") ||
                              name.includes("debar") ||
                              name.includes("consistency")
                            );
                          }
                          if (complianceFilter === "FINANCIAL") {
                            return (
                              code.includes("turnover") ||
                              code.includes("revenue") ||
                              code.includes("profit") ||
                              code.includes("financial") ||
                              code.includes("pat") ||
                              name.includes("turnover") ||
                              name.includes("revenue") ||
                              name.includes("profit") ||
                              name.includes("financial")
                            );
                          }
                          if (complianceFilter === "EXPERIENCE") {
                            return (
                              code.includes("experience") ||
                              code.includes("project") ||
                              code.includes("work_order") ||
                              name.includes("experience") ||
                              name.includes("project") ||
                              name.includes("work order")
                            );
                          }
                          if (complianceFilter === "TECHNICAL") {
                            return (
                              code.includes("tech") ||
                              code.includes("product") ||
                              code.includes("model") ||
                              code.includes("spec") ||
                              code.includes("datasheet") ||
                              name.includes("technical") ||
                              name.includes("product") ||
                              name.includes("model") ||
                              name.includes("specification")
                            );
                          }
                          if (complianceFilter === "OEM") {
                            return (
                              code.includes("oem") ||
                              code.includes("maf") ||
                              code.includes("authorization") ||
                              name.includes("oem") ||
                              name.includes("authorization") ||
                              name.includes("manufacturer")
                            );
                          }
                          if (complianceFilter === "LOCAL_CONTENT") {
                            return (
                              code.includes("local_content") ||
                              code.includes("make_in_india") ||
                              code.includes("mii") ||
                              code.includes("supplier_class") ||
                              name.includes("local content") ||
                              name.includes("make in india") ||
                              name.includes("mii")
                            );
                          }
                          if (complianceFilter === "BIS") {
                            return (
                              code.includes("bis") ||
                              code.includes("crs") ||
                              code.includes("standard") ||
                              name.includes("bis") ||
                              name.includes("standard")
                            );
                          }
                          if (complianceFilter === "DOCUMENTS") {
                            return (
                              code.includes("document") ||
                              code.includes("declaration") ||
                              code.includes("certificate") ||
                              name.includes("document") ||
                              name.includes("certificate") ||
                              name.includes("declaration")
                            );
                          }
                          if (complianceFilter === "ATTENTION") {
                            return r.compliance_status === "FAIL" || r.compliance_status === "REVIEW";
                          }
                          return true;
                        })
                        .map((r) => {
                        const isExpanded = expandedComplianceId === r.id;
                        let statusColor = "bg-slate-100 text-slate-800 border-slate-300";
                        let StatusIcon = AlertCircle;

                        if (r.compliance_status === "PASS") {
                          statusColor = "bg-emerald-50 text-emerald-800 border-emerald-200";
                          StatusIcon = CheckCircle2;
                        } else if (r.compliance_status === "FAIL") {
                          statusColor = "bg-rose-50 text-rose-800 border-rose-200";
                          StatusIcon = XCircle;
                        } else if (r.compliance_status === "REVIEW") {
                          statusColor = "bg-amber-50 text-amber-800 border-amber-200";
                          StatusIcon = AlertTriangle;
                        } else if (r.compliance_status === "PENDING") {
                          statusColor = "bg-blue-50 text-blue-800 border-blue-200";
                          StatusIcon = Clock;
                        }

                        return (
                          <div
                            key={r.id}
                            className="rounded-lg border border-slate-200 bg-white overflow-hidden transition-all shadow-2xs"
                          >
                            <div
                              onClick={() => setExpandedComplianceId(isExpanded ? null : r.id)}
                              className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 gap-3 cursor-pointer hover:bg-slate-50/75 transition-colors"
                            >
                              <div className="space-y-1">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="font-bold text-xs text-slate-900">{r.requirement_name}</span>
                                  <span className="font-mono text-[10px] text-slate-500 font-semibold">({r.requirement_code})</span>
                                  {r.is_mandatory && (
                                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                                      Mandatory
                                    </span>
                                  )}
                                  {Boolean((r as any).critical_failure) && (
                                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-600 text-white shadow-2xs animate-pulse">
                                      Critical Requirement Failed
                                    </span>
                                  )}
                                  {Boolean((r as any).is_critical) && !(r as any).critical_failure && (
                                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
                                      Critical
                                    </span>
                                  )}
                                  {r.weight !== undefined && (
                                    <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                                      Weight: {Number(r.weight).toFixed(1)}
                                    </span>
                                  )}
                                </div>
                                <p className="text-[11px] text-slate-600 line-clamp-1">{r.reason}</p>
                              </div>

                              <div className="flex items-center gap-3 shrink-0 self-start sm:self-auto">
                                <span className={`inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full border ${statusColor}`}>
                                  <StatusIcon className="h-3 w-3" />
                                  {r.compliance_status}
                                </span>
                              </div>
                            </div>

                            {/* Expanded Evidence Details Drawer */}
                            {isExpanded && (
                              <div className="border-t border-slate-100 bg-slate-50/60 p-4 text-xs space-y-3">
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-[11px]">
                                  <div className="p-2.5 rounded bg-white border border-slate-200 space-y-1">
                                    <span className="text-slate-500 font-medium">Operator & Target</span>
                                    <p className="font-mono font-bold text-slate-800">
                                      {r.operator || "EQUALS"} &apos;{String(r.expected_value)}&apos;
                                    </p>
                                  </div>
                                  <div className="p-2.5 rounded bg-white border border-slate-200 space-y-1">
                                    <span className="text-slate-500 font-medium">Actual Evaluated Value</span>
                                    <p className="font-mono font-bold text-slate-800">
                                      {r.actual_value !== null ? String(r.actual_value) : "None / Unspecified"}
                                    </p>
                                  </div>
                                  <div className="p-2.5 rounded bg-white border border-slate-200 space-y-1">
                                    <span className="text-slate-500 font-medium">Source Evidence Trace</span>
                                    <p className="text-slate-700">
                                      {r.source_verification_ids && r.source_verification_ids.length > 0
                                        ? `${r.source_verification_ids.length} Verification Records Linked`
                                        : "Direct Attribute Check"}
                                    </p>
                                  </div>
                                </div>

                                <div className="space-y-1">
                                  <span className="text-[11px] font-bold text-slate-700">Evaluation Justification:</span>
                                  <p className="text-slate-700 text-xs bg-white p-2.5 rounded border border-slate-200">
                                    {r.reason}
                                  </p>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-center p-6 text-xs text-slate-500 bg-slate-50 rounded-lg border border-slate-200">
                      No compliance evaluation records generated yet. Click <strong>&quot;Evaluate Compliance&quot;</strong> above to execute rule matching.
                    </div>
                  )}
                </div>

                {/* Commercial & Technical Proposal Section */}
                <form onSubmit={handleSaveDraft} className="space-y-6">
                  {/* Commercial Information Section */}
                  <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
                    <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3">
                      <div className="rounded-lg bg-emerald-50 p-2 text-emerald-700">
                        <DollarSign className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                          Commercial Proposal & Pricing
                        </h2>
                        <p className="text-xs text-slate-500">
                          {isSubmitted
                            ? "Submitted commercial proposal quotation."
                            : "Enter total commercial quote inclusive of all taxes, duties, and freight."}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div className="sm:col-span-2 space-y-1.5">
                        <label className="text-xs font-bold text-slate-700">
                          Total Quoted Amount (₹ INR) <span className="text-rose-600">*</span>
                        </label>
                        <div className="relative">
                          <span className="absolute left-3 top-2 text-xs font-bold text-slate-500">
                            ₹
                          </span>
                          <input
                            ref={quoteInputRef}
                            type="number"
                            step="0.01"
                            min="0"
                            placeholder="e.g. 4850000.00"
                            value={quotedAmount}
                            onChange={(e) => setQuotedAmount(e.target.value)}
                            disabled={!isDraft}
                            className="w-full rounded-lg border border-slate-300 bg-slate-50/50 pl-8 pr-3 py-2 text-xs font-mono text-slate-900 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-600 disabled:opacity-75 disabled:bg-slate-100"
                          />
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-bold text-slate-700">
                          Currency
                        </label>
                        <input
                          type="text"
                          value={currency}
                          disabled
                          className="w-full rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-xs font-mono text-slate-700 uppercase"
                          readOnly
                        />
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-slate-700">
                        Commercial Notes & Payment Terms
                      </label>
                      <textarea
                        rows={3}
                        placeholder="Provide details regarding payment milestones, price validity (e.g. 90 days), AMC warranty inclusions, or delivery transit insurance..."
                        value={commercialNotes}
                        onChange={(e) => setCommercialNotes(e.target.value)}
                        disabled={!isDraft}
                        className="w-full rounded-lg border border-slate-300 bg-slate-50/50 p-3 text-xs text-slate-900 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-600 disabled:opacity-75 disabled:bg-slate-100 font-sans"
                      />
                    </div>
                  </div>

                  {/* Technical Proposal Section */}
                  <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
                    <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3">
                      <div className="rounded-lg bg-blue-50 p-2 text-blue-700">
                        <Briefcase className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                          Technical & Operational Response
                        </h2>
                        <p className="text-xs text-slate-500">
                          {isSubmitted
                            ? "Submitted technical scope offering."
                            : "Summarize your technical offering, compliance with equipment specs, and timeline."}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-slate-700">
                        Technical Offering & Scope Summary <span className="text-rose-600">*</span>
                      </label>
                      <textarea
                        rows={4}
                        placeholder="Provide an overview of make, model, architecture, certifications, or OEM authorizations being offered in response to the tender scope..."
                        value={technicalSummary}
                        onChange={(e) => setTechnicalSummary(e.target.value)}
                        disabled={!isDraft}
                        className="w-full rounded-lg border border-slate-300 bg-slate-50/50 p-3 text-xs text-slate-900 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-600 disabled:opacity-75 disabled:bg-slate-100 font-sans"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-slate-700">
                        Remarks, Delivery Lead Time & Site Readiness
                      </label>
                      <textarea
                        rows={3}
                        placeholder="State anticipated delivery timeline from LOA issuance, pre-dispatch inspection protocols, or site readiness assumptions..."
                        value={remarks}
                        onChange={(e) => setRemarks(e.target.value)}
                        disabled={!isDraft}
                        className="w-full rounded-lg border border-slate-300 bg-slate-50/50 p-3 text-xs text-slate-900 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-600 disabled:opacity-75 disabled:bg-slate-100 font-sans"
                      />
                    </div>
                  </div>

                  {/* Save Draft Action (Only for DRAFT) */}
                  {isDraft && (
                    <div className="flex items-center justify-between bg-slate-50 p-4 rounded-xl border border-slate-200">
                      <p className="text-xs text-slate-500">
                        Last persisted: <strong>{formatDateTime(bid.updated_at)}</strong>
                      </p>
                      <button
                        type="submit"
                        disabled={saving}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-blue-700 px-5 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-800 transition-colors disabled:opacity-50"
                      >
                        {saving ? (
                          <>
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Save className="h-3.5 w-3.5" />
                            Save Proposal Draft
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </form>

                {/* Part 3E: Declaration & Final Submission Box */}
                {isDraft && (
                  <div className="rounded-xl border-2 border-blue-200 bg-linear-to-b from-blue-50/50 to-white p-6 shadow-xs space-y-4">
                    <div className="flex items-center gap-2.5 border-b border-blue-100 pb-3">
                      <div className="rounded-lg bg-blue-600 p-2 text-white">
                        <Send className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                          Final Bid Declaration & Submission (Part 3E)
                        </h2>
                        <p className="text-xs text-slate-500">
                          Confirm accuracy of proposal data and execute binding final submission.
                        </p>
                      </div>
                    </div>

                    {submitError && (
                      <div className="flex items-start gap-2 rounded-lg bg-rose-50 p-3 text-xs text-rose-800 border border-rose-200">
                        <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-600" />
                        <span>{submitError}</span>
                      </div>
                    )}

                    {/* Statutory Declaration Checkbox */}
                    <div className="rounded-lg bg-white p-4 border border-blue-200 shadow-2xs space-y-2">
                      <label className="flex items-start gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={declarationAccepted}
                          onChange={(e) => setDeclarationAccepted(e.target.checked)}
                          className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-600"
                        />
                        <span className="text-xs text-slate-800 leading-relaxed select-none">
                          <strong>Statutory Bidder Declaration:</strong> I hereby certify that the commercial quotation, technical parameters, and uploaded statutory documents submitted in this proposal are authentic, accurate, and compliant with the requirements of tender <strong>{bid.tender.tender_number}</strong>.
                        </span>
                      </label>
                    </div>

                    {/* Final Submission Action Button */}
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
                      <p className="text-[11px] text-slate-500">
                        {readiness?.ready_to_submit
                          ? declarationAccepted
                            ? "All criteria satisfied. Click to submit final bid."
                            : "Please accept the declaration checkbox above to enable submission."
                          : "Resolve all incomplete readiness items above before submission."}
                      </p>

                      <button
                        type="button"
                        onClick={() => setIsSubmitModalOpen(true)}
                        disabled={!readiness?.ready_to_submit || !declarationAccepted || submitting}
                        className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
                      >
                        <Lock className="h-4 w-4" />
                        Submit Final Bid Proposal
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Right 1 Column: Progress Pipeline & Tender Overview */}
              <div className="space-y-6">
                {/* Submission Progress Tracker */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                    Submission Progress Pipeline
                  </h3>

                  <div className="space-y-3 text-xs">
                    {/* 1. Profile */}
                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        <span className="font-bold">1. Bidder Profile</span>
                      </div>
                      <span className="text-[11px] font-bold text-emerald-700 bg-emerald-100/70 px-2 py-0.5 rounded">
                        Complete
                      </span>
                    </div>

                    {/* 2. Proposal Details */}
                    <div
                      className={`flex items-center justify-between p-2.5 rounded-lg border ${
                        readiness?.checks.bid_details_complete
                          ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                          : "bg-blue-50 border-blue-200 text-blue-900"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {readiness?.checks.bid_details_complete ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        ) : (
                          <FileText className="h-4 w-4 text-blue-600" />
                        )}
                        <span className="font-bold">2. Proposal Details</span>
                      </div>
                      <span
                        className={`text-[11px] font-bold px-2 py-0.5 rounded ${
                          readiness?.checks.bid_details_complete
                            ? "text-emerald-700 bg-emerald-100"
                            : "text-blue-700 bg-blue-100"
                        }`}
                      >
                        {readiness?.checks.bid_details_complete ? "Complete" : "Drafting"}
                      </span>
                    </div>

                    {/* 3. Documents */}
                    <div
                      className={`flex items-center justify-between p-2.5 rounded-lg border ${
                        readiness?.checks.mandatory_documents_complete
                          ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                          : "bg-blue-50 border-blue-200 text-blue-900"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {readiness?.checks.mandatory_documents_complete ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        ) : (
                          <FileUp className="h-4 w-4 text-blue-600" />
                        )}
                        <span className="font-bold">3. Document Package</span>
                      </div>
                      <span
                        className={`text-[11px] font-bold px-2 py-0.5 rounded ${
                          readiness?.checks.mandatory_documents_complete
                            ? "text-emerald-700 bg-emerald-100"
                            : "text-blue-700 bg-blue-100"
                        }`}
                      >
                        {docsSummary
                          ? `${docsSummary.uploaded_required}/${docsSummary.total_required} Ready`
                          : "0 Uploaded"}
                      </span>
                    </div>

                    {/* 4. Final Submission */}
                    <div
                      className={`flex items-center justify-between p-2.5 rounded-lg border ${
                        isSubmitted
                          ? "bg-emerald-600 border-emerald-700 text-white font-bold"
                          : readiness?.ready_to_submit
                          ? "bg-blue-50 border-blue-300 text-blue-900 font-bold"
                          : "bg-slate-50 border-slate-200 text-slate-600"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {isSubmitted ? (
                          <ShieldCheck className="h-4 w-4 text-white" />
                        ) : (
                          <Lock className="h-4 w-4 text-slate-400" />
                        )}
                        <span>4. Final Submission</span>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          isSubmitted
                            ? "bg-white text-emerald-800"
                            : readiness?.ready_to_submit
                            ? "bg-blue-100 text-blue-800"
                            : "bg-slate-200 text-slate-600"
                        }`}
                      >
                        {isSubmitted ? "SUBMITTED" : readiness?.ready_to_submit ? "Ready" : "Pending"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Procurement Timeline Reference */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                      Tender Timeline
                    </h3>
                    <span
                      className={`rounded px-2 py-0.5 text-[11px] font-bold border ${deadline.colorClass}`}
                    >
                      {deadline.text}
                    </span>
                  </div>

                  <div className="space-y-2.5 text-xs">
                    <div className="flex items-start gap-2">
                      <Clock className="h-3.5 w-3.5 text-rose-600 mt-0.5 shrink-0" />
                      <div>
                        <span className="text-slate-500">Submission Closes:</span>
                        <p className="font-bold text-slate-900">
                          {formatDateTime(bid.tender.submission_end_date)}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-start gap-2">
                      <Building2 className="h-3.5 w-3.5 text-slate-400 mt-0.5 shrink-0" />
                      <div>
                        <span className="text-slate-500">Procuring Authority:</span>
                        <p className="font-semibold text-slate-800">
                          {bid.tender.organization_name || "Procuring Entity"}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bidder Organization Summary */}
                {bid.bidder_organization && (
                  <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                      Participating Entity
                    </h3>
                    <div className="text-xs space-y-1.5 bg-slate-50 p-3.5 rounded-lg border border-slate-200">
                      <p className="font-bold text-slate-900">
                        {bid.bidder_organization.name}
                      </p>
                      {bid.bidder_organization.pan_number && (
                        <p className="text-slate-600 font-mono text-[11px]">
                          PAN: <strong>{bid.bidder_organization.pan_number}</strong>
                        </p>
                      )}
                      {bid.bidder_organization.gstin && (
                        <p className="text-slate-600 font-mono text-[11px]">
                          GSTIN: <strong>{bid.bidder_organization.gstin}</strong>
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* Final Submission Confirmation Dialog (Part 3E) */}
      {/* ========================================================================= */}
      {isSubmitModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center gap-3 text-emerald-600">
              <div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700">
                <Lock className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Submit Final Bid Proposal?
                </h3>
                <p className="text-xs text-slate-500 font-mono">
                  {bid?.bid_number}
                </p>
              </div>
            </div>

            <div className="rounded-xl bg-amber-50 p-4 border border-amber-200 text-xs text-amber-900 space-y-2">
              <p className="font-bold flex items-center gap-1.5 text-amber-800">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                Permanent Proposal Locking Notice
              </p>
              <p className="leading-relaxed text-[11px] text-amber-800">
                After submission, your bid will become <strong>SUBMITTED</strong> and completely locked. You will no longer be able to edit commercial rates, update technical scope, or modify documents.
              </p>
            </div>

            <div className="rounded-lg bg-slate-50 p-3 text-xs space-y-1 border border-slate-200">
              <div className="flex justify-between">
                <span className="text-slate-500">Quoted Amount:</span>
                <span className="font-bold font-mono text-slate-900">
                  {formatCurrency(quotedAmount, currency)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Uploaded Documents:</span>
                <span className="font-bold text-slate-900">
                  {documents.length} verified files
                </span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setIsSubmitModalOpen(false)}
                disabled={submitting}
                className="rounded-lg px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleFinalSubmitConfirm}
                disabled={submitting}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-5 py-2 text-xs font-bold text-white shadow-xs hover:bg-emerald-700 transition-colors disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Submitting Final Bid...
                  </>
                ) : (
                  <>
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Confirm & Submit Bid
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Upload Document Modal */}
      {/* ========================================================================= */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-blue-50 p-2 text-blue-700">
                  <UploadCloud className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Upload Bid Compliance Document
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    {uploadTargetReqName
                      ? `Target: ${uploadTargetReqName}`
                      : "General Proposal Document"}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsUploadModalOpen(false)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              {uploadError && (
                <div className="flex items-start gap-2 rounded-lg bg-rose-50 p-3 text-xs text-rose-800 border border-rose-200">
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-600" />
                  <span>{uploadError}</span>
                </div>
              )}

              {uploadSuccessMsg && (
                <div className="flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-xs text-emerald-800 border border-emerald-200">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  <span>{uploadSuccessMsg}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">
                  Document Classification <span className="text-rose-600">*</span>
                </label>
                <select
                  value={selectedDocType}
                  onChange={(e) => setSelectedDocType(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
                >
                  {DOCUMENT_TYPES.map((dt) => (
                    <option key={dt.value} value={dt.value}>
                      {dt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* File Dropzone */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">
                  Select File (PDF, PNG, JPG, DOCX, XLSX $\le$ 10 MB){" "}
                  <span className="text-rose-600">*</span>
                </label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="cursor-pointer rounded-xl border-2 border-dashed border-slate-300 hover:border-blue-500 bg-slate-50/50 hover:bg-blue-50/30 p-6 text-center transition-all"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <FileUp className="mx-auto h-8 w-8 text-slate-400 mb-2" />
                  {selectedFile ? (
                    <div className="space-y-1">
                      <p className="text-xs font-bold text-blue-700">
                        {selectedFile.name}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        Size: {formatFileSize(selectedFile.size)}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <p className="text-xs font-semibold text-slate-700">
                        Click to browse or drop file here
                      </p>
                      <p className="text-[11px] text-slate-400">
                        Max file size: 10 MB per document
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">
                  Document Notes / Remarks (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Valid until March 2027, Certificate No: 12345"
                  value={uploadNotes}
                  onChange={(e) => setUploadNotes(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3 py-2 text-xs text-slate-900 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-600"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsUploadModalOpen(false)}
                  disabled={uploading}
                  className="rounded-lg px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading || !selectedFile}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-700 px-5 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-800 transition-colors disabled:opacity-50"
                >
                  {uploading ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <UploadCloud className="h-3.5 w-3.5" />
                      Upload to Private Storage
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Replace Document Confirmation Modal */}
      {/* ========================================================================= */}
      {replaceTargetDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center gap-2 text-blue-700">
              <RefreshCw className="h-5 w-5" />
              <h3 className="text-sm font-bold text-slate-900">
                Replace Document
              </h3>
            </div>

            <div className="rounded-lg bg-blue-50 p-3.5 text-xs text-blue-900 border border-blue-200 space-y-1">
              <p className="font-semibold">
                Current active document: {replaceTargetDoc.original_filename} (v{replaceTargetDoc.version})
              </p>
              <p className="text-[11px] text-blue-700">
                The current document will be marked as replaced and preserved for audit trail. The new file will become active as v{replaceTargetDoc.version + 1}.
              </p>
            </div>

            <form onSubmit={handleReplaceSubmit} className="space-y-4">
              {uploadError && (
                <div className="flex items-start gap-2 rounded-lg bg-rose-50 p-3 text-xs text-rose-800 border border-rose-200">
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-600" />
                  <span>{uploadError}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">
                  Choose New File (PDF, PNG, JPG, DOCX $\le$ 10 MB){" "}
                  <span className="text-rose-600">*</span>
                </label>
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx"
                  onChange={handleFileChange}
                  className="w-full text-xs text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">
                  Updated Notes (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Revised certificate with updated validity"
                  value={uploadNotes}
                  onChange={(e) => setUploadNotes(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3 py-2 text-xs text-slate-900 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-600"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setReplaceTargetDoc(null)}
                  disabled={actionInProgress}
                  className="rounded-lg px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionInProgress || !selectedFile}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-700 px-5 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-800 transition-colors disabled:opacity-50"
                >
                  {actionInProgress ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Replacing...
                    </>
                  ) : (
                    "Confirm Replacement"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Remove Document Confirmation Modal */}
      {/* ========================================================================= */}
      {removeTargetDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center gap-2 text-rose-600">
              <AlertTriangle className="h-5 w-5" />
              <h3 className="text-sm font-bold text-slate-900">
                Remove Document from Active Bid?
              </h3>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to remove <strong>{removeTargetDoc.original_filename}</strong> from this active bid proposal?
              The file will be marked as removed, and the corresponding tender requirement will become incomplete.
            </p>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setRemoveTargetDoc(null)}
                disabled={actionInProgress}
                className="rounded-lg px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRemoveConfirm}
                disabled={actionInProgress}
                className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-rose-700 transition-colors disabled:opacity-50"
              >
                {actionInProgress ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Removing...
                  </>
                ) : (
                  "Confirm Removal"
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Part 4B: Extracted Text Preview Modal */}
      {/* ========================================================================= */}
      {viewingExtractedTextDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl space-y-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-slate-900">
                <FileText className="h-5 w-5 text-blue-600" />
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Extracted Text Preview (PyMuPDF)
                  </h3>
                  <p className="text-xs text-slate-500 font-mono">
                    {viewingExtractedTextDoc.original_filename}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setViewingExtractedTextDoc(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {loadingExtractedText ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-3">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                <p className="text-xs text-slate-500 font-medium">
                  Loading extracted document text...
                </p>
              </div>
            ) : extractedTextData ? (
              <div className="space-y-4 overflow-y-auto flex-1 pr-1">
                {/* Part 4D: Classification Summary Banner */}
                {extractedTextData.detected_document_type && (
                  <div className={`rounded-xl border p-3.5 space-y-2 ${
                    extractedTextData.classification_requires_review
                      ? "border-amber-200 bg-amber-50/50"
                      : "border-indigo-100 bg-indigo-50/40"
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <FileCheck className="h-4 w-4 text-indigo-700" />
                        <span className="text-xs font-bold text-slate-900">
                          Classification: {extractedTextData.detected_document_type.replace(/_/g, " ")}
                        </span>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        extractedTextData.classification_confidence_level === "HIGH"
                          ? "bg-emerald-100 text-emerald-800 border-emerald-200"
                          : extractedTextData.classification_confidence_level === "MEDIUM"
                          ? "bg-blue-100 text-blue-800 border-blue-200"
                          : "bg-amber-100 text-amber-800 border-amber-200"
                      }`}>
                        {extractedTextData.classification_confidence_level || "LOW"} Confidence ({Math.round((extractedTextData.classification_confidence || 0) * 100)}%)
                      </span>
                    </div>
                    {extractedTextData.classification_reason && (
                      <p className="text-[11px] text-slate-600">
                        <strong className="text-slate-700">Classification Evidence:</strong> {extractedTextData.classification_reason}
                      </p>
                    )}
                    {extractedTextData.classification_requires_review && (
                      <div className="flex items-center gap-1.5 text-[11px] font-medium text-amber-800 bg-amber-100/60 p-2 rounded-lg border border-amber-200">
                        <AlertTriangle className="h-3.5 w-3.5 text-amber-700 shrink-0" />
                        <span>Document mismatch or review required. Please ensure this file satisfies the requested tender condition.</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Extraction Metadata Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-200">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Extraction Method</span>
                    <p className="font-bold text-slate-800">{extractedTextData.extraction_method}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-200">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Pages Extracted</span>
                    <p className="font-bold text-slate-800">{extractedTextData.page_count || 1} Pages</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-200">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Character Count</span>
                    <p className="font-bold text-slate-800">
                      {extractedTextData.character_count?.toLocaleString() || 0} Chars
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-200">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Quality Label</span>
                    <p className="font-bold text-emerald-700">{extractedTextData.quality_label || "Digital PDF"}</p>
                  </div>
                </div>

                {/* Part 4E: Structured Entity Extraction Display */}
                {extractedTextData.extracted_data && extractedTextData.extracted_data.fields && Object.keys(extractedTextData.extracted_data.fields).length > 0 && (
                  <div className="rounded-xl border border-blue-100 bg-blue-50/30 p-3.5 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <Sparkles className="h-4 w-4 text-blue-600" />
                        <span className="text-xs font-bold text-slate-900">
                          Extracted Structured Entities ({Object.keys(extractedTextData.extracted_data.fields).length} Fields)
                        </span>
                      </div>
                      {extractedTextData.extraction_requires_review && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200 flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3 text-amber-700" /> Review Required
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {Object.entries(extractedTextData.extracted_data.fields).map(([fieldName, fieldData]: [string, any]) => (
                        <div key={fieldName} className="rounded-lg border border-slate-200 bg-white p-2.5 space-y-1 shadow-2xs">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="font-bold text-slate-500 uppercase tracking-wider text-[9px]">
                              {fieldName.replace(/_/g, " ")}
                            </span>
                            <div className="flex items-center gap-1">
                              <span className="text-[9px] font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                                Page {fieldData.page || 1}
                              </span>
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                                fieldData.confidence >= 0.85
                                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                  : fieldData.confidence >= 0.65
                                  ? "bg-blue-50 text-blue-700 border border-blue-200"
                                  : "bg-amber-50 text-amber-700 border border-amber-200"
                              }`}>
                                {Math.round((fieldData.confidence || 0) * 100)}%
                              </span>
                            </div>
                          </div>
                          <div className="font-mono text-xs font-bold text-slate-900 break-words">
                            {typeof fieldData.value === "object"
                              ? JSON.stringify(fieldData.value, null, 1)
                              : typeof fieldData.value === "boolean"
                              ? (fieldData.value ? "True" : "False (Not Blacklisted / Debarred)")
                              : String(fieldData.value)}
                          </div>
                          {fieldData.evidence && (
                            <p className="text-[10px] text-slate-500 italic truncate" title={fieldData.evidence}>
                              Evidence: &ldquo;{fieldData.evidence}&rdquo;
                            </p>
                          )}
                          {fieldData.is_conflict && (
                            <div className="text-[10px] font-bold text-red-600 bg-red-50 p-1 rounded border border-red-200">
                              Conflict detected with: {Array.isArray(fieldData.conflict_values) ? fieldData.conflict_values.join(", ") : ""}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Part 5A: Development / Mock Verification Engine Telemetry */}
                <div className="rounded-xl border border-indigo-200 bg-linear-to-b from-indigo-50/50 to-white p-4 space-y-3 shadow-2xs">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-indigo-100 pb-2.5">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-indigo-700" />
                      <div>
                        <h4 className="text-xs font-bold text-slate-900">
                          Claim Verification Engine
                        </h4>
                        <span className="text-[10px] font-semibold text-indigo-700">
                          Development / Mock Verification Source (Synthetic Sandbox)
                        </span>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleVerifyDocument(viewingExtractedTextDoc.id)}
                      disabled={verifyingDocId === viewingExtractedTextDoc.id}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 hover:bg-indigo-800 text-white text-[11px] font-bold px-3 py-1.5 shadow-2xs transition-colors disabled:opacity-50"
                    >
                      {verifyingDocId === viewingExtractedTextDoc.id ? (
                        <>
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Verifying Claim...
                        </>
                      ) : (
                        <>
                          <RotateCw className="h-3 w-3" />
                          Run Mock Verification
                        </>
                      )}
                    </button>
                  </div>

                  {bidVerifications && bidVerifications.verifications && bidVerifications.verifications.length > 0 ? (
                    <div className="space-y-3">
                      {bidVerifications.verifications.map((vItem) => (
                        <div
                          key={vItem.id}
                          className="rounded-xl border border-slate-200 bg-white p-3.5 space-y-2.5 shadow-2xs text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-900 text-sm">
                                {vItem.verification_type} Claim
                              </span>
                              <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                                {vItem.source_name} ({vItem.source_type})
                              </span>
                              <span className="text-[10px] text-slate-400 font-semibold">
                                Attempt #{vItem.attempt_number}
                              </span>
                            </div>

                            <div className="flex items-center gap-2">
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                                  vItem.verification_status === "VERIFIED"
                                    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                                    : vItem.verification_status === "NOT_VERIFIED"
                                    ? "bg-rose-50 text-rose-800 border-rose-200"
                                    : vItem.verification_status === "NEEDS_REVIEW"
                                    ? "bg-amber-50 text-amber-800 border-amber-200"
                                    : vItem.verification_status === "UNAVAILABLE"
                                    ? "bg-slate-100 text-slate-800 border-slate-300"
                                    : "bg-red-100 text-red-800 border-red-300"
                                }`}
                              >
                                {vItem.verification_status.replace(/_/g, " ")}
                              </span>

                              {vItem.is_retryable && (
                                <button
                                  type="button"
                                  onClick={() => handleRetryVerification(vItem.id)}
                                  disabled={retryingVerificationId === vItem.id}
                                  className="inline-flex items-center gap-1 text-[10px] font-bold text-indigo-700 hover:text-indigo-900 border border-indigo-200 bg-indigo-50 px-2 py-0.5 rounded"
                                >
                                  {retryingVerificationId === vItem.id ? (
                                    <Loader2 className="h-2.5 w-2.5 animate-spin" />
                                  ) : (
                                    <RefreshCw className="h-2.5 w-2.5" />
                                  )}
                                  Retry
                                </button>
                              )}
                            </div>
                          </div>

                          {/* Identifier Row */}
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                            <div>
                              <span className="text-[9px] font-bold uppercase text-slate-400">Claimed Identifier</span>
                              <p className="font-mono font-bold text-slate-900 mt-0.5">{vItem.claimed_value}</p>
                            </div>
                            <div>
                              <span className="text-[9px] font-bold uppercase text-slate-400">Verified Match Value</span>
                              <p className="font-mono font-bold text-slate-900 mt-0.5">
                                {vItem.verified_value || "—"}
                              </p>
                            </div>
                          </div>

                          {/* Domain Specific Attributes */}
                          {vItem.evidence && (
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] bg-slate-50/60 p-2.5 rounded-lg border border-slate-100">
                              {(vItem.evidence.legal_name || vItem.evidence.registry_legal_name || vItem.evidence.registry_name || vItem.evidence.registry_enterprise_name || vItem.evidence.company_name || vItem.evidence.registry_company_name || vItem.evidence.entity_name || vItem.evidence.establishment_name || vItem.evidence.employer_name || vItem.evidence.oem_name) && (
                                <div>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">Registry Entity / OEM</span>
                                  <p className="font-bold text-slate-800 truncate">
                                    {vItem.evidence.oem_name ? `${vItem.evidence.oem_name} (OEM)` : (vItem.evidence.registry_legal_name || vItem.evidence.registry_name || vItem.evidence.registry_enterprise_name || vItem.evidence.registry_company_name || vItem.evidence.company_name || vItem.evidence.entity_name || vItem.evidence.establishment_name || vItem.evidence.employer_name || vItem.evidence.legal_name || "—")}
                                  </p>
                                </div>
                              )}

                              {vItem.evidence.authorized_entity && (
                                <div>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">Authorized Bidder / Grantee</span>
                                  <p className="font-bold text-emerald-700 truncate">
                                    {vItem.evidence.authorized_entity}
                                  </p>
                                </div>
                              )}

                              {vItem.evidence.product_scope && (
                                <div className="sm:col-span-2">
                                  <span className="text-[9px] font-bold uppercase text-slate-400">Authorized Product Scope</span>
                                  <p className="font-medium text-slate-700 text-[10px]">
                                    {vItem.evidence.product_scope}
                                  </p>
                                </div>
                              )}

                              {vItem.evidence.supplier_class && (
                                <div>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">MII Supplier Class</span>
                                  <p className="font-bold text-indigo-700">
                                    {vItem.evidence.supplier_class} (Local Content: {vItem.evidence.verified_percentage ?? vItem.evidence.claimed_percentage}%)
                                  </p>
                                </div>
                              )}

                              {vItem.evidence.standard_number && (
                                <div>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">BIS Standard Number</span>
                                  <p className="font-bold text-slate-800">
                                    {vItem.evidence.standard_number} ({vItem.evidence.product_name || "Certified Product"})
                                  </p>
                                </div>
                              )}

                              {vItem.evidence.is_internal_check && (
                                <div>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">Verification Method</span>
                                  <p className="font-bold text-slate-700">
                                    Internal Evidence Check (Checks: {vItem.evidence.score})
                                  </p>
                                </div>
                              )}

                              {vItem.evidence.authority && (
                                <div>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">Issuing / Enforcement Authority</span>
                                  <p className="font-bold text-slate-800 truncate">
                                    {vItem.evidence.authority} (Ref: {vItem.evidence.reference_number || "—"})
                                  </p>
                                </div>
                              )}

                              {vItem.evidence.total_checks !== undefined && (
                                <div className="sm:col-span-2">
                                  <span className="text-[9px] font-bold uppercase text-slate-400">Cross-Document Matrix</span>
                                  <p className="font-bold text-indigo-700">
                                    {vItem.evidence.matched_checks}/{vItem.evidence.total_checks} Checks Aligned ({vItem.evidence.review_required_checks || 0} Require Review)
                                  </p>
                                </div>
                              )}

                              {vItem.evidence.enterprise_classification && (
                                <div>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">MSME Classification</span>
                                  <p className="font-bold text-indigo-700">
                                    {vItem.evidence.enterprise_classification} ({vItem.evidence.major_activity || "Enterprise"})
                                  </p>
                                </div>
                              )}

                              {vItem.evidence.company_type && (
                                <div>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">Company Type</span>
                                  <p className="font-bold text-slate-800">
                                    {vItem.evidence.company_type}
                                  </p>
                                </div>
                              )}

                              {vItem.evidence.sector && (
                                <div>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">Startup Sector</span>
                                  <p className="font-bold text-slate-800">
                                    {vItem.evidence.sector}
                                  </p>
                                </div>
                              )}

                              {vItem.evidence.valid_until && (
                                <div>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">Validity Window</span>
                                  <p className="font-bold text-slate-800">
                                    {vItem.evidence.valid_from ? `${vItem.evidence.valid_from} to ` : ""}{vItem.evidence.valid_until}
                                  </p>
                                </div>
                              )}

                              {vItem.evidence.entity_type_description && (
                                <div>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">Taxpayer Entity Type</span>
                                  <p className="font-bold text-slate-800">
                                    {vItem.evidence.entity_type_description}
                                  </p>
                                </div>
                              )}

                              {(vItem.evidence.registration_status || vItem.evidence.company_status || vItem.evidence.startup_status || vItem.evidence.authorization_status) && (
                                <div>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">Registration / Authorization Status</span>
                                  <span className={`inline-block px-1.5 py-0.2 rounded text-[10px] font-bold ${
                                    (vItem.evidence.registration_status || vItem.evidence.company_status || vItem.evidence.startup_status || vItem.evidence.authorization_status) === "ACTIVE" ||
                                    (vItem.evidence.registration_status || vItem.evidence.company_status || vItem.evidence.startup_status || vItem.evidence.authorization_status) === "VALID" ||
                                    (vItem.evidence.registration_status || vItem.evidence.company_status || vItem.evidence.startup_status || vItem.evidence.authorization_status) === "RECOGNIZED"
                                      ? "bg-emerald-100 text-emerald-800"
                                      : "bg-amber-100 text-amber-800"
                                  }`}>
                                    {vItem.evidence.registration_status || vItem.evidence.company_status || vItem.evidence.startup_status || vItem.evidence.authorization_status}
                                  </span>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Match Evidence Summary */}
                          {vItem.evidence && vItem.evidence.reason && (
                            <div className="text-[10px] text-slate-600 bg-slate-50 p-2 rounded border border-slate-200">
                              <span className="font-bold text-slate-700">Verification Outcome:</span> {vItem.evidence.reason}
                            </div>
                          )}

                          {vItem.error_message && (
                            <div className="text-[10px] text-rose-700 bg-rose-50 p-2 rounded border border-rose-200">
                              <strong>Notice:</strong> {vItem.error_message}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-3 text-center text-xs text-slate-500 bg-slate-50 rounded-lg">
                      No claims verified yet for this document. Click <strong>Run Mock Verification</strong> to validate extracted statutory identifiers.
                    </div>
                  )}
                </div>

                {/* Text Content Area */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-700">
                      Normalized Machine-Readable Text
                    </label>
                    <button
                      type="button"
                      onClick={handleCopyExtractedText}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-blue-700 hover:text-blue-800"
                    >
                      {copiedText ? (
                        <>
                          <Check className="h-3 w-3 text-emerald-600" />
                          <span className="text-emerald-700">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3" />
                          Copy Text
                        </>
                      )}
                    </button>
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-xs text-slate-800 max-h-72 overflow-y-auto whitespace-pre-wrap leading-relaxed select-text">
                    {extractedTextData.normalized_text || extractedTextData.raw_text || (
                      <span className="text-slate-400 italic">No text extracted.</span>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-xs text-slate-500">
                No extracted text available for this document.
              </div>
            )}

            <div className="flex items-center justify-end pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setViewingExtractedTextDoc(null)}
                className="rounded-lg bg-slate-100 px-4 py-2 text-xs font-bold text-slate-700 hover:bg-slate-200"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Part 11: Document Quality Diagnostics Modal */}
      <DocumentQualityModal
        isOpen={!!qualityModalDoc}
        onClose={() => {
          setQualityModalDoc(null);
          setQualityResultData(null);
        }}
        quality={qualityResultData}
        documentName={qualityModalDoc?.original_filename}
        documentType={qualityModalDoc?.document_type}
      />
    </DashboardLayout>
  );
}
