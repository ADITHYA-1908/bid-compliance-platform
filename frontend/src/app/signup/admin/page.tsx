"use client";

import React, { Suspense } from "react";
import { RoleSignupForm } from "@/components/auth/RoleSignupForm";

export default function AdminSignupPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-50">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-900 border-t-transparent mx-auto" />
            <p className="mt-3 text-xs text-slate-500 font-medium">Loading Administrator Registration...</p>
          </div>
        </div>
      }
    >
      <RoleSignupForm forcedRole="ADMIN" showRoleTabs={false} />
    </Suspense>
  );
}
