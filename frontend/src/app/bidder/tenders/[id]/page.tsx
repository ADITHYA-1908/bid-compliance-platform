"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  api,
  ApiError,
  BidderTenderDetail,
  BidderTenderRequirementSummary,
  BidListItem,
  ProfileCompletionInfo,
} from "@/lib/api";
import { formatCurrency, formatDateTime, formatDeadlineRemaining } from "@/lib/formatters";
import {
  ArrowLeft,
  Building2,
  Calendar,
  Clock,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  Info,
  Loader2,
  RefreshCw,
  Send,
  ArrowRight,
  FileEdit,
  X,
  AlertTriangle,
  ExternalLink,
} from "lucide-react";

export default function BidderTenderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const tenderId = params?.id as string;

  const [tender, setTender] = useState<BidderTenderDetail | null>(null);
  const [existingBid, setExistingBid] = useState<BidListItem | null>(null);
  const [profileCompletion, setProfileCompletion] = useState<ProfileCompletionInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Modal and Bid Creation states
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const [creatingBid, setCreatingBid] = useState<boolean>(false);
  const [creationError, setCreationError] = useState<string | null>(null);

  const fetchTenderDetailAndStatus = async () => {
    if (!tenderId) return;
    setLoading(true);
    setErrorMessage(null);
    try {
      // 1. Fetch tender details
      const tenderData = await api.getBidderTender(tenderId);
      setTender(tenderData);

      // 2. Fetch existing bid for this tender if any
      try {
        const bidData = await api.checkTenderBid(tenderId);
        setExistingBid(bidData);
      } catch {
        setExistingBid(null);
      }

      // 3. Fetch bidder profile completeness
      try {
        const profileResp = await api.getBidderProfile();
        setProfileCompletion(profileResp.completion);
      } catch {
        // Non-blocking
      }
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 404) {
        setErrorMessage(
          "This procurement opportunity is either not published or not currently open for bidding."
        );
      } else {
        setErrorMessage(
          err instanceof ApiError ? err.message : "Failed to load tender details."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTenderDetailAndStatus();
  }, [tenderId]);

  const handleStartBid = async () => {
    if (!tenderId) return;
    setCreatingBid(true);
    setCreationError(null);
    try {
      const newBid = await api.createBid(tenderId);
      setShowConfirmModal(false);
      // Navigate to the newly created draft bid workspace
      router.push(`/bidder/bids/${newBid.id}`);
    } catch (err: any) {
      setCreationError(
        err instanceof ApiError
          ? err.message
          : "Failed to initiate tender participation. Please check your profile and try again."
      );
      setCreatingBid(false);
    }
  };

  // Group requirements by category
  const requirementsByCategory: Record<string, BidderTenderRequirementSummary[]> = {};
  if (tender?.requirements) {
    tender.requirements.forEach((req) => {
      const cat = req.category || "GENERAL";
      if (!requirementsByCategory[cat]) {
        requirementsByCategory[cat] = [];
      }
      requirementsByCategory[cat].push(req);
    });
  }

  const deadline = formatDeadlineRemaining(tender?.submission_end_date);
  const isOpen = tender?.status === "OPEN";
  const isDeadlinePassed = deadline.isPassed;
  const isProfileReady = profileCompletion ? profileCompletion.is_complete : true;
  const canParticipate = isOpen && !isDeadlinePassed && !existingBid && isProfileReady;

  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title={tender ? tender.title : "Tender Details"}
      description={
        tender
          ? `Reference: ${tender.tender_number} • Issued by ${tender.organization.name}`
          : "Procurement opportunity details and eligibility criteria."
      }
      breadcrumbs={[
        { label: "Bidder Portal", href: "/bidder" },
        { label: "Tenders", href: "/bidder/tenders" },
        { label: tender?.tender_number || "Tender Details" },
      ]}
    >
      <div className="space-y-6">
        {/* Back Navigation Bar */}
        <div className="flex items-center justify-between">
          <Link
            href="/bidder/tenders"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-blue-700 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Available Tenders
          </Link>
          <span className="text-xs text-slate-500 font-mono">
            Tender ID: {tenderId}
          </span>
        </div>

        {loading ? (
          <div className="rounded-xl border border-slate-200 bg-white p-16 text-center shadow-xs">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-700" />
            <p className="mt-3 text-sm font-medium text-slate-600">
              Loading tender specifications & compliance rules...
            </p>
          </div>
        ) : errorMessage || !tender ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-8 text-center shadow-xs">
            <AlertCircle className="mx-auto h-10 w-10 text-rose-600" />
            <h3 className="mt-3 text-base font-bold text-rose-900">
              Tender Unavailable
            </h3>
            <p className="mt-1 text-xs text-rose-700 max-w-md mx-auto">
              {errorMessage || "The requested tender could not be found."}
            </p>
            <div className="mt-5 flex items-center justify-center gap-3">
              <button
                onClick={fetchTenderDetailAndStatus}
                className="inline-flex items-center gap-1.5 rounded-md bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700 shadow-xs"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </button>
              <Link
                href="/bidder/tenders"
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs"
              >
                Browse Other Tenders
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-600 tracking-wider">
                      {tender.tender_number}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold border ${
                        isOpen
                          ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                          : "bg-blue-50 text-blue-800 border-blue-200"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          isOpen ? "bg-emerald-600 animate-pulse" : "bg-blue-600"
                        }`}
                      />
                      {isOpen ? "OPEN FOR BIDDING" : "UPCOMING NOTICE"}
                    </span>
                    {tender.category && (
                      <span className="rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
                        {tender.category}
                      </span>
                    )}
                    {tender.procurement_type && (
                      <span className="rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
                        {tender.procurement_type}
                      </span>
                    )}
                  </div>

                  <h1 className="text-xl font-bold text-slate-900 leading-snug">
                    {tender.title}
                  </h1>

                  <div className="flex items-center gap-2 text-xs text-slate-600">
                    <Building2 className="h-4 w-4 text-slate-400 shrink-0" />
                    <span>
                      <strong className="text-slate-800">{tender.organization.name}</strong>
                      {tender.department ? ` • ${tender.department}` : ""}
                    </span>
                  </div>
                </div>

                {/* Estimated Value & Action Box */}
                <div className="flex md:flex-col items-baseline md:items-end justify-between border-t md:border-t-0 pt-3 md:pt-0 border-slate-100 shrink-0">
                  <span className="text-xs text-slate-500 font-medium">Estimated Value</span>
                  <span className="font-mono text-2xl font-extrabold text-slate-900">
                    {formatCurrency(tender.estimated_value, tender.currency)}
                  </span>
                </div>
              </div>
            </div>

            {/* Participation Dynamic Action Banner (Part 3C) */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Participation Status
                    </span>
                    {existingBid ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                        Bid In Progress ({existingBid.bid_number})
                      </span>
                    ) : isOpen && !isDeadlinePassed ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-800 border border-blue-200">
                        <Info className="h-3.5 w-3.5 text-blue-600" />
                        Eligible to Participate
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200">
                        Participation Closed
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-600">
                    {existingBid
                      ? `Your organization created draft bid ${existingBid.bid_number}. You can continue editing your proposal workspace.`
                      : !isProfileReady
                      ? "Complete your statutory organization profile to unlock tender participation."
                      : !isOpen
                      ? "This tender is not open for commercial participation."
                      : isDeadlinePassed
                      ? "The submission deadline for this tender has expired."
                      : "Create a draft bid workspace to prepare your technical and commercial response."}
                  </p>
                </div>

                {/* Action CTA Buttons */}
                <div className="shrink-0 w-full sm:w-auto">
                  {existingBid ? (
                    <Link
                      href={`/bidder/bids/${existingBid.id}`}
                      className="inline-flex items-center justify-center gap-2 w-full sm:w-auto rounded-lg bg-emerald-700 px-5 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-emerald-800 transition-colors"
                    >
                      <FileEdit className="h-4 w-4" />
                      Continue Bid Workspace
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  ) : !isProfileReady ? (
                    <Link
                      href="/bidder/organization"
                      className="inline-flex items-center justify-center gap-2 w-full sm:w-auto rounded-lg bg-amber-600 px-5 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-amber-700 transition-colors"
                    >
                      <AlertTriangle className="h-4 w-4" />
                      Complete Profile Setup
                    </Link>
                  ) : canParticipate ? (
                    <button
                      onClick={() => setShowConfirmModal(true)}
                      className="inline-flex items-center justify-center gap-2 w-full sm:w-auto rounded-lg bg-blue-700 px-5 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-blue-800 transition-colors"
                    >
                      <Send className="h-4 w-4" />
                      Start Bid / Participate
                    </button>
                  ) : (
                    <button
                      disabled
                      className="inline-flex items-center justify-center gap-2 w-full sm:w-auto rounded-lg bg-slate-100 px-5 py-2.5 text-xs font-bold text-slate-400 border border-slate-200 cursor-not-allowed"
                    >
                      Participation Unavailable
                    </button>
                  )}
                </div>
              </div>

              {/* Profile Incomplete Warning Banner if applicable */}
              {!isProfileReady && profileCompletion && (
                <div className="mt-4 rounded-lg bg-amber-50 p-3.5 border border-amber-200 flex items-start gap-3">
                  <AlertTriangle className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" />
                  <div className="text-xs text-amber-900 space-y-1">
                    <p className="font-bold">
                      Profile Readiness Check: {profileCompletion.completion_percentage}% Complete
                    </p>
                    <p className="text-amber-800 leading-relaxed">
                      Missing required statutory details:{" "}
                      <strong>{profileCompletion.missing_required_fields.join(", ")}</strong>. Please update these in your organization profile before initiating a bid.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Main Grid Content */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              {/* Left 2 Columns: Overview, Requirements, Buyer Details */}
              <div className="lg:col-span-2 space-y-6">
                {/* Description & Scope */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-3">
                  <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                    Scope of Work & Overview
                  </h2>
                  <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-line bg-slate-50 p-4 rounded-lg border border-slate-200/75 font-sans">
                    {tender.description || "No specific detailed description provided by the procuring entity."}
                  </div>
                </div>

                {/* Eligibility & Compliance Requirements Section */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                    <div className="flex items-center gap-2">
                      <div className="rounded-lg bg-blue-50 p-2 text-blue-700">
                        <ShieldCheck className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-slate-900">
                          Eligibility & Compliance Criteria
                        </h2>
                        <p className="text-xs text-slate-500">
                          Mandatory statutory, financial, technical, and document conditions.
                        </p>
                      </div>
                    </div>
                    <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700 border border-blue-200">
                      {tender.requirements.length} Requirements
                    </span>
                  </div>

                  {tender.requirements.length === 0 ? (
                    <div className="text-center py-6 text-xs text-slate-500">
                      No specific statutory or eligibility requirements configured for this tender.
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {Object.entries(requirementsByCategory).map(([category, reqs]) => (
                        <div key={category} className="space-y-3">
                          <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-600 bg-slate-100 px-3 py-1.5 rounded-md inline-block">
                            {category} Requirements ({reqs.length})
                          </h3>

                          <div className="space-y-3">
                            {reqs.map((req) => (
                              <div
                                key={req.id}
                                className="rounded-lg border border-slate-200 bg-white p-4 shadow-2xs hover:border-slate-300 transition-colors space-y-2"
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <div className="flex items-center gap-2">
                                    <span className="font-mono text-xs font-bold text-blue-800 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                                      {req.code}
                                    </span>
                                    <h4 className="text-sm font-bold text-slate-900">
                                      {req.name}
                                    </h4>
                                  </div>
                                  <span
                                    className={`rounded-full px-2 py-0.5 text-[11px] font-bold border ${
                                      req.is_mandatory
                                        ? "bg-rose-50 text-rose-800 border-rose-200"
                                        : "bg-slate-100 text-slate-700 border-slate-200"
                                    }`}
                                  >
                                    {req.is_mandatory ? "MANDATORY" : "OPTIONAL"}
                                  </span>
                                </div>

                                {req.description && (
                                  <p className="text-xs text-slate-600">
                                    {req.description}
                                  </p>
                                )}

                                {/* Condition Highlight Box */}
                                <div className="rounded-md bg-slate-50 p-2.5 border border-slate-200/80 flex items-center justify-between text-xs">
                                  <span className="text-slate-500 font-medium">
                                    Eligibility Condition:
                                  </span>
                                  <span className="font-semibold text-slate-900 bg-white px-2 py-1 rounded border border-slate-200 shadow-2xs">
                                    {req.condition_text}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Buyer Organization Card */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-3">
                  <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                    Buyer Entity Information
                  </h2>
                  <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                    <div className="rounded-lg bg-slate-50 p-3.5 border border-slate-200/75">
                      <dt className="text-slate-500 font-medium">Procuring Authority</dt>
                      <dd className="font-bold text-slate-900 mt-1 text-sm">
                        {tender.organization.name}
                      </dd>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-3.5 border border-slate-200/75">
                      <dt className="text-slate-500 font-medium">Location</dt>
                      <dd className="font-semibold text-slate-800 mt-1">
                        {tender.organization.city
                          ? `${tender.organization.city}, ${tender.organization.state || "India"}`
                          : "New Delhi, India"}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>

              {/* Right 1 Column Sidebar */}
              <div className="space-y-6">
                {/* Important Timeline Dates */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                      Procurement Timeline
                    </h3>
                    <span
                      className={`rounded px-2 py-0.5 text-[11px] font-bold border ${deadline.colorClass}`}
                    >
                      {deadline.text}
                    </span>
                  </div>

                  <div className="space-y-3 text-xs">
                    <div className="flex items-start gap-2.5">
                      <Calendar className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="text-slate-500 font-medium">Notice Published</span>
                        <p className="font-semibold text-slate-800 mt-0.5">
                          {formatDateTime(tender.publish_date)}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-start gap-2.5">
                      <Clock className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="text-slate-500 font-medium">Submission Window Starts</span>
                        <p className="font-semibold text-slate-800 mt-0.5">
                          {formatDateTime(tender.submission_start_date)}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-start gap-2.5">
                      <Clock className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="text-slate-500 font-medium">Submission Deadline</span>
                        <p className="font-bold text-slate-900 mt-0.5">
                          {formatDateTime(tender.submission_end_date)}
                        </p>
                      </div>
                    </div>

                    {tender.evaluation_start_date && (
                      <div className="flex items-start gap-2.5">
                        <Calendar className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
                        <div>
                          <span className="text-slate-500 font-medium">Evaluation Date</span>
                          <p className="font-semibold text-slate-800 mt-0.5">
                            {formatDateTime(tender.evaluation_start_date)}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Pre-Bidding Readiness Card */}
                <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
                  <div className="flex items-center gap-2">
                    <div className="rounded-lg bg-emerald-50 p-2 text-emerald-700">
                      <CheckCircle2 className="h-4 w-4" />
                    </div>
                    <h3 className="text-sm font-bold text-slate-900">
                      Pre-Bidding Checklist
                    </h3>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">
                    Ensure your legal business name, registered address, GSTIN, PAN, and MSME/Udyam certificates are fully configured in your profile prior to bid packaging.
                  </p>

                  <Link
                    href="/bidder/organization"
                    className="block w-full text-center rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors shadow-xs"
                  >
                    Verify Organization Setup
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Start Bid Confirmation Modal */}
        {showConfirmModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
            <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="rounded-lg bg-blue-50 p-2 text-blue-700">
                    <Send className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">
                      Start Tender Participation?
                    </h3>
                    <p className="text-xs text-slate-500 font-mono">
                      {tender?.tender_number}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => !creatingBid && setShowConfirmModal(false)}
                  disabled={creatingBid}
                  className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors disabled:opacity-50"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="text-xs text-slate-600 space-y-2 bg-slate-50 p-3.5 rounded-lg border border-slate-200/80">
                <p>
                  A <strong>DRAFT bid</strong> will be created for your organization. You will be redirected to your dedicated workspace where you can enter:
                </p>
                <ul className="list-disc list-inside space-y-1 font-medium text-slate-700">
                  <li>Total Quoted Commercial Amount & Currency</li>
                  <li>Technical Response Summary</li>
                  <li>Commercial & Warranty Notes</li>
                </ul>
                <p className="text-slate-500 text-[11px]">
                  * Your bid will remain in DRAFT status until final submission in Part 3E.
                </p>
              </div>

              {creationError && (
                <div className="rounded-lg bg-rose-50 p-3 border border-rose-200 text-xs text-rose-800 flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                  <span>{creationError}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowConfirmModal(false)}
                  disabled={creatingBid}
                  className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleStartBid}
                  disabled={creatingBid}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-700 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-800 transition-colors disabled:opacity-50"
                >
                  {creatingBid ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Creating Bid Workspace...
                    </>
                  ) : (
                    <>
                      <Send className="h-3.5 w-3.5" />
                      Confirm & Start Bid
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
