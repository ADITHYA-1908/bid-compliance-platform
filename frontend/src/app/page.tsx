"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { getDashboardRoute } from "@/lib/roles";
import {
  ShieldCheck,
  FileCheck2,
  Lock,
  ArrowRight,
  Building2,
  CheckCircle2,
  Scale,
  ShieldAlert,
  Activity,
  Landmark,
  FileText,
  Search,
  Check,
  Cpu,
  History,
} from "lucide-react";

export default function HomePage() {
  const { user, loading } = useAuth();
  const portalRoute = user ? getDashboardRoute(user.role) : "/login";

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 flex flex-col font-body">
      {/* Top Government Portal Bar */}
      <div className="border-b border-slate-200 bg-[#0F1E36] text-white py-2 px-4 sm:px-6 lg:px-8 text-xs">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2 font-medium">
            <Landmark className="h-3.5 w-3.5 text-amber-400" />
            <span>Government of India • GeM Public Procurement Compliance Verification System</span>
          </div>
          <div className="hidden sm:flex items-center gap-4 text-slate-300">
            <span>Security Standard: GFR 2017 Compliant</span>
            <span>•</span>
            <span className="text-emerald-400 font-semibold">Production Ready Demo</span>
          </div>
        </div>
      </div>

      {/* Main Navigation Header */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#0F1E36] text-white shadow-2xs">
              <Landmark className="h-5 w-5 text-amber-400" />
            </div>
            <div>
              <span className="font-heading text-lg font-bold tracking-tight text-[#0F1E36]">
                BidVerify <span className="text-emerald-700 font-extrabold">AI</span>
              </span>
              <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                AI-Powered Bid Compliance Verification
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {loading ? (
              <div className="h-9 w-24 bg-slate-100 rounded-lg animate-pulse" />
            ) : user ? (
              <Link
                href={portalRoute}
                className="btn-primary-navy inline-flex items-center gap-2 rounded-lg px-4 py-2 text-xs shadow-xs"
              >
                <span>Go to Dashboard</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/login"
                  className="btn-secondary-outline rounded-lg px-4 py-2 text-xs"
                >
                  Sign In
                </Link>
                <Link
                  href="/signup"
                  className="btn-primary-navy rounded-lg px-4 py-2 text-xs shadow-xs"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="border-b border-slate-200 bg-white py-12 sm:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700 mb-4">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-700" />
              <span>Deterministic Compliance & Document AI Architecture</span>
            </div>

            <h1 className="font-heading text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-slate-900 leading-tight">
              Enterprise Procurement Compliance & Claim Verification
            </h1>

            <p className="mt-4 text-sm sm:text-base text-slate-600 leading-relaxed">
              Automated statutory credential extraction, cross-document entity consistency matrix, deterministic rule evaluation, and human-in-the-loop decision cockpit for public procurement under GeM.
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Link
                href="/login/procurement"
                className="btn-primary-navy inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-xs font-bold shadow-xs"
              >
                <span>Procurement Officer Portal</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>

              <Link
                href="/login/bidder"
                className="btn-secondary-outline inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-xs font-bold"
              >
                <span>Bidder (Vendor) Portal</span>
              </Link>

              <Link
                href="/procurement/validation"
                className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-700 hover:text-slate-900 hover:underline px-3 py-2"
              >
                <Activity className="h-3.5 w-3.5 text-emerald-700" />
                <span>View Empirical Benchmark Suite</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Role Access Portals Section */}
      <section className="py-12 bg-[#F8FAFC] border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-8">
            <h2 className="font-heading text-xl sm:text-2xl font-bold text-slate-900">
              Select Role Portal
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Role-Based Access Control (RBAC) with tailored workspaces and audit logging.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Bidder Card */}
            <div className="card-formal bg-white p-6 border border-slate-200 flex flex-col justify-between">
              <div>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700 border border-blue-200 mb-4">
                  <Building2 className="h-5 w-5" />
                </div>
                <h3 className="font-heading text-base font-bold text-slate-900">
                  Bidder Portal (Vendor)
                </h3>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                  Discover published GeM opportunities, upload official PDF statutory documents (PAN, GSTIN, Udyam), review auto-extracted details, and track proposal readiness.
                </p>

                <ul className="mt-4 space-y-1.5 text-xs text-slate-600">
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span>PDF-First Statutory Ingestion</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span>Real-time Readiness Score</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span>Buyer Clarification Resolution</span>
                  </li>
                </ul>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100">
                <Link
                  href="/login/bidder"
                  className="btn-primary-navy w-full flex items-center justify-center gap-2 rounded-lg py-2 text-xs"
                >
                  <span>Sign In as Bidder</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </div>

            {/* Procurement Officer Card */}
            <div className="card-formal bg-white p-6 border border-slate-200 flex flex-col justify-between">
              <div>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 mb-4">
                  <FileCheck2 className="h-5 w-5" />
                </div>
                <h3 className="font-heading text-base font-bold text-slate-900">
                  Procurement Officer Portal
                </h3>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                  Create and publish tenders with dynamic criteria, inspect the Priority Review Queue, examine Explain Why evidence panels, and record formal qualification decisions.
                </p>

                <ul className="mt-4 space-y-1.5 text-xs text-slate-600">
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span>Priority Review Queue</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span>Explain Why Evidence Cockpit</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span>Human Final Determination</span>
                  </li>
                </ul>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100">
                <Link
                  href="/login/procurement"
                  className="btn-primary-navy w-full flex items-center justify-center gap-2 rounded-lg py-2 text-xs"
                >
                  <span>Sign In as Procurement Officer</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </div>

            {/* Admin Card */}
            <div className="card-formal bg-white p-6 border border-slate-200 flex flex-col justify-between">
              <div>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-50 text-purple-700 border border-purple-200 mb-4">
                  <Lock className="h-5 w-5" />
                </div>
                <h3 className="font-heading text-base font-bold text-slate-900">
                  Admin Oversight Portal
                </h3>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                  Platform governance, organization registry oversight, user role provisioning, empirical validation benchmark analytics, and immutable audit log exploration.
                </p>

                <ul className="mt-4 space-y-1.5 text-xs text-slate-600">
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span>Organization & User Governance</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span>Empirical Benchmark Cockpit</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span>Immutable Platform Audit Log</span>
                  </li>
                </ul>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100">
                <Link
                  href="/login/admin"
                  className="btn-primary-navy w-full flex items-center justify-center gap-2 rounded-lg py-2 text-xs"
                >
                  <span>Sign In as Admin</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Core Architectural Pillars */}
      <section className="py-12 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-8">
            <h2 className="font-heading text-xl sm:text-2xl font-bold text-slate-900">
              Core Technical Capabilities
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Engineered for deterministic precision, legal traceability, and enterprise compliance.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <Cpu className="h-5 w-5 text-[#0F1E36] mb-2" />
              <h4 className="text-sm font-bold text-slate-900">Multimodal Document AI</h4>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                PyMuPDF for digital PDFs and OpenCV + PaddleOCR for scanned statutory certificates with confidence scoring.
              </p>
            </div>

            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <Scale className="h-5 w-5 text-emerald-700 mb-2" />
              <h4 className="text-sm font-bold text-slate-900">Deterministic Compliance</h4>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Rule-based eligibility verification engine (Turnover, GST, Experience) with transparent PASS / FAIL / REVIEW outcomes.
              </p>
            </div>

            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <ShieldAlert className="h-5 w-5 text-amber-700 mb-2" />
              <h4 className="text-sm font-bold text-slate-900">Cross-Document Consistency</h4>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Automated similarity matrix comparing PAN, GSTIN, Udyam, and MCA legal entity names to prevent discrepancy fraud.
              </p>
            </div>

            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <History className="h-5 w-5 text-purple-700 mb-2" />
              <h4 className="text-sm font-bold text-slate-900">Tamper-Evident Audit Trail</h4>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Complete chronological event logging of all officer determinations, rule revisions, and bidder uploads.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 py-8 px-4 sm:px-6 lg:px-8 text-xs mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-white">
            <Landmark className="h-4 w-4 text-amber-400" />
            <span className="font-bold">BidVerify AI</span>
            <span className="text-slate-500">•</span>
            <span className="text-slate-400 text-[11px]">Government Procurement Compliance Platform</span>
          </div>

          <div className="flex items-center gap-4 text-slate-400">
            <Link href="/procurement/validation" className="hover:text-white transition-colors">
              Empirical Validation
            </Link>
            <Link href="/procurement/audit" className="hover:text-white transition-colors">
              Audit Log
            </Link>
            <Link href="/login" className="hover:text-white transition-colors">
              Portal Login
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
