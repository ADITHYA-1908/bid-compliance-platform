"use client";

import React from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { FeaturePlaceholder } from "@/components/common/FeaturePlaceholder";

export default function BidderNotificationsPage() {
  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title="Notifications & Alerts"
      description="Stay updated with tender milestones, bid evaluation decisions, and audit notices."
      breadcrumbs={[
        { label: "Bidder", href: "/bidder" },
        { label: "Notifications" },
      ]}
    >
      <FeaturePlaceholder
        title="Notification & Audit Feed"
        description="Real-time alerts for procurement timeline changes, corrigendum notices, and qualification announcements."
        phase="Part 7"
        moduleName="Notification Center"
      />
    </DashboardLayout>
  );
}
