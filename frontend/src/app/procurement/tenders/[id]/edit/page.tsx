"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { TenderForm } from "@/components/tenders/TenderForm";
import { api, Tender, TenderUpdatePayload } from "@/lib/api";
import { AlertCircle, ArrowLeft } from "lucide-react";

export default function EditTenderPage() {
  const params = useParams();
  const router = useRouter();
  const tenderId = params.id as string;

  const [tender, setTender] = useState<Tender | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadTender = useCallback(async () => {
    if (!tenderId) return;
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await api.getTender(tenderId);
      setTender(data);
    } catch (err: any) {
      setLoadError(
        err?.status === 404
          ? "Tender not found or you do not have permission to edit it."
          : err?.message || "Failed to load tender for editing."
      );
    } finally {
      setIsLoading(false);
    }
  }, [tenderId]);

  useEffect(() => {
    loadTender();
  }, [loadTender]);

  const handleUpdate = async (payload: TenderUpdatePayload) => {
    if (!tenderId) return;
    setIsSubmitting(true);
    setServerError(null);

    try {
      await api.updateTender(tenderId, payload);
      router.push(`/procurement/tenders/${tenderId}`);
    } catch (err: any) {
      setServerError(err?.message || "Failed to save tender changes. Please check your inputs.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <DashboardLayout
        allowedRoles={["PROCUREMENT_OFFICER"]}
        title="Edit Tender"
        description="Modify procurement specifications."
        breadcrumbs={[
          { label: "Procurement Portal", href: "/procurement" },
          { label: "Tenders", href: "/procurement/tenders" },
          { label: "Edit Tender" },
        ]}
      >
        <div className="rounded-xl border border-slate-200 bg-white p-8 animate-pulse space-y-4 max-w-4xl mx-auto">
          <div className="h-6 bg-slate-200 rounded w-1/3"></div>
          <div className="h-10 bg-slate-100 rounded"></div>
          <div className="h-10 bg-slate-100 rounded"></div>
          <div className="h-32 bg-slate-100 rounded"></div>
        </div>
      </DashboardLayout>
    );
  }

  if (loadError || !tender) {
    return (
      <DashboardLayout
        allowedRoles={["PROCUREMENT_OFFICER"]}
        title="Edit Tender"
        description="Modify procurement specifications."
        breadcrumbs={[
          { label: "Procurement Portal", href: "/procurement" },
          { label: "Tenders", href: "/procurement/tenders" },
          { label: "Error" },
        ]}
      >
        <div className="rounded-xl border border-red-200 bg-white p-12 text-center shadow-xs max-w-lg mx-auto">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600 mb-3">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">Unable to Edit Tender</h3>
          <p className="text-xs text-slate-600 mt-1">{loadError || "Tender could not be loaded."}</p>
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

  // If tender is not in DRAFT or is archived, prevent editing
  if (tender.status !== "DRAFT" || !tender.is_active) {
    return (
      <DashboardLayout
        allowedRoles={["PROCUREMENT_OFFICER"]}
        title={`Edit ${tender.tender_number}`}
        description="Modify procurement specifications."
        breadcrumbs={[
          { label: "Procurement Portal", href: "/procurement" },
          { label: "Tenders", href: "/procurement/tenders" },
          { label: tender.tender_number, href: `/procurement/tenders/${tender.id}` },
          { label: "Edit" },
        ]}
      >
        <div className="rounded-xl border border-amber-200 bg-amber-50/75 p-8 text-center shadow-xs max-w-lg mx-auto">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 text-amber-700 mb-3">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-bold text-amber-900">Tender is not editable</h3>
          <p className="text-xs text-amber-800 mt-1">
            Only active tenders in <strong>DRAFT</strong> status can be updated. Current status:{" "}
            <span className="font-bold">{tender.status}</span>.
          </p>
          <div className="mt-5">
            <Link
              href={`/procurement/tenders/${tender.id}`}
              className="inline-flex items-center gap-1.5 rounded-lg bg-purple-900 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-purple-800 transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Return to Tender Details
            </Link>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER"]}
      title={`Edit ${tender.tender_number}`}
      description="Update basic procurement specifications and deadlines."
      breadcrumbs={[
        { label: "Procurement Portal", href: "/procurement" },
        { label: "Tenders", href: "/procurement/tenders" },
        { label: tender.tender_number, href: `/procurement/tenders/${tender.id}` },
        { label: "Edit" },
      ]}
    >
      <div className="max-w-4xl mx-auto">
        <TenderForm
          mode="edit"
          initialData={tender}
          isSubmitting={isSubmitting}
          serverError={serverError}
          onSubmit={handleUpdate as any}
          cancelHref={`/procurement/tenders/${tender.id}`}
        />
      </div>
    </DashboardLayout>
  );
}
