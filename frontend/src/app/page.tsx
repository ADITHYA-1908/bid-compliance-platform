"use client";

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
  Sparkles,
  Scale,
} from "lucide-react";

export default function HomePage() {
  const { user, loading } = useAuth();
  const portalRoute = user ? getDashboardRoute(user.role) : "/login";

  return (
    <div className="min-h-screen flex flex-col bg-slate-900 text-slate-100 selection:bg-purple-600 selection:text-white">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-tr from-purple-700 to-indigo-600 shadow-md">
              <ShieldCheck className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
                BidVerify <span className="text-purple-400 font-semibold">AI</span>
              </span>
              <span className="hidden sm:block text-[10px] text-slate-400 font-medium tracking-wide uppercase">
                GeM Procurement Verification
              </span>
            </div>
          </div>

          <nav className="flex items-center gap-3">
            {loading ? (
              <span className="text-xs text-slate-400">Loading...</span>
            ) : user ? (
              <Link
                href={portalRoute}
                className="inline-flex items-center gap-1.5 rounded-lg bg-purple-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-purple-500 transition-colors"
              >
                Go to {user.role === "PROCUREMENT_OFFICER" ? "Procurement" : user.role === "BIDDER" ? "Bidder" : "Admin"} Portal
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="rounded-lg px-3.5 py-2 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="/signup"
                  className="inline-flex items-center justify-center rounded-lg bg-purple-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-purple-500 transition-colors"
                >
                  Register as Bidder
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1">
        <section className="relative overflow-hidden pt-16 pb-20 sm:pt-24 sm:pb-28">
          {/* Subtle Ambient Gradient Glow */}
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-purple-900/20 blur-[120px] rounded-full pointer-events-none -z-0" />

          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10 space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-purple-500/30 bg-purple-950/50 px-3.5 py-1.5 text-xs font-medium text-purple-300 shadow-sm backdrop-blur-xs">
              <Sparkles className="h-3.5 w-3.5 text-purple-400" />
              <span>Government e-Marketplace (GeM) Compliance Platform</span>
            </div>

            <div className="space-y-4">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight">
                AI-Powered Integrated Bid Compliance Verification
              </h1>
              <p className="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed">
                Streamline procurement eligibility, automate statutory compliance audits, and accelerate tender evaluations with intelligent rule verification.
              </p>
            </div>

            {/* Public Authentication Entry Actions */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              {loading ? (
                <div className="h-10 w-48 bg-slate-800 rounded-lg animate-pulse" />
              ) : user ? (
                <Link
                  href={portalRoute}
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-md hover:from-purple-500 hover:to-indigo-500 transition-all"
                >
                  <span>Open {user.role} Portal</span>
                  <ArrowRight className="h-4 w-4" />
                </Link>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-md hover:from-purple-500 hover:to-indigo-500 transition-all cursor-pointer"
                  >
                    <span>Sign In</span>
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                  <Link
                    href="/signup"
                    className="w-full sm:w-auto inline-flex items-center justify-center rounded-lg border border-slate-700 bg-slate-800/80 px-6 py-3 text-sm font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-colors cursor-pointer"
                  >
                    Register as Bidder
                  </Link>
                </>
              )}
            </div>

            {/* Platform Feature Badges */}
            <div className="pt-6 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>Automated Statutory Verification</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>Dynamic Eligibility Criteria</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>Tamper-Proof Audit Trails</span>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Cards Grid */}
        <section className="border-t border-slate-800 bg-slate-950/60 py-16">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Card 1 */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-3 hover:border-purple-500/40 transition-colors">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-950 text-purple-400 border border-purple-800/50">
                  <FileCheck2 className="h-5 w-5" />
                </div>
                <h3 className="text-base font-bold text-white">Dynamic Eligibility Rules</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Configurable criteria for turnover, local content, statutory documentation, and technical thresholds stored dynamically for each procurement tender.
                </p>
              </div>

              {/* Card 2 */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-3 hover:border-indigo-500/40 transition-colors">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-950 text-indigo-400 border border-indigo-800/50">
                  <Scale className="h-5 w-5" />
                </div>
                <h3 className="text-base font-bold text-white">Lifecycle State Machine</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Strict multi-stage workflow governance from draft and publishing to bidding closure, evaluation, contract award, and archival.
                </p>
              </div>

              {/* Card 3 */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-3 hover:border-purple-500/40 transition-colors">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-950 text-purple-400 border border-purple-800/50">
                  <Lock className="h-5 w-5" />
                </div>
                <h3 className="text-base font-bold text-white">Enterprise Role Isolation</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Unified authentication with isolated workspaces for Bidders, Procurement Officers, and Platform Administrators ensuring complete data privacy.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 py-8 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-purple-400" />
            <span className="font-semibold text-slate-400">BidVerify AI</span>
            <span>— GeM Procurement Compliance System</span>
          </div>
          <div>
            <span>Designed for Public Procurement Transparency & Compliance</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
