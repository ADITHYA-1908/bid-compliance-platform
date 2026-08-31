"use client";

import React from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { FeaturePlaceholder } from "@/components/common/FeaturePlaceholder";

export default function AdminOrganizationsPage() {
  return (
    <DashboardLayout
      allowedRoles={["ADMIN"]}
      title="Organization Directory"
      description="Manage participating vendor companies, ministries, departments, and CPSE entities."
      breadcrumbs={[
        { label: "Admin", href: "/admin" },
        { label: "Organizations" },
      ]}
    >
      <FeaturePlaceholder
        title="Organization Registry & Verification"
        description="Centralized organization master with legal entity validation, registration numbers, and verification status."
        phase="Part 2"
        moduleName="Organization Directory Module"
      />
    </DashboardLayout>
  );
}
