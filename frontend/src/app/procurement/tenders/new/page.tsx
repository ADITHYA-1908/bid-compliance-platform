"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { TenderForm } from "@/components/tenders/TenderForm";
import { api, TenderCreatePayload, ApiError } from "@/lib/api";
import { SectionCard } from "@/components/common/SectionCard";
import { FileText, CheckCircle2, ListChecks, ShieldCheck, ArrowRight, Layers } from "lucide-react";

export default function CreateTenderPage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const handleCreate = async (payload: TenderCreatePayload) => {
    setIsSubmitting(true);
    setServerError(null);

    try {
      const createdTender = await api.createTender(payload);
      router.push(`/procurement/tenders/${createdTender.id}`);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 409) {
        setServerError(
          `Tender number "${payload.tender_number}" already exists. Please specify a unique GeM reference number.`
        );
      } else {
        setServerError(
          err?.message || "Failed to create tender. Please verify all mandatory inputs and try again."
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Create Procurement Tender"
      description="Define foundational opportunity specifications, estimated contract valuation, and key submission deadlines."
      breadcrumbs={[
        { label: "Procurement Portal", href: "/procurement" },
        { label: "Tenders", href: "/procurement/tenders" },
        { label: "Create Tender" },
      ]}
    >
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Wizard Overview Header */}
        <div className="floating-card rounded-2xl p-5 bg-white border border-slate-200">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold text-xs font-mono">
                01
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 font-heading">Opportunity Specs</h4>
                <p className="text-[11px] text-slate-500">Title, number, & valuation</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-700 border border-slate-200 font-bold text-xs font-mono">
                02
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 font-heading">Dynamic Criteria</h4>
                <p className="text-[11px] text-slate-500">Eligibility & documents</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-700 border border-slate-200 font-bold text-xs font-mono">
                03
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 font-heading">Publish Controls</h4>
                <p className="text-[11px] text-slate-500">Draft → GeM publication</p>
              </div>
            </div>
          </div>
        </div>

        {/* Core Creation Form */}
        <TenderForm
          mode="create"
          isSubmitting={isSubmitting}
          serverError={serverError}
          onSubmit={handleCreate as any}
          cancelHref="/procurement/tenders"
        />
      </div>
    </DashboardLayout>
  );
}
