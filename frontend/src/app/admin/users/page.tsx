"use client";

import React from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { FeaturePlaceholder } from "@/components/common/FeaturePlaceholder";

export default function AdminUsersPage() {
  return (
    <DashboardLayout
      allowedRoles={["ADMIN"]}
      title="User Account Management"
      description="Inspect user credentials, assigned roles, organization bindings, and active account status."
      breadcrumbs={[
        { label: "Admin", href: "/admin" },
        { label: "Users" },
      ]}
    >
      <FeaturePlaceholder
        title="User Administration & Security Oversight"
        description="Comprehensive user directory with role assignment, status toggling, and multi-factor authentication enforcement."
        phase="Part 2"
        moduleName="User Administration Module"
      />
    </DashboardLayout>
  );
}
