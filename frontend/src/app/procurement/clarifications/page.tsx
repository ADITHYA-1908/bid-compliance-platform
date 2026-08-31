"use client";

import React from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { FeaturePlaceholder } from "@/components/common/FeaturePlaceholder";

export default function ProcurementClarificationsPage() {
  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER"]}
      title="Clarifications Management"
      description="Issue formal clarification notices to bidders and evaluate returned explanations."
      breadcrumbs={[
        { label: "Procurement", href: "/procurement" },
        { label: "Clarifications" },
      ]}
    >
      <FeaturePlaceholder
        title="Clarification Request Workflow"
        description="Structured request system with deadline timers, document resubmission flags, and committee logging."
        phase="Part 6"
        moduleName="Clarifications Module"
      />
    </DashboardLayout>
  );
}
