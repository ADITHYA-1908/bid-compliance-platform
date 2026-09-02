"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { Users, Building2, Shield, Network, ArrowRight, ShieldCheck, Activity } from "lucide-react";

export default function AdminDashboardPage() {
  const { user } = useAuth();
  const [dbStatus, setDbStatus] = useState<string>("Checking...");

  useEffect(() => {
    // Check real backend status via centralized API client
    api.checkDatabaseHealth()
      .then((res) => {
        if (res.database === "connected") {
          setDbStatus("Connected (Supabase PostgreSQL)");
        } else {
          setDbStatus("Unavailable");
        }
      })
      .catch(() => setDbStatus("Unavailable"));
  }, []);

  return (
    <DashboardLayout
      allowedRoles={["ADMIN"]}
      title="Administrator Workspace"
      description="System oversight, user account management, role policies, and platform integration health."
      breadcrumbs={[{ label: "Admin Portal", href: "/admin" }, { label: "Dashboard" }]}
    >
      <div className="space-y-6">
        {/* Welcome & Admin Entity Card */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 border border-emerald-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-600"></span>
                  Superuser Session
                </span>
                <span className="inline-flex items-center rounded-md bg-rose-50 px-2 py-0.5 text-xs font-semibold text-rose-800 border border-rose-200">
                  ADMIN
                </span>
              </div>
              <h2 className="text-xl font-bold text-slate-900">
                Welcome, {user?.full_name}
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Scope: <span className="font-semibold text-slate-700">{user?.organization || "Platform Oversight"}</span> • Admin Email: <span className="font-mono text-slate-700">{user?.email}</span>
              </p>
            </div>

            <Link
              href="/admin/users"
              className="inline-flex items-center gap-1.5 self-start sm:self-center rounded-md bg-rose-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-rose-800 transition-colors shadow-xs"
            >
              User Oversight
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>

        {/* Metric Placeholder Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Total Users
              </span>
              <div className="rounded-lg bg-rose-50 p-2 text-rose-900">
                <Users className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">—</p>
            <p className="mt-1 text-[11px] text-slate-500">System oversight & compliance</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Organizations
              </span>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                <Building2 className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">—</p>
            <p className="mt-1 text-[11px] text-slate-500">Buyer and vendor registry</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                System RBAC Roles
              </span>
              <div className="rounded-lg bg-purple-50 p-2 text-purple-900">
                <Shield className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl font-bold font-mono text-slate-900">3</p>
            <p className="mt-1 text-[11px] text-slate-500">BIDDER, PROCUREMENT, ADMIN</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Database Status
              </span>
              <div className="rounded-lg bg-emerald-50 p-2 text-emerald-700">
                <Activity className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-xs font-bold text-emerald-700 font-mono line-clamp-1">{dbStatus}</p>
            <p className="mt-1 text-[11px] text-slate-500">Live PostgreSQL Engine</p>
          </div>
        </div>

        {/* Operational Notice */}
        <div className="rounded-xl border border-rose-200 bg-rose-50/40 p-5">
          <div className="flex items-start gap-3">
            <ShieldCheck className="h-5 w-5 text-rose-900 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-700 space-y-1">
              <p className="font-bold text-rose-900">
                System Administration Shell Active
              </p>
              <p>
                Platform user administration, organization validation, and API integration monitoring controls will be activated in upcoming development phases.
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
