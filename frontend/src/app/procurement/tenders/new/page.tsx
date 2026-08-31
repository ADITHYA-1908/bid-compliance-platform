"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { TenderForm } from "@/components/tenders/TenderForm";
import { api, TenderCreatePayload, ApiError } from "@/lib/api";

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
        setServerError(`Tender number "${payload.tender_number}" already exists. Please choose a unique tender number.`);
      } else {
        setServerError(err?.message || "Failed to create tender. Please verify your inputs and try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER"]}
      title="Create Procurement Tender"
      description="Enter foundational opportunity specifications, estimated contract valuation, and key submission deadlines."
      breadcrumbs={[
        { label: "Procurement Portal", href: "/procurement" },
        { label: "Tenders", href: "/procurement/tenders" },
        { label: "Create Tender" },
      ]}
    >
      <div className="max-w-4xl mx-auto">
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
