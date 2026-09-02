"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { TenderStatusBadge } from "@/components/tenders/TenderStatusBadge";
import { RequirementList } from "@/components/tenders/RequirementList";
import { LifecycleTimeline } from "@/components/tenders/LifecycleTimeline";
import {
  LifecycleActionModal,
  LifecycleAction,
} from "@/components/tenders/LifecycleActionModal";
import {
  api,
  Tender,
  TenderRequirement,
  TenderRequirementCreatePayload,
  TenderRequirementUpdatePayload,
} from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/formatters";
import {
  ArrowLeft,
  Edit2,
  Archive,
  Building2,
  Calendar,
  Clock,
  AlertCircle,
  CheckCircle2,
  Send,
  Unlock,
  Lock,
  SearchCheck,
  Trophy,
} from "lucide-react";

export default function TenderDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const tenderId = params.id as string;

  const [tender, setTender] = useState<Tender | null>(null);
  const [requirements, setRequirements] = useState<TenderRequirement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Success / notification feedback alert
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Lifecycle transition modal state
  const [activeTransition, setActiveTransition] = useState<LifecycleAction | null>(null);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [transitionError, setTransitionError] = useState<string | null>(null);

  const loadTenderAndRequirements = useCallback(async () => {
    if (!tenderId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [tenderData, reqsData] = await Promise.all([
        api.getTender(tenderId),
        api.getTenderRequirements(tenderId),
      ]);
      setTender(tenderData);
      setRequirements(reqsData);
    } catch (err: any) {
      setError(
        err?.status === 404
          ? "Tender not found or you do not have permission to view it."
          : err?.message || "Failed to load tender details."
      );
    } finally {
      setIsLoading(false);
    }
  }, [tenderId]);

  useEffect(() => {
    loadTenderAndRequirements();
  }, [loadTenderAndRequirements]);

  const handleOpenTransitionModal = (target: LifecycleAction) => {
    setTransitionError(null);
    setActiveTransition(target);
  };

  const handleExecuteTransition = async (
    targetStatus: LifecycleAction,
    remarks?: string
  ) => {
    if (!tender) return;
    setIsTransitioning(true);
    setTransitionError(null);

    try {
      const updatedTender = await api.transitionTenderStatus(
        tender.id,
        targetStatus,
        remarks
      );
      setTender(updatedTender);
      setActiveTransition(null);

      let successMsg = `Tender ${tender.tender_number} successfully transitioned to ${targetStatus}.`;
      if (targetStatus === "PUBLISHED") {
        successMsg = "Tender published successfully. It is now ready to open for bidding.";
      } else if (targetStatus === "OPEN") {
        successMsg = "Tender opened successfully. Bidders can now submit compliance bids.";
      } else if (targetStatus === "CLOSED") {
        successMsg = "Tender closed successfully. Submissions are now halted.";
      } else if (targetStatus === "UNDER_EVALUATION") {
        successMsg = "Compliance evaluation initiated successfully.";
      } else if (targetStatus === "AWARDED") {
        successMsg = "Tender awarded successfully.";
      } else if (targetStatus === "ARCHIVED") {
        successMsg = "Tender archived successfully and is now read-only.";
      }

      setFeedback({ type: "success", message: successMsg });
      await loadTenderAndRequirements();
    } catch (err: any) {
      setTransitionError(err?.message || "Failed to complete status transition.");
    } finally {
      setIsTransitioning(false);
    }
  };

  const handleAddRequirement = async (payload: TenderRequirementCreatePayload) => {
    const newReq = await api.createTenderRequirement(tenderId, payload);
    setRequirements((prev) => [...prev, newReq]);
    setFeedback({
      type: "success",
      message: `Requirement rule "${newReq.code}" added successfully.`,
    });
  };

  const handleUpdateRequirement = async (
    requirementId: string,
    payload: TenderRequirementUpdatePayload
  ) => {
    const updatedReq = await api.updateTenderRequirement(
      tenderId,
      requirementId,
      payload
    );
    setRequirements((prev) =>
      prev.map((r) => (r.id === requirementId ? updatedReq : r))
    );
    setFeedback({
      type: "success",
      message: `Requirement rule "${updatedReq.code}" updated successfully.`,
    });
  };

  const handleDisableRequirement = async (requirementId: string) => {
    const disabledReq = await api.disableTenderRequirement(tenderId, requirementId);
    setRequirements((prev) => prev.filter((r) => r.id !== requirementId));
    setFeedback({
      type: "success",
      message: `Requirement rule "${disabledReq.code}" disabled.`,
    });
  };

  if (isLoading) {
    return (
      <DashboardLayout
        allowedRoles={["PROCUREMENT_OFFICER"]}
        title="Tender Details"
        description="Inspecting procurement opportunity specifications."
        breadcrumbs={[
          { label: "Procurement Portal", href: "/procurement" },
          { label: "Tenders", href: "/procurement/tenders" },
          { label: "Loading..." },
        ]}
      >
        <div className="rounded-xl border border-slate-200 bg-white p-8 animate-pulse space-y-6">
          <div className="h-6 bg-slate-200 rounded w-1/3"></div>
          <div className="h-4 bg-slate-100 rounded w-1/2"></div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4">
            <div className="h-24 bg-slate-100 rounded"></div>
            <div className="h-24 bg-slate-100 rounded"></div>
            <div className="h-24 bg-slate-100 rounded"></div>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (error || !tender) {
    return (
      <DashboardLayout
        allowedRoles={["PROCUREMENT_OFFICER"]}
        title="Tender Details"
        description="Inspecting procurement opportunity specifications."
        breadcrumbs={[
          { label: "Procurement Portal", href: "/procurement" },
          { label: "Tenders", href: "/procurement/tenders" },
          { label: "Error" },
        ]}
      >
        <div className="rounded-xl border border-red-200 bg-white p-12 text-center shadow-xs">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600 mb-3">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">Tender Unavailable</h3>
          <p className="text-xs text-slate-600 mt-1 max-w-md mx-auto">
            {error || "Tender could not be loaded."}
          </p>
          <div className="mt-5">
            <Link
              href="/procurement/tenders"
              className="inline-flex items-center gap-1.5 rounded-lg bg-purple-900 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-purple-800 transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to Tenders
            </Link>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  const isDraft = tender.status === "DRAFT" && tender.is_active;
  const isArchived = !tender.is_active || tender.status === "ARCHIVED";

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER"]}
      title={tender.title}
      description={`Tender Reference: ${tender.tender_number}`}
      breadcrumbs={[
        { label: "Procurement Portal", href: "/procurement" },
        { label: "Tenders", href: "/procurement/tenders" },
        { label: tender.tender_number },
      ]}
      action={
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href="/procurement/tenders"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back
          </Link>

          <Link
            href={`/procurement/tenders/${tender.id}/evaluation`}
            className="inline-flex items-center gap-1.5 rounded-lg bg-purple-900 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-purple-800 transition-colors"
          >
            <SearchCheck className="h-3.5 w-3.5" />
            Bid Evaluation Matrix
          </Link>

          {/* DRAFT Actions */}
          {tender.status === "DRAFT" && !isArchived && (
            <>
              <Link
                href={`/procurement/tenders/${tender.id}/edit`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-purple-300 bg-purple-50 px-3.5 py-2 text-xs font-semibold text-purple-900 shadow-2xs hover:bg-purple-100 transition-colors"
              >
                <Edit2 className="h-3.5 w-3.5" />
                Edit Details
              </Link>

              <button
                type="button"
                onClick={() => handleOpenTransitionModal("PUBLISHED")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-700 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-800 transition-colors cursor-pointer"
              >
                <Send className="h-3.5 w-3.5" />
                Publish Tender
              </button>

              <button
                type="button"
                onClick={() => handleOpenTransitionModal("ARCHIVED")}
                className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 shadow-2xs hover:bg-rose-100 transition-colors cursor-pointer"
              >
                <Archive className="h-3.5 w-3.5" />
                Archive
              </button>
            </>
          )}

          {/* PUBLISHED Actions */}
          {tender.status === "PUBLISHED" && !isArchived && (
            <>
              <button
                type="button"
                onClick={() => handleOpenTransitionModal("OPEN")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-emerald-800 transition-colors cursor-pointer"
              >
                <Unlock className="h-3.5 w-3.5" />
                Open for Bidding
              </button>

              <button
                type="button"
                onClick={() => handleOpenTransitionModal("ARCHIVED")}
                className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 shadow-2xs hover:bg-rose-100 transition-colors cursor-pointer"
              >
                <Archive className="h-3.5 w-3.5" />
                Archive
              </button>
            </>
          )}

          {/* OPEN Actions */}
          {tender.status === "OPEN" && !isArchived && (
            <button
              type="button"
              onClick={() => handleOpenTransitionModal("CLOSED")}
              className="inline-flex items-center gap-1.5 rounded-lg bg-amber-700 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-amber-800 transition-colors cursor-pointer"
            >
              <Lock className="h-3.5 w-3.5" />
              Close Bidding
            </button>
          )}

          {/* CLOSED Actions */}
          {tender.status === "CLOSED" && !isArchived && (
            <button
              type="button"
              onClick={() => handleOpenTransitionModal("UNDER_EVALUATION")}
              className="inline-flex items-center gap-1.5 rounded-lg bg-purple-900 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-purple-800 transition-colors cursor-pointer"
            >
              <SearchCheck className="h-3.5 w-3.5" />
              Start Evaluation
            </button>
          )}

          {/* UNDER_EVALUATION Actions */}
          {tender.status === "UNDER_EVALUATION" && !isArchived && (
            <>
              <button
                type="button"
                onClick={() => handleOpenTransitionModal("AWARDED")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-indigo-800 transition-colors cursor-pointer"
              >
                <Trophy className="h-3.5 w-3.5" />
                Award Tender
              </button>

              <button
                type="button"
                onClick={() => handleOpenTransitionModal("ARCHIVED")}
                className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 shadow-2xs hover:bg-rose-100 transition-colors cursor-pointer"
              >
                <Archive className="h-3.5 w-3.5" />
                Archive
              </button>
            </>
          )}

          {/* AWARDED Actions */}
          {tender.status === "AWARDED" && !isArchived && (
            <button
              type="button"
              onClick={() => handleOpenTransitionModal("ARCHIVED")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 shadow-2xs hover:bg-rose-100 transition-colors cursor-pointer"
            >
              <Archive className="h-3.5 w-3.5" />
              Archive
            </button>
          )}
        </div>
      }
    >
      <div className="space-y-6">
        {/* Feedback Alert */}
        {feedback && (
          <div
            className={`rounded-xl border p-4 text-xs font-medium flex items-center justify-between ${
              feedback.type === "success"
                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                : "bg-red-50 text-red-800 border-red-200"
            }`}
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
              <span>{feedback.message}</span>
            </div>
            <button
              onClick={() => setFeedback(null)}
              className="text-slate-500 hover:text-slate-700 font-bold ml-4 cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}

        {/* Status & Valuation Bar */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <span className="font-mono text-sm font-bold text-slate-900 bg-slate-100 px-2.5 py-0.5 rounded-md border border-slate-200">
                {tender.tender_number}
              </span>
              <TenderStatusBadge status={tender.status} />
            </div>
            <h2 className="text-lg font-bold text-slate-900">{tender.title}</h2>
          </div>

          <div className="text-left sm:text-right border-t sm:border-t-0 pt-3 sm:pt-0 border-slate-100">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Estimated Valuation
            </span>
            <p className="text-xl font-bold font-mono text-purple-950">
              {formatCurrency(tender.estimated_value, tender.currency)}
            </p>
          </div>
        </div>

        {/* Lifecycle Stepper Timeline (Part 2E) */}
        <LifecycleTimeline
          status={tender.status}
          isActive={tender.is_active}
          publishedAt={tender.published_at}
          openedAt={tender.opened_at}
          closedAt={tender.closed_at}
          evaluationStartedAt={tender.evaluation_started_at}
          awardedAt={tender.awarded_at}
          archivedAt={tender.archived_at}
          createdAt={tender.created_at}
        />

        {/* 2-Column Main Info Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left 2 Cols: Details, Scope & Requirements */}
          <div className="lg:col-span-2 space-y-6">
            {/* Overview Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                <Building2 className="h-4 w-4 text-purple-900" />
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Procurement Information
                </h3>
              </div>

              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 text-xs">
                <div>
                  <dt className="text-slate-500 font-medium">Department / Ministry</dt>
                  <dd className="font-semibold text-slate-900 mt-0.5">
                    {tender.department || "—"}
                  </dd>
                </div>

                <div>
                  <dt className="text-slate-500 font-medium">Category</dt>
                  <dd className="font-semibold text-slate-900 mt-0.5">
                    {tender.category || "—"}
                  </dd>
                </div>

                <div>
                  <dt className="text-slate-500 font-medium">Procurement Type</dt>
                  <dd className="font-semibold text-slate-900 mt-0.5">
                    <span className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-700">
                      {tender.procurement_type || "GOODS"}
                    </span>
                  </dd>
                </div>

                <div>
                  <dt className="text-slate-500 font-medium">Designated Currency</dt>
                  <dd className="font-mono font-semibold text-slate-900 mt-0.5">
                    {tender.currency}
                  </dd>
                </div>
              </dl>

              {tender.description && (
                <div className="border-t border-slate-100 pt-4">
                  <span className="text-xs font-semibold text-slate-700 block mb-1">
                    Scope of Work & Technical Description
                  </span>
                  <p className="text-xs text-slate-600 whitespace-pre-line leading-relaxed bg-slate-50 p-3.5 rounded-lg border border-slate-200/75">
                    {tender.description}
                  </p>
                </div>
              )}
            </div>

            {/* Dynamic Requirements Section (Part 2D / 2E) */}
            <RequirementList
              tenderId={tender.id}
              isDraft={isDraft}
              status={tender.status}
              requirements={requirements}
              onAddRequirement={handleAddRequirement}
              onUpdateRequirement={handleUpdateRequirement}
              onDisableRequirement={handleDisableRequirement}
            />
          </div>

          {/* Right 1 Col: Schedule & Ownership Cards */}
          <div className="space-y-6">
            {/* Schedule Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                <Calendar className="h-4 w-4 text-purple-900" />
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Schedule & Milestones
                </h3>
              </div>

              <div className="space-y-3.5 text-xs">
                <div>
                  <span className="text-[11px] text-slate-500 block">Publication Date</span>
                  <span className="font-semibold text-slate-900 font-mono mt-0.5 block">
                    {formatDateTime(tender.publish_date)}
                  </span>
                </div>

                <div>
                  <span className="text-[11px] text-slate-500 block">Bid Submission Starts</span>
                  <span className="font-semibold text-slate-900 font-mono mt-0.5 block">
                    {formatDateTime(tender.submission_start_date)}
                  </span>
                </div>

                <div className="rounded-lg bg-purple-50/60 p-2.5 border border-purple-100">
                  <span className="text-[11px] text-purple-900 font-bold block">
                    Submission Deadline (End Date)
                  </span>
                  <span className="font-semibold text-purple-950 font-mono mt-0.5 block">
                    {formatDateTime(tender.submission_end_date)}
                  </span>
                </div>

                <div>
                  <span className="text-[11px] text-slate-500 block">
                    Evaluation & Verification Starts
                  </span>
                  <span className="font-semibold text-slate-900 font-mono mt-0.5 block">
                    {formatDateTime(tender.evaluation_start_date)}
                  </span>
                </div>
              </div>
            </div>

            {/* Audit & Ownership Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-3 text-xs">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                <Clock className="h-4 w-4 text-slate-500" />
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Audit & Security Record
                </h3>
              </div>

              <div className="space-y-2 text-[11px] text-slate-600">
                <div>
                  <span className="text-slate-400 block">Internal Record ID:</span>
                  <span className="font-mono text-slate-700 truncate block">{tender.id}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Owning Organization ID:</span>
                  <span className="font-mono text-slate-700 truncate block">
                    {tender.organization_id}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Created Timestamp:</span>
                  <span className="font-mono text-slate-700 block">
                    {formatDateTime(tender.created_at)}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Last Modified:</span>
                  <span className="font-mono text-slate-700 block">
                    {formatDateTime(tender.updated_at)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Reusable Lifecycle Transition Confirmation Dialog */}
      <LifecycleActionModal
        isOpen={activeTransition !== null}
        targetStatus={activeTransition}
        tenderNumber={tender.tender_number}
        tenderTitle={tender.title}
        isSubmitting={isTransitioning}
        serverError={transitionError}
        onConfirm={handleExecuteTransition}
        onClose={() => {
          if (!isTransitioning) {
            setActiveTransition(null);
            setTransitionError(null);
          }
        }}
      />
    </DashboardLayout>
  );
}
