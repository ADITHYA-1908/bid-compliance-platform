"use client";

import React, { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { FeaturePlaceholder } from "@/components/common/FeaturePlaceholder";
import { CheckCircle2, Network } from "lucide-react";
import { api } from "@/lib/api";

export default function AdminIntegrationsPage() {
  const [dbStatus, setDbStatus] = useState<string>("Checking...");

  useEffect(() => {
    api.checkDatabaseHealth()
      .then((res) => (res.database === "connected" ? setDbStatus("Connected") : setDbStatus("Disconnected")))
      .catch(() => setDbStatus("Disconnected"));
  }, []);

  return (
    <DashboardLayout
      allowedRoles={["ADMIN"]}
      title="Integration Status"
      description="Monitor connectivity with Supabase PostgreSQL, GeM API Gateway, and OCR services."
      breadcrumbs={[
        { label: "Admin", href: "/admin" },
        { label: "Integrations" },
      ]}
    >
      <div className="space-y-6">
        {/* Live Database Engine Status */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="flex items-center gap-2 mb-4">
            <Network className="h-5 w-5 text-blue-900" />
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Connected Infrastructure Services
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-lg bg-slate-50 p-4 border border-slate-200/75 flex items-start justify-between">
              <div>
                <span className="text-xs text-slate-500 font-medium">PostgreSQL Database</span>
                <p className="text-sm font-bold text-slate-900 mt-1">Supabase Pooler (Tokyo)</p>
                <span className="inline-flex items-center gap-1 mt-2 text-xs font-semibold text-emerald-700">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {dbStatus}
                </span>
              </div>
            </div>

            <div className="rounded-lg bg-slate-50 p-4 border border-slate-200/75 flex items-start justify-between">
              <div>
                <span className="text-xs text-slate-500 font-medium">FastAPI Backend</span>
                <p className="text-sm font-bold text-slate-900 mt-1">v1.0.0 API Service</p>
                <span className="inline-flex items-center gap-1 mt-2 text-xs font-semibold text-emerald-700">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Healthy
                </span>
              </div>
            </div>

            <div className="rounded-lg bg-slate-50 p-4 border border-slate-200/75 flex items-start justify-between">
              <div>
                <span className="text-xs text-slate-500 font-medium">GeM API Gateway</span>
                <p className="text-sm font-bold text-slate-900 mt-1">Procurement Bridge</p>
                <span className="inline-flex items-center gap-1 mt-2 text-xs font-semibold text-amber-700">
                  Scheduled Part 7
                </span>
              </div>
            </div>
          </div>
        </div>

        <FeaturePlaceholder
          title="Government API Connectors"
          description="GSTN API, Income Tax e-filing bridge, MCA-21 company registry, and GeM Core integrations."
          phase="Part 7"
          moduleName="Integration Management"
        />
      </div>
    </DashboardLayout>
  );
}
