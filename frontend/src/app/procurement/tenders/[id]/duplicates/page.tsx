"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { DuplicateMatchesList } from "@/components/procurement/DuplicateMatchesList";
import { ChevronLeft, FileText, ArrowLeft, ShieldAlert } from "lucide-react";
import { getTenderBidEvaluations } from "@/lib/api/procurement_dashboard";
import { TenderBidEvaluationsListResponse } from "@/types/procurement_dashboard";

export default function TenderDuplicateDetectionPage() {
  const params = useParams();
  const tenderId = params?.id as string;
  const [tenderData, setTenderData] = useState<TenderBidEvaluationsListResponse | null>(null);

  useEffect(() => {
    if (tenderId) {
      getTenderBidEvaluations(tenderId)
        .then(setTenderData)
        .catch(() => {});
    }
  }, [tenderId]);

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Duplicate & Reuse Document Alerts"
      description="Multi-signal cross-bidder document comparison, anomaly detection, and human review decision workspace."
      breadcrumbs={[
        { label: "Procurement Portal", href: "/procurement" },
        { label: "Tenders", href: "/procurement/tenders" },
        { label: tenderData?.tender_number || "Tender", href: `/procurement/tenders/${tenderId}` },
        { label: "Evaluation", href: `/procurement/tenders/${tenderId}/evaluation` },
        { label: "Duplicate Alerts" },
      ]}
    >
      <div className="space-y-6 max-w-7xl mx-auto px-4 py-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Link
              href="/procurement/tenders"
              className="hover:text-slate-200 transition-colors"
            >
              Tenders
            </Link>
            <span>/</span>
            <Link
              href={`/procurement/tenders/${tenderId}`}
              className="hover:text-slate-200 transition-colors"
            >
              {tenderData?.tender_number || "Tender Details"}
            </Link>
            <span>/</span>
            <Link
              href={`/procurement/tenders/${tenderId}/evaluation`}
              className="hover:text-slate-200 transition-colors"
            >
              Evaluation
            </Link>
            <span>/</span>
            <span className="text-slate-200 font-semibold">Duplicate Alerts</span>
          </div>

          <Link
            href={`/procurement/tenders/${tenderId}/evaluation`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Evaluation Workspace
          </Link>
        </div>

        {/* Duplicate Matches Workspace Component */}
        <DuplicateMatchesList
          tenderId={tenderId}
          tenderNumber={tenderData?.tender_number}
        />
      </div>
    </DashboardLayout>
  );
}
