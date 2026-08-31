"use client";

import React, { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { FeaturePlaceholder } from "@/components/common/FeaturePlaceholder";
import { Shield } from "lucide-react";
import { api, RoleItem } from "@/lib/api";

export default function AdminRolesPage() {
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getRoles()
      .then((data) => {
        if (Array.isArray(data)) setRoles(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <DashboardLayout
      allowedRoles={["ADMIN"]}
      title="System RBAC Roles"
      description="Inspect active database role definitions and access control policies."
      breadcrumbs={[
        { label: "Admin", href: "/admin" },
        { label: "Roles" },
      ]}
    >
      <div className="space-y-6">
        {/* Live Database Roles List */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="h-5 w-5 text-purple-900" />
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Configured Database Roles ({roles.length})
            </h2>
          </div>

          {loading ? (
            <p className="text-xs text-slate-500">Loading roles from database...</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {roles.map((r) => (
                <div key={r.id} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <span className="font-bold text-xs font-mono text-slate-900 bg-slate-100 px-2 py-0.5 rounded-md">
                      {r.name}
                    </span>
                    <p className="text-xs text-slate-600 mt-1">{r.description}</p>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400 truncate max-w-xs">{r.id}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <FeaturePlaceholder
          title="Role Policy Matrix & Custom Permissions"
          description="Granular permission sets and hierarchical access assignment."
          phase="Part 2"
          moduleName="Role Matrix Module"
        />
      </div>
    </DashboardLayout>
  );
}
