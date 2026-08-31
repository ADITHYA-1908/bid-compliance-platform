"use client";

import React from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { FeaturePlaceholder } from "@/components/common/FeaturePlaceholder";

export default function BidderClarificationsPage() {
  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title="Buyer Clarifications & Queries"
      description="Respond to formal clarification requests issued by procurement evaluation committees."
      breadcrumbs={[
        { label: "Bidder", href: "/bidder" },
        { label: "Clarifications" },
      ]}
    >
      <FeaturePlaceholder
        title="Clarification & Query Resolution"
        description="Encrypted communication channel to respond to buyer clarification notices and submit supplementary evidence."
        phase="Part 6"
        moduleName="Clarification Module"
      />
    </DashboardLayout>
  );
}
