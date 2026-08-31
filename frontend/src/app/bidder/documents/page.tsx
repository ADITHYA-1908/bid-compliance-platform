"use client";

import React from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  FileText,
  ShieldCheck,
  Lock,
  ArrowRight,
  Layers,
  Sparkles,
  CheckCircle2,
  FileCheck2,
} from "lucide-react";

export default function BidderDocumentsPage() {
  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title="Documents & Compliance Proofs"
      description="Overview of document storage, tender requirement attachments, and secure vault storage."
      breadcrumbs={[
        { label: "Bidder Portal", href: "/bidder" },
        { label: "Documents" },
      ]}
    >
      <div className="space-y-6">
        {/* Document Storage Overview Card */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center rounded-md bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-800 border border-blue-200">
                  Private Storage Active
                </span>
                <span className="inline-flex items-center gap-1 text-xs text-emerald-700 font-medium">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Encrypted & Tenant Isolated
                </span>
              </div>
              <h2 className="text-xl font-bold text-slate-900">
                Bid Compliance Document Center
              </h2>
              <p className="text-xs text-slate-600 max-w-2xl">
                Procurement compliance documents (GST certificates, OEM authorizations, audited balance sheets, PAN cards) are attached directly to their respective tender requirements inside your active Bid Workspaces.
              </p>
            </div>

            <Link
              href="/bidder/bids"
              className="inline-flex items-center gap-1.5 rounded-md bg-blue-700 px-4 py-2.5 text-xs font-semibold text-white hover:bg-blue-800 transition-colors shadow-xs shrink-0"
            >
              <Layers className="h-4 w-4" />
              Open Bid Workspaces
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>

        {/* Security & Lifecycle Architecture Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="rounded-lg bg-blue-50 p-2 text-blue-800 w-fit mb-3">
              <FileCheck2 className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">
              Requirement-Level Mapping
            </h3>
            <p className="text-xs text-slate-600 mt-1">
              Files are explicitly linked to tender requirements (technical, financial, statutory). Replacing a file automatically supersedes prior versions.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="rounded-lg bg-emerald-50 p-2 text-emerald-700 w-fit mb-3">
              <Lock className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">
              Private Signed URLs
            </h3>
            <p className="text-xs text-slate-600 mt-1">
              Documents are stored in a private Supabase Storage bucket. Access is authenticated via expiring HMAC-signed URLs, preventing public exposure.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="rounded-lg bg-purple-50 p-2 text-purple-700 w-fit mb-3">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">
              Post-Submission Lock
            </h3>
            <p className="text-xs text-slate-600 mt-1">
              Once a bid is finalized and moved to <span className="font-semibold text-emerald-700">SUBMITTED</span> status, document modifications and deletions are permanently locked.
            </p>
          </div>
        </div>

        {/* Part 4 Preview Card */}
        <div className="rounded-xl border border-blue-200 bg-linear-to-r from-blue-50/70 to-indigo-50/70 p-5">
          <div className="flex items-start gap-3">
            <Sparkles className="h-5 w-5 text-blue-800 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="text-xs font-bold text-blue-950 uppercase tracking-wider">
                Upcoming in Part 4: Automated OCR & Document Extraction
              </p>
              <p className="text-xs text-slate-700">
                The centralized reusable document vault with optical character recognition (OCR), financial table extraction, and automated statutory certificate verification will be activated in the next development phase.
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
