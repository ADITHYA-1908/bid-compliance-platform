"use client";

import React from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { FeaturePlaceholder } from "@/components/common/FeaturePlaceholder";

export default function ProcurementVerificationsPage() {
  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER"]}
      title="Verification Center"
      description="Run integrity verifications, central blacklisting queries, and anomaly scans."
      breadcrumbs={[
        { label: "Procurement", href: "/procurement" },
        { label: "Verifications" },
      ]}
    >
      <FeaturePlaceholder
        title="External Registry & Debarment Verification"
        description="Unified lookups against GeM Incident Management, CVC debarment databases, and MCA company filings."
        phase="Part 5"
        moduleName="Integrity Verification Center"
      />
    </DashboardLayout>
  );
}
