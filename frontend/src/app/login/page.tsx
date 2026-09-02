"use client";

import React, { Suspense } from "react";
import { RoleLoginForm } from "@/components/auth/RoleLoginForm";

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-50">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-900 border-t-transparent mx-auto" />
            <p className="mt-3 text-xs text-slate-500 font-medium">Loading portal authentication...</p>
          </div>
        </div>
      }
    >
      <RoleLoginForm />
    </Suspense>
  );
}
