"use client";

import React from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { FeaturePlaceholder } from "@/components/common/FeaturePlaceholder";

export default function ProcurementBiddersPage() {
  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER"]}
      title="Participating Bidders"
      description="Inspect vendor registration details, MSME credentials, and past performance history."
      breadcrumbs={[
        { label: "Procurement", href: "/procurement" },
        { label: "Bidders" },
      ]}
    >
      <FeaturePlaceholder
        title="Bidder Dossier & Profile Verification"
        description="Verify vendor identity, financial solvency, and statutory eligibility against GeM and government registries."
        phase="Part 3"
        moduleName="Bidder Oversight Module"
      />
    </DashboardLayout>
  );
}
