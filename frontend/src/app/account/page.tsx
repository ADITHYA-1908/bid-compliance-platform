"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";

export default function AccountPage() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="flex items-center gap-3 text-slate-600 text-sm font-medium">
          <svg className="h-5 w-5 animate-spin text-blue-900" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Loading user session...
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-lg font-bold text-slate-900 hover:text-blue-900 transition-colors">
              BidVerify AI
            </Link>
            <span className="rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
              Portal
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden text-xs text-slate-500 sm:inline-block">
              {user.email}
            </span>
            <button
              onClick={handleLogout}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors cursor-pointer"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-900">
            <span>Authentication Verified</span>
            <span>•</span>
            <span>Verified Active Session</span>
          </div>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Welcome, {user.full_name}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Your authenticated session and profile details from PostgreSQL & Supabase.
          </p>
        </div>

        {/* Profile Card */}
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="border-b border-slate-200 bg-slate-50/75 px-6 py-4">
            <h2 className="text-sm font-semibold text-slate-900">Account & Profile Identity</h2>
            <p className="text-xs text-slate-500">Verified via JWT bearer token against `/api/v1/auth/me`</p>
          </div>

          <dl className="divide-y divide-slate-200">
            <div className="px-6 py-4 sm:grid sm:grid-cols-3 sm:gap-4">
              <dt className="text-xs font-medium text-slate-500 uppercase tracking-wider">Full Name</dt>
              <dd className="mt-1 text-sm font-semibold text-slate-900 sm:col-span-2 sm:mt-0">
                {user.full_name}
              </dd>
            </div>

            <div className="px-6 py-4 sm:grid sm:grid-cols-3 sm:gap-4">
              <dt className="text-xs font-medium text-slate-500 uppercase tracking-wider">Email Address</dt>
              <dd className="mt-1 text-sm text-slate-900 sm:col-span-2 sm:mt-0 font-mono">
                {user.email}
              </dd>
            </div>

            <div className="px-6 py-4 sm:grid sm:grid-cols-3 sm:gap-4">
              <dt className="text-xs font-medium text-slate-500 uppercase tracking-wider">Assigned Role</dt>
              <dd className="mt-1 sm:col-span-2 sm:mt-0">
                <span className="inline-flex items-center rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-800 border border-blue-200">
                  {user.role}
                </span>
              </dd>
            </div>

            <div className="px-6 py-4 sm:grid sm:grid-cols-3 sm:gap-4">
              <dt className="text-xs font-medium text-slate-500 uppercase tracking-wider">Organization Entity</dt>
              <dd className="mt-1 text-sm font-medium text-slate-900 sm:col-span-2 sm:mt-0">
                {user.organization || "No organization assigned"}
              </dd>
            </div>

            <div className="px-6 py-4 sm:grid sm:grid-cols-3 sm:gap-4">
              <dt className="text-xs font-medium text-slate-500 uppercase tracking-wider">Account Status</dt>
              <dd className="mt-1 sm:col-span-2 sm:mt-0">
                <span className="inline-flex items-center gap-1.5 rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800 border border-emerald-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-600"></span>
                  Active
                </span>
              </dd>
            </div>

            <div className="px-6 py-4 sm:grid sm:grid-cols-3 sm:gap-4">
              <dt className="text-xs font-medium text-slate-500 uppercase tracking-wider">Internal User ID</dt>
              <dd className="mt-1 text-xs text-slate-500 font-mono sm:col-span-2 sm:mt-0">
                {user.id}
              </dd>
            </div>
          </dl>
        </div>

        {/* Info Callout */}
        <div className="mt-6 rounded-lg bg-blue-50/50 p-4 border border-blue-200 text-xs text-slate-700 flex items-start gap-3">
          <svg className="h-5 w-5 text-blue-800 shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
          </svg>
          <div>
            <span className="font-semibold text-blue-900">Next Phase Note:</span> Role-based dashboards (Bidder workspace, Procurement Officer tender evaluation portal) will be enabled in subsequent parts.
          </div>
        </div>
      </main>
    </div>
  );
}
