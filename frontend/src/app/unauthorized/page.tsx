"use client";

import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { getDashboardRoute } from "@/lib/roles";

export default function UnauthorizedPage() {
  const { user, logout } = useAuth();
  const returnRoute = user ? getDashboardRoute(user.role) : "/login";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4 py-12 text-center">
      <div className="mx-auto max-w-md bg-white p-8 rounded-xl shadow-xs border border-slate-200">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 mb-4">
          <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
        </div>

        <h1 className="text-xl font-bold text-slate-900 sm:text-2xl">
          Access Denied (403)
        </h1>

        <p className="mt-2 text-sm text-slate-600">
          You do not have permission to access the requested portal or resource with your current role.
        </p>

        {user && (
          <div className="mt-4 rounded-md bg-slate-50 p-3 border border-slate-200 text-xs text-slate-700 text-left">
            <p><span className="font-semibold">Logged in as:</span> {user.email}</p>
            <p className="mt-1"><span className="font-semibold">Your Assigned Role:</span> <span className="font-mono text-blue-900 font-bold">{user.role}</span></p>
          </div>
        )}

        <div className="mt-6 flex flex-col gap-2.5 sm:flex-row sm:justify-center">
          <Link
            href={returnRoute}
            className="inline-flex items-center justify-center rounded-md bg-blue-900 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-800 transition-colors"
          >
            Return to My Portal
          </Link>
          {user && (
            <button
              onClick={() => logout()}
              className="inline-flex items-center justify-center rounded-md border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
            >
              Sign Out
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
